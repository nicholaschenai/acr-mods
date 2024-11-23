import inspect
import json
import re
from collections.abc import Callable
from os.path import join as pjoin
from pathlib import Path

from loguru import logger
from termcolor import colored

from app import globals
from app.api.manage import ProjectApiManager
from app.data_structures import FunctionCallIntent, MessageThread
from app.log import (
    log_and_cprint,
    log_and_print,
    print_acr,
    print_banner,
    print_issue,
    print_retrieval,
)
from app.model import common, ollama
from app.search.search_manage import SearchManager
from app.utils import parse_function_invocation

# agent edits
from cog_arch.utils import agent_globals
# from cog_arch.utils.agent_globals import agent

# FIXME: the system prompt should be different for stratified/state machine.
SYSTEM_PROMPT = """You are a software developer maintaining a large project.
You are working on an issue submitted to your project.
The issue contains a description marked between <issue> and </issue>.
Your task is to invoke a few search API calls to gather buggy information, then write patches to solve the issues.
"""


def prepare_issue_prompt(problem_stmt: str) -> str:
    """
    Given the raw problem statement, sanitize it and prepare the issue prompt.
    Args:
        problem_stmt (str): The raw problem statement.
            Assumption: the problem statement is the content of a markdown file.
    Returns:
        str: The issue prompt.
    """
    # remove markdown comments
    problem_wo_comments = re.sub(r"<!--.*?-->", "", problem_stmt, flags=re.DOTALL)
    content_lines = problem_wo_comments.split("\n")
    # remove spaces and empty lines
    content_lines = [x.strip() for x in content_lines]
    content_lines = [x for x in content_lines if x != ""]
    problem_stripped = "\n".join(content_lines)
    # add tags
    result = "<issue>" + problem_stripped + "\n</issue>"
    return result


def add_step_trigger(orig_prompt: str, is_first: bool = False) -> str:
    """
    Given the original prompt, add the trigger question for the next step.
    Args:
        orig_prompt (str): The original prompt.
        is_first (bool): Whether the trigger is for the first step.
    Returns:
        str: The prompt with trigger question.
    """
    if is_first:
        trigger = "What is the first step?"
    else:
        trigger = "What's the next step to complete the task? Be reminded that you are solving the initial issue."
    return orig_prompt + "\n" + trigger


