import inspect
import json
from os.path import join as pjoin
from pathlib import Path
from typing import Callable

from loguru import logger
from langchain_core.messages import HumanMessage

from app import globals
from app.api.manage import ProjectApiManager
from app.data_structures import MessageThread, FunctionCallIntent
from app.log import print_acr, print_banner, print_retrieval
from app.model import common
from app.search.search_manage import SearchManager
from app.utils import parse_function_invocation

# agent imports
from ..prompts import subtask_prompts
from ..prompts.multi_attempt_prompts import shared_context_template

from ..utils import agent_globals
from ..utils.langgraph_utils import AgentState


def start_agent_gather_info(
        state: AgentState,
        output_dir: str,
        api_manager: ProjectApiManager,
        issue_prompt: str,
        print_callback: Callable[[dict], None] | None = None,
):
    """
    This version uses json data to process API calls, instead of using the OpenAI function calling.
    Advantage is that multiple API calls can be made in a single round.

    This function runs the agent subtask
    """
    start_round_no = state['start_round_no']
    info = state['info']

    msg_thread = MessageThread()
    msg_thread.add_system(subtask_prompts.sys_prompt)

    # TODO: revive this when plan stuff saved
    # plans_message = agent_globals.agent.get_plans_msg(msg_thread.messages, use_retrieved=False)
    # print_acr(
    #     agent_globals.agent.full_plan,
    #     "full_plan",
    #     print_callback=print_callback,
    # )
    # if plans_message:
    #     msg_thread.add_user(plans_message)
    #     print_acr(
    #         plans_message,
    #         "plans_message",
    #         print_callback=print_callback,
    #         )

    print_acr(
        subtask_prompts.api_prompt,
        f"api prompt",
        print_callback=print_callback,
    )
    msg_thread.add_user(subtask_prompts.api_prompt)
    mgr_msg = f"Here are the instructions from the engineering manager:\n\n{info}"
    print_acr(mgr_msg, "mgr_msg", print_callback=print_callback)
    msg_thread.add_user(mgr_msg)

    # shared context
    shared_ctx_msg = shared_context_template.format(context=agent_globals.agent.working_mem.get_context_tables())
    print_acr(shared_ctx_msg, "shared_ctx_msg", print_callback=print_callback)
    msg_thread.add_user(shared_ctx_msg)

    # TODO: gather relevant info to be analyzed in traj analysis
    end_round_no = start_round_no + globals.conv_round_limit + 1
    for round_no in range(start_round_no, end_round_no):
        api_manager.start_new_tool_call_layer()

        conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
        # save current state before starting a new round
        msg_thread.save_to_file(conversation_file)

        print_banner(f"CONTEXT RETRIEVAL ROUND {round_no}")

        res_text, *_ = common.SELECTED_MODEL.call(msg_thread.to_msg())

        msg_thread.add_model(res_text, tools=[])
        print_retrieval(res_text, f"round {round_no}", print_callback=print_callback)

        if "task_completed" in res_text:
            break

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

        formatted = []
        if json_api_calls:
            formatted.append("API calls:")
            for call in json_api_calls:
                formatted.extend([f"\n- `{call}`"])

        print_acr(
            "\n".join(formatted),
            "Agent-selected API calls",
            print_callback=print_callback,
        )

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
            msg = subtask_prompts.next_step_prompt

            msg_thread.add_user(msg)
            print_acr(
                msg,
                f"context retrieval round {round_no}",
                print_callback=print_callback,
            )
    else:
        logger.info("Too many rounds.")

    round_no += 1

    conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
    msg_thread.save_to_file(conversation_file)

    # sidechain summarize impt info n append to main loop
    # TODO: summarize via traj analysis
    answer = agent_globals.agent.planning_module.subtask_extract_ans(msg_thread.messages, issue_prompt)
    print_acr(
        answer,
        f"subtask ans and summary",
        print_callback=print_callback,
    )
    return {"messages": [HumanMessage(content=answer)], "start_round_no": round_no, "msg_thread": msg_thread}
