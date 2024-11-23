from typing import Callable

from langchain_core.messages import HumanMessage
from langgraph.graph import END

from app.api.manage import ProjectApiManager
from app.data_structures import MessageThread, FunctionCallIntent
from app.log import print_acr

# agent imports
from ..prompts.multi_attempt_prompts import shared_context_template

from ..utils import agent_globals, format_failed_tests
from ..utils.langgraph_utils import AgentState


def start_agent_write_patch(
        state: AgentState,
        output_dir: str,
        api_manager: ProjectApiManager,
        issue_prompt: str,
        print_callback: Callable[[dict], None] | None = None,
):
    info = state['info']
    buggy_area_msg = state['buggy_area_msg']
    print_acr(buggy_area_msg, "buggy_area_msg", print_callback=print_callback)

    msg_thread = MessageThread()
    # Dummy system message as itll be replaced during write_patch
    msg_thread.add_system("")
    msg_thread.add_user(issue_prompt)

    info_msg = f"Here is the information gathered:\n\n{info}"
    print_acr(info_msg, "info_msg", print_callback=print_callback)
    msg_thread.add_user(info_msg)

    msg_thread.add_user(buggy_area_msg)

    # shared context
    shared_ctx_msg = shared_context_template.format(context=agent_globals.agent.working_mem.get_context_tables())
    print_acr(shared_ctx_msg, "shared_ctx_msg", print_callback=print_callback)
    msg_thread.add_user(shared_ctx_msg)

    api_manager.start_new_tool_call_layer()

    write_patch_intent = FunctionCallIntent("write_patch", {}, None)
    api_manager.dispatch_intent(
        write_patch_intent, msg_thread, print_callback=print_callback
    )
    # TODO: handle failed extraction of patch

    # agent edits
    if agent_globals.agent.patch_is_correct:
        return {"correct_patch": True}
    else:
        # TODO: analyze patch failure
        # TODO: analysis refactor to new node?
        # TODO: upgrade summarization w those in traj analysis
        summary = agent_globals.agent.patch_analysis.summarize_patch_attempt(msg_thread.messages)
        # TODO: handle failed extraction of patch
        err_msg = format_failed_tests(agent_globals.agent.failed_tests)
        results = f"Patch attempt failed\n\n# Attempt Summary\n\n{summary}\n\n# Error message\n\n{err_msg}"

        print_acr(
            results,
            f"wrong patch results",
            print_callback=print_callback,
        )
        return {"messages": [HumanMessage(content=results)], "correct_patch": False}


def patch_router(state):
    if state['correct_patch']:
        return END
    return "agent"