def start_conversation_round_stratified(
    output_dir: str,
    msg_thread: MessageThread,
    api_manager: ProjectApiManager,
    start_round_no: int = 0,
    print_callback: Callable[[dict], None] | None = None,
) -> bool:
    """
    This version uses json data to process API calls, instead of using the OpenAI function calling.
    Advantage is that multiple API calls can be made in a single round.
    """
    # agent edits
    if agent_globals.use_agent and agent_globals.agent.agent_mode=='plan':
        # global agent
        # agent = AcrAgent(agent_model=agent_model, ckpt_dir=agent_globals.ckpt_dir)
        plans_message = agent_globals.agent.get_plans_msg(msg_thread.messages, use_retrieved=False)
        print_acr(
            agent_globals.agent.full_plan,
            "full_plan",
            print_callback=print_callback,
        )
        if plans_message:
            # print(f'\n\nplans_message: {plans_message}')
            msg_thread.add_user(plans_message)
            print_acr(
                plans_message,
                "plans_message",
                print_callback=print_callback,
            )

    prompt = (
        "Based on the files, classes, methods, and code statements from the issue related to the bug, you can use the following search APIs to get more context of the project."
        "\n- search_class(class_name: str): Search for a class in the codebase"
        "\n- search_method_in_file(method_name: str, file_path: str): Search for a method in a given file"
        "\n- search_method_in_class(method_name: str, class_name: str): Search for a method in a given class"
        "\n- search_method(method_name: str): Search for a method in the entire codebase"
        "\n- search_code(code_str: str): Search for a code snippet in the entire codebase"
        "\n- search_code_in_file(code_str: str, file_path: str): Search for a code snippet in a given file file"
        "\n\nNote that you can use multiple search APIs in one round."
        "\n\nNow analyze the issue and select necessary APIs to get more context of the project. Each API call must have concrete arguments as inputs."
    )
    msg_thread.add_user(prompt)

    round_no = start_round_no
    for round_no in range(start_round_no, globals.conv_round_limit + 1):
        api_manager.start_new_tool_call_layer()

        conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
        # save current state before starting a new round
        msg_thread.save_to_file(conversation_file)

        print_banner(f"CONTEXT RETRIEVAL ROUND {round_no}")

        print_acr(
            prompt,
            f"context retrieval round {start_round_no}",
            print_callback=print_callback,
        )

        res_text, *_ = common.SELECTED_MODEL.call(msg_thread.to_msg())
        msg_thread.add_model(res_text, tools=[])
        print_retrieval(res_text, f"round {round_no}", print_callback=print_callback)

        selected_apis, _, proxy_threads = api_manager.proxy_apis(res_text)

        proxy_log = Path(output_dir, f"agent_proxy_{round_no}.json")
        proxy_messages = [thread.to_msg() for thread in proxy_threads]
        proxy_log.write_text(json.dumps(proxy_messages, indent=4))

        if selected_apis is None:
            msg = "The search API calls seem not valid. Please check the arguments you give carefully and try again."
            msg_thread.add_user(msg)
            print_acr(
                msg,
                f"context retrieval round {round_no}",
                print_callback=print_callback,
            )
            continue

        selected_apis_json = json.loads(selected_apis)

        json_api_calls = selected_apis_json.get("API_calls", [])
        buggy_locations = selected_apis_json.get("bug_locations", [])

        formatted = []
        if json_api_calls:
            formatted.append("API calls:")
            for call in json_api_calls:
                formatted.extend([f"\n- `{call}`"])

        if buggy_locations:
            formatted.append("\n\nBug locations")
            for location in buggy_locations:
                s = ", ".join(f"{k}: `{v}`" for k, v in location.items())
                formatted.extend([f"\n- {s}"])

        print_acr(
            "\n".join(formatted),
            "Agent-selected API calls",
            print_callback=print_callback,
        )

        # collected enough information to write patch
        if buggy_locations and (not json_api_calls):
            collated_tool_response = "Here is the code in buggy locations:\n\n"
            # provide the buggy locations to the model
            for bug_location in buggy_locations:
                tool_output, *_ = search_for_bug_location(
                    api_manager, msg_thread, bug_location
                )
                collated_tool_response += f"\n\n{tool_output}\n"

            if (
                "Unknown function" not in collated_tool_response
                and "Could not" not in collated_tool_response
            ):
                msg_thread.add_user(collated_tool_response)

                print_banner("PATCH GENERATION")
                logger.debug("Gathered enough information. Invoking write_patch.")
                print_acr(
                    collated_tool_response,
                    "patch generation round 1",
                    print_callback=print_callback,
                )
                break

            msg = "The buggy locations is not precise. You may need to check whether the arguments are correct and search more information."
            msg_thread.add_user(msg)
            print_acr(
                msg,
                f"context retrieval round {round_no}",
                print_callback=print_callback,
            )
            continue

        # prepare response from tools
        collated_tool_response = ""

        for api_call in json_api_calls:
            func_name, func_args = parse_function_invocation(api_call)

            arg_spec = inspect.getfullargspec(getattr(SearchManager, func_name))
            arg_names = arg_spec.args[1:]  # first parameter is self

            assert len(func_args) == len(
                arg_names
            ), f"Number of argument is wrong in API call: {api_call}"

            kwargs = dict(zip(arg_names, func_args))
            intent = FunctionCallIntent(func_name, kwargs, None)
            tool_output, _, _ = api_manager.dispatch_intent(intent, msg_thread)

            collated_tool_response += f"Result of {api_call}:\n\n"
            collated_tool_response += tool_output + "\n\n"

        msg_thread.add_user(collated_tool_response)
        print_acr(
            collated_tool_response,
            f"context retrieval round {round_no}",
            print_callback=print_callback,
        )

        msg = "Let's analyze collected context first"
        msg_thread.add_user(msg)
        print_acr(
            msg, f"context retrieval round {round_no}", print_callback=print_callback
        )

        res_text, *_ = common.SELECTED_MODEL.call(msg_thread.to_msg())
        msg_thread.add_model(res_text, tools=[])
        print_retrieval(res_text, f"round {round_no}", print_callback=print_callback)

        if round_no < globals.conv_round_limit:
            msg = (
                "Based on your analysis, answer below questions:"
                "\n- do we need more context: construct search API calls to get more context of the project. (leave it empty if you don't need more context)"
                "\n- where are bug locations: buggy files and methods. (leave it empty if you don't have enough information)"
            )
            if agent_globals.use_agent and agent_globals.agent.agent_mode == 'kg':
                agent_globals.agent.declarative_mem.print_doc_count()
                msg_thread_list = msg_thread.to_msg()
                extra_info = agent_globals.agent.graph_retrieval_procedure(msg_thread_list)
                # msg += f"\n\nBefore you answer, please consider the following info from a knowledge graph of past attempts:\n\n{extra_info}"
                extra_info_msg = f"\n\nHere are some info from past attempts:\n\n{extra_info}"
                msg_thread.add_user(extra_info_msg)
                print_acr(
                    extra_info_msg,
                    f"context retrieval round {round_no}",
                    print_callback=print_callback,
                )
            if isinstance(common.SELECTED_MODEL, ollama.OllamaModel):
                # llama models tend to always output search APIs and buggy locations.
                msg += "\n\nNOTE: If you have already identified the bug locations, do not make any search API calls."
            msg_thread.add_user(msg)
            print_acr(
                msg,
                f"context retrieval round {round_no}",
                print_callback=print_callback,
            )
    else:
        logger.info("Too many rounds. Try writing patch anyway.")

    round_no += 1

    api_manager.start_new_tool_call_layer()

    write_patch_intent = FunctionCallIntent("write_patch", {}, None)
    api_manager.dispatch_intent(
        write_patch_intent, msg_thread, print_callback=print_callback
    )

    # agent edits
    if agent_globals.use_agent and agent_globals.agent.agent_mode == 'plan':
        if not agent_globals.agent.patch_is_correct and agent_globals.agent.edit_location_summary:
            if agent_globals.agent.workflow_retry_count < agent_globals.agent.workflow_retry_limit:
                agent_globals.agent.extract_learn_plan(msg_thread.messages)

    conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
    msg_thread.save_to_file(conversation_file)

    logger.info("Invoked write_patch. Ending workflow.")

    return True


