"""
An agent, which is only responsible for the write_patch tool call.
"""

import json
import shutil
from collections.abc import Callable, Iterable
from copy import deepcopy
from os.path import join as pjoin
from pathlib import Path

from loguru import logger

from app import globals
from app.api import agent_common
from app.api.python import validation
from app.data_structures import MessageThread, MethodId
from app.log import print_acr, print_patch_generation
from app.model import common
from app.post_process import (
    ExtractStatus,
    extract_diff_one_instance,
    record_extract_status,
)
from app.task import SweTask, Task

# agent edits
from cog_arch.utils import agent_globals
from cog_arch.utils import format_failed_tests
# from cog_arch.utils.agent_globals import agent
from cog_arch.utils.traj_file_io import extract_failed_tests
from pprint import pp

SYSTEM_PROMPT = """You are a software developer maintaining a large project.
You are working on an issue submitted to your project.
The issue contains a description marked between <issue> and </issue>.
You ultimate goal is to write a patch that resolves this issue.
"""


USER_PROMPT_INIT = """Write a patch for the issue, based on the retrieved context.\n\nYou can import necessary libraries.\n\n
Return the patch in the format below.\n\nWithin `<file></file>`, replace `...` with actual file path.\n\nWithin `<original></original>`, replace `...` with the original code snippet from the program.\n\nWithin `<patched></patched>`, replace `...` with the fixed version of the original code. When adding orignal code and updated code, pay attention to indentation, as the code is in Python.
You can write multiple modifications if needed.

```
# modification 1
<file>...</file>
<original>...</original>
<patched>...</patched>

# modification 2
<file>...</file>
<original>...</original>
<patched>...</patched>

# modification 3
...
```
"""


