import functools

from typing import Callable

from langgraph.graph import StateGraph
from langchain_core.runnables.graph import MermaidDrawMethod

from app import globals
from app.api.manage import ProjectApiManager
from app.inference import prepare_issue_prompt

from app.log import print_banner, print_issue

from ..prompts.multi_attempt_prompts import sys_prompt, human_prompt
from ..prompts.subtask_prompts import api_definitions

from ..decisions import agent_decide as ad
from ..decisions.gather_info import start_agent_gather_info
from ..decisions.write_patch import start_agent_write_patch, patch_router
from ..decisions.prune_working_mem import prune_working_mem, prune_router

# from ..utils import agent_globals
from ..utils.agent_globals import agent
from ..utils.langgraph_utils import AgentState
from ..utils.validate_buggy_areas import validate_buggy_areas, buggy_area_router


def run_one_task_multi_attempt(
    output_dir: str,
    api_manager: ProjectApiManager,
    problem_stmt: str,
    print_callback: Callable[[dict], None] | None = None,
) -> bool:
    """
    Main entry point to run inference on one task.
    agent w multi attempts

    Args:
        output_dir (str): Path to the output directory.
        api_manager (ProjectApiManager): The already-initialized API manager.
        problem_stmt (str): The original problem statement submitted to the task issue.
    """
    print_banner("Starting ACR agent multiattempt on the following issue")
    print_issue(problem_stmt)

    issue_prompt = prepare_issue_prompt(problem_stmt)
    # Add another user message about fault localization
    localization_prompt = ''
    if globals.enable_sbfl:
        localization_result, _, _ = api_manager.fault_localization()
        localization_prompt += "An external analysis tool has been deployed to identify the suspicious code to be fixed. You can choose to use the results from this tool, if you think they are useful."
        localization_prompt += "The tool output is as follows:\n"
        localization_prompt += localization_result

    agent.localization_prompt = localization_prompt
    agent.traj_analysis.issue_statement = issue_prompt

    multi_attempt_msgs = agent.traj_analysis.construct_messages(
        sys_template=sys_prompt,
        human_template=human_prompt,
        sys_vars={'api_definitions': api_definitions},
        human_vars={
            'issue_prompt': issue_prompt,
            'localization_prompt': localization_prompt,
        },
    )
    messages = multi_attempt_msgs[0]

    # Define a new graph
    workflow = StateGraph(AgentState)

    gather_info_node = functools.partial(
        start_agent_gather_info,
        output_dir=output_dir,
        api_manager=api_manager,
        print_callback=print_callback,
        issue_prompt=issue_prompt,
    )
    write_patch_node = functools.partial(
        start_agent_write_patch,
        output_dir=output_dir,
        api_manager=api_manager,
        print_callback=print_callback,
        issue_prompt=issue_prompt,
    )
    validate_buggy_areas_node = functools.partial(
        validate_buggy_areas,
        output_dir=output_dir,
        api_manager=api_manager,
        print_callback=print_callback,
    )

    workflow.add_node("agent", ad.agent_decide_process)

    workflow.add_node("delegate_write_patch", ad.delegate_write_patch)
    workflow.add_node("decide_info_to_gather", ad.decide_info_to_gather)
    workflow.add_node("delegate_gather_info", ad.delegate_gather_info)

    workflow.add_node("prune_working_mem", prune_working_mem)

    workflow.add_node("gather_info", gather_info_node)
    workflow.add_node("validate_buggy_areas", validate_buggy_areas_node)
    workflow.add_node("write_patch", write_patch_node)

    workflow.add_edge("delegate_write_patch", "prune_working_mem")

    workflow.add_edge("decide_info_to_gather", "delegate_gather_info")
    workflow.add_edge("delegate_gather_info", "prune_working_mem")
    workflow.add_edge("gather_info", "agent")

    workflow.add_conditional_edges(
        "agent",
        ad.decision_router,
    )
    workflow.add_conditional_edges(
        "prune_working_mem",
        prune_router,
    )
    workflow.add_conditional_edges(
        "validate_buggy_areas",
        buggy_area_router,
    )
    # TODO: after patch, analyze why fail
    workflow.add_conditional_edges(
        "write_patch",
        patch_router,
    )

    workflow.set_entry_point("agent")
    agent_graph = workflow.compile()

    # graph_for_viz = agent_graph.get_graph()
    # print(graph_for_viz.draw_mermaid())

    # # Generate the image
    # image_data = graph_for_viz.draw_mermaid_png(draw_method=MermaidDrawMethod.API)
    # # Save the image to disk
    # with open(output_dir+'/langgraph_viz.png', 'wb') as f:
    #     f.write(image_data)

    # Use the Runnable
    final_state = agent_graph.invoke({
        "messages": messages,
        "iterations": 0,
        "start_round_no": 0,
        "correct_patch": False,
    })

    # print(final_state["messages"])
    # TODO: if successful trajectory, generalize n learn subplan
    return True