def search_for_bug_location(
    api_manager: ProjectApiManager,
    msg_thread: MessageThread,
    bug_location: dict[str, str],
) -> tuple[str, str, bool]:
    found = False

    file_name = bug_location.get("file")
    method_name = bug_location.get("method")
    class_name = bug_location.get("class")

    assert method_name or class_name, f"Invalid bug location: {bug_location}"

    call_result = None

    def call_function(func_name: str, kwargs: dict[str, str]) -> None:
        nonlocal found, call_result

        intent = FunctionCallIntent(func_name, kwargs, None)
        call_result = api_manager.dispatch_intent(intent, msg_thread)
        _, _, call_is_ok = call_result
        found |= call_is_ok

    if (not found) and method_name and class_name:
        kwargs = {"method_name": method_name, "class_name": class_name}
        call_function("search_method_in_class", kwargs)

    if (not found) and method_name and file_name:
        kwargs = {"method_name": method_name, "file_name": file_name}
        call_function("search_method_in_file", kwargs)

    if (not found) and class_name and file_name:
        kwargs = {"class_name": class_name, "file_name": file_name}
        call_function("search_class_in_file", kwargs)

    if (not found) and class_name:
        kwargs = {"class_name": class_name}
        call_function("get_class_full_snippet", kwargs)

    if (not found) and method_name:
        kwargs = {"method_name": method_name}
        call_function("search_method", kwargs)

    assert call_result

    return call_result


def dump_tool_call_layers_to_file(
    tool_call_layers: list[dict], output_dir: str
) -> None:
    """Dump the layers of tool calls to a file."""
    tool_call_file = pjoin(output_dir, "tool_call_layers.json")
    with open(tool_call_file, "w") as f:
        json.dump(tool_call_layers, f, indent=4)