def run_with_retries(
    message_thread: MessageThread,
    output_dir: str,
    task: Task,
    retries=3,
    print_callback: Callable[[dict], None] | None = None,
) -> tuple[str, float, int, int]:
    """
    Since the agent may not always write an applicable patch, we allow for retries.
    This is a wrapper around the actual run.
    """
    # (1) replace system prompt
    messages = deepcopy(message_thread.messages)
    new_thread: MessageThread = MessageThread(messages=messages)
    new_thread = agent_common.replace_system_prompt(new_thread, SYSTEM_PROMPT)

    # (2) add the initial user prompt
    new_thread.add_user(USER_PROMPT_INIT)
    print_acr(USER_PROMPT_INIT, "patch generation", print_callback=print_callback)

    can_stop = False
    result_msg = ""

    # agent edits
    if agent_globals.use_agent:
        # global agent
        # note theres this i > retries break part
        # we denote retries as number of tries
        retries = agent_globals.agent.patch_retries

    for i in range(1, retries + 2):
        if i > 1:
            debug_file = pjoin(output_dir, f"debug_agent_write_patch_{i - 1}.json")
            with open(debug_file, "w") as f:
                json.dump(new_thread.to_msg(), f, indent=4)

        if can_stop or i > retries:
            break

        logger.info(f"Trying to write a patch. Try {i} of {retries}.")

        raw_patch_file = pjoin(output_dir, f"agent_patch_raw_{i}")

        # actually calling model
        res_text, *_ = common.SELECTED_MODEL.call(new_thread.to_msg())

        new_thread.add_model(res_text, [])  # no tools

        logger.info(f"Raw patch produced in try {i}. Writing patch into file.")

        with open(raw_patch_file, "w") as f:
            f.write(res_text)

        print_patch_generation(
            res_text, f"try {i} / {retries}", print_callback=print_callback
        )

        # Attemp to extract a real patch from the raw patch
        diff_file = pjoin(output_dir, f"extracted_patch_{i}.diff")
        extract_status, extract_msg = extract_diff_one_instance(
            raw_patch_file, diff_file
        )

        # record the extract status. This is for classifying the task at the end of workflow
        record_extract_status(output_dir, extract_status)

        if extract_status == ExtractStatus.APPLICABLE_PATCH:
            patch_content = Path(diff_file).read_text()
            print_acr(
                f"```diff\n{patch_content}\n```",
                "extracted patch",
                print_callback=print_callback,
            )

            # patch generated is applicable and all edits are ok, so we can think about validation
            if globals.enable_validation:
                # if we have a patch extracted, apply it and validate

                patch_is_correct, err_message, log_file = task.validate(diff_file)
                log_file_dest = pjoin(output_dir, f"run_test_suite_{i}.log")
                shutil.move(log_file, log_file_dest)

                # agent edits
                if agent_globals.use_agent:
                    # agent.patch_is_correct = patch_is_correct
                    agent_globals.agent.patch_is_correct = patch_is_correct
                    agent_globals.agent.failed_tests = extract_failed_tests(log_file_dest)
                    print(f'patch_is_correct: {patch_is_correct}')

                if patch_is_correct:
                    result_msg = (
                        "Written a patch that resolves the issue. Congratulations!"
                    )
                    new_thread.add_user(result_msg)  # just for logging
                    print_acr(
                        result_msg,
                        f"patch generation try {i} / {retries}",
                        print_callback=print_callback,
                    )
                    can_stop = True
                # the following two branches cannot be swapped, because
                # --enable-perfect-angelic is meant to override --enable-angelic
                elif globals.enable_perfect_angelic:
                    if not isinstance(task, SweTask):
                        raise NotImplementedError(
                            f"Angelic debugging not implemented for {type(task).__name__}"
                        )

                    msg = (
                        f"Written an applicable patch, but it did not resolve the issue. Error message: {err_message}.",
                    )

                    # incorrect_locations = validation.perfect_angelic_debug(
                    #     task.task_id, diff_file, task.project_path
                    # )
                    incorrect_locations = validation.perfect_angelic_debug_mod(
                        pjoin(output_dir, 'developer_patch.diff'), diff_file, task.project_path
                    )
                    angelic_msg = angelic_debugging_message(incorrect_locations[0])

                    # agent edits
                    if agent_globals.use_agent:
                        # agent.edit_location_summary = incorrect_locations
                        agent_globals.agent.edit_location_summary = incorrect_locations
                        print('incorrect_locations\n')
                        pp(incorrect_locations)

                    result_msg = f"{msg}\n{angelic_msg}"
                    new_thread.add_user(result_msg)
                    print_acr(
                        result_msg,
                        f"patch generation try {i} / {retries}",
                        print_callback=print_callback,
                    )
                    continue
                elif globals.enable_angelic:
                    raise NotImplementedError(
                        "Angelic debugging has not been integrated"
                    )
                else:
                    result_msg = f"Written an applicable patch, but it did not resolve the issue. {err_message} "
                    result_msg += " Please try again."
                    new_thread.add_user(result_msg)
                    if agent_globals.use_agent and agent_globals.agent.agent_mode == 'kg' and i < retries:
                        msg_thread_list = new_thread.to_msg()
                        extra_info = agent_globals.agent.graph_retrieval_procedure(msg_thread_list, msg_thread_list[-2]['content'])
                        
                        failed_tests_msg = f"Failed tests:\n\n{format_failed_tests(agent_globals.agent.failed_tests)}"
                        new_thread.add_user(failed_tests_msg)
                        print_acr(
                            failed_tests_msg,
                            f"patch generation try {i} / {retries}",
                            print_callback=print_callback,
                        )

                        # extra_info_msg = f"Also, consider the following information:\n\n{extra_info}"
                        extra_info_msg = f"\n\nHere are some info from past attempts:\n\n{extra_info}"
                        new_thread.add_user(extra_info_msg)
                        print_acr(
                            extra_info_msg,
                            f"patch generation try {i} / {retries}",
                            print_callback=print_callback,
                        )
                    print_acr(
                        result_msg,
                        f"patch generation try {i} / {retries}",
                        print_callback=print_callback,
                    )
                    continue
            elif globals.enable_perfect_angelic:
                if not isinstance(task, SweTask):
                    raise NotImplementedError(
                        f"Angelic debugging not implemented for {type(task).__name__}"
                    )

                incorrect_locations = validation.perfect_angelic_debug(
                    task.task_id, diff_file, task.project_path
                )

                msg = "Extracted a patch."
                if angelic_msg := angelic_debugging_message(incorrect_locations[0]):
                    result_msg = f"{msg}\n{angelic_msg}"
                else:
                    result_msg = msg

                new_thread.add_user(result_msg)
                print_acr(
                    result_msg,
                    f"patch generation try {i} / {retries}",
                    print_callback=print_callback,
                )
                continue
            elif globals.enable_angelic:
                raise NotImplementedError("Angelic debugging has not been integrated")
            else:
                result_msg = "Extracted a patch. Since validation is disabled, you should validation the patch later on. Ending the workflow."
                new_thread.add_user(result_msg)  # just for logging
                print_acr(
                    result_msg,
                    f"patch generation try {i} / {retries}",
                    print_callback=print_callback,
                )
                can_stop = True

        else:
            # we dont have a valid patch
            new_prompt = (
                "Your edit could not be applied to the program. "
                + extract_msg
                + " Please try again."
            )
            new_thread.add_user(new_prompt)
            if agent_globals.use_agent and agent_globals.agent.agent_mode == 'kg' and i < retries:
                msg_thread_list = new_thread.to_msg()
                extra_info = agent_globals.agent.graph_retrieval_procedure(msg_thread_list, msg_thread_list[-2]['content'])
                # extra_info_msg = f"Also, consider the following information:\n\n{extra_info}"
                extra_info_msg = f"\n\nHere are some info from past attempts:\n\n{extra_info}"
                new_thread.add_user(extra_info_msg)
                print_acr(
                    extra_info_msg,
                    f"patch generation try {i} / {retries}",
                    print_callback=print_callback,
                )
            print_acr(
                new_prompt,
                f"patch generation try {i} / {retries}",
                print_callback=print_callback,
            )
            result_msg = "Failed to write a valid patch."

    return result_msg


def angelic_debugging_message(
    incorrect_locations: Iterable[tuple[str, MethodId]],
) -> str:
    msg = []

    if incorrect_locations:
        msg.append("The following methods should not have been changed:")
        msg.extend(
            f"    {filename}: {method_id!s}"
            for filename, method_id in incorrect_locations
        )

    return "\n".join(msg)