def start_conversation_round_state_machine(
    output_dir: str,
    msg_thread: MessageThread,
    api_manager: ProjectApiManager,
    start_round_no: int = 0,
) -> bool:
    """
    Start the actual rounds of conversations with model.

    Args:
        output_dir (str): Path to the output directory.
        msg_thread (MessageThread): The message thread to be used.
        api_manager (ProjectApiManager): The API manager to be used.
        start_round_no (int): The round number to start with.
    """
    round_no = start_round_no
    for round_no in range(start_round_no, globals.conv_round_limit + 1):
        conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
        # save current state before starting a new round
        msg_thread.save_to_file(conversation_file)
        log_and_cprint(
            f"\n========== Conversation Round {round_no} ==========", style="red bold"
        )
        log_and_print(f"{colored('Current message thread:', 'green')}\n{msg_thread}")

        allowed_tools = api_manager.next_tools()
        # TODO: configure the list of tools based on state machine
        tools = ProjectApiManager.get_full_funcs_for_openai(allowed_tools)

        log_and_cprint(f"Current tool state: {api_manager.curr_tool}", style="yellow")
        log_and_cprint(f"Allowed next tool states: {allowed_tools}", style="yellow")

        # create a new iteration of conversation
        res_text, raw_tool_calls, func_call_intents, *_ = common.SELECTED_MODEL.call(
            msg_thread.to_msg(), tools=tools
        )
        log_and_print(
            f"{colored('This roud model response (text):', 'blue')} {res_text}"
        )
        # model can decide whether to create a function call
        if len(func_call_intents) == 1:
            # good case in which we can check function call
            func_call_intent: FunctionCallIntent = func_call_intents[0]
            log_and_print(
                f"{colored('This round model response (function call):', 'blue')} {func_call_intent}"
            )
            # dispatch this function call
            this_model_response = res_text
            this_model_tools = raw_tool_calls
            # add previous call information to user message
            tool_output, summary, _ = api_manager.dispatch_intent(
                func_call_intent, msg_thread
            )
        else:
            # no function call, let's force the model to make one
            this_model_tools = []
            this_model_response = res_text
            tool_output = ""
            summary = "There is no function call in your previous response. Make sure you include one function call. "

        next_user_message = add_step_trigger(summary)

        # form message thread for next round. should include what the model said as well
        msg_thread.add_model(this_model_response, this_model_tools)
        if this_model_tools:
            tool_call_id = this_model_tools[0].id
            msg_thread.add_tool(tool_output, tool_call_id)
            msg_thread.add_user(next_user_message)
        else:
            msg_thread.add_user(next_user_message)

        if len(func_call_intents) == 1:
            func_call_name = func_call_intents[0].func_name
            if func_call_name == "write_patch":
                log_and_print("Ending workflow. write_patch has been invoked.")
                break

        log_and_print("Going to next round ..........")
    else:
        log_and_print("Too many rounds. Try writing patch anyway.")
        write_patch_intent = FunctionCallIntent("write_patch", {}, None)
        api_manager.dispatch_intent(write_patch_intent, msg_thread)

    round_no += 1

    # if we end the workflow normally, there is one more round of conversation to store
    conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
    msg_thread.save_to_file(conversation_file)
    return True


def run_one_task(
    output_dir: str,
    api_manager: ProjectApiManager,
    problem_stmt: str,
    print_callback: Callable[[dict], None] | None = None,
) -> bool:
    """
    Main entry point to run inference on one task.
    Args:
        output_dir (str): Path to the output directory.
        api_manager (ProjectApiManager): The already-initialized API manager.
        problem_stmt (str): The original problem statement submitted to the task issue.
    """
    print_banner("Starting AutoCodeRover on the following issue")
    print_issue(problem_stmt)
    msg_thread = MessageThread()

    system_prompt = SYSTEM_PROMPT
    if (not globals.enable_layered) and common.SELECTED_MODEL.parallel_tool_call:
        # these models support parallel tool calls, let's try to make them not do it
        system_prompt += " In your response, DO NOT make more than one tool call."

    msg_thread.add_system(system_prompt)
    original_prompt = prepare_issue_prompt(problem_stmt)
    msg_thread.add_user(original_prompt)

    # Add another user message about fault localization
    if globals.enable_sbfl:
        localization_result, _, _ = api_manager.fault_localization()
        localization_prompt = "An external analysis tool has been deployed to identify the suspicious code to be fixed. You can choose to use the results from this tool, if you think they are useful."
        localization_prompt += "The tool output is as follows:\n"
        localization_prompt += localization_result
        msg_thread.add_user(localization_prompt)

    if globals.enable_layered:
        return start_conversation_round_stratified(
            output_dir, msg_thread, api_manager, print_callback=print_callback
        )
    else:
        return start_conversation_round_state_machine(
            output_dir, msg_thread, api_manager
        )


# NOTE: deprecated
def continue_task_from_cache(
    cache_path: str, output_dir: str, api_manager: ProjectApiManager
) -> bool:
    """
    Run inference on one task, but load conversation history from cache.
    Args:
        cache_path (str): Path to the old conversation history file.
        output_dir (str): Path to the output directory.
        api_manager (ProjectApiManager): The already-initialized API manager.
    """
    # (1) load the existing message thread
    msg_thread = MessageThread.load_from_file(cache_path)
    completed_round_no = msg_thread.get_round_number()

    # (2) start the actual workflow
    return start_conversation_round_state_machine(
        output_dir, msg_thread, api_manager, start_round_no=completed_round_no
    )
