import os
import json
import time
import uuid

from argparse import ArgumentParser
from pprint import pp

from cog_arch.agents.acr_agent import AcrAgent
from cog_arch.memories.kg_data_models import IssueNode
import cog_arch.memories.kg_data_models as km

import cog_arch.utils.traj_file_io as tfu
import cog_arch.utils.traj_analysis_utils as ta_utils
import cog_arch.utils.info_extraction_utils as ie_utils
import cog_arch.utils as u

from cognitive_base.utils import lm_cache_init

namespace = uuid.NAMESPACE_DNS

results_folder_path = './data/20240621_autocoderover-v20240620/trajs'

# TODO: future: refactor these fns to take in raw data since during inference, wont hv log files
# TODO: future: the fns here represent decision process, so only include transforms and agent actions
# def update_graph_from_context_step(agent: AcrAgent, tool_call_layer_info, messages, prev_msg_idx, task):
#     """
#     a step during context collection, which consists of reasoning msg (reason what API to use),
#     tool call msg (result of tool call / API call), and analysis msg (analyzing tool call result)
#     """
#     # extract entities from tool call via rule based n update KG
#     nodes_in_layer = update_graph_from_tool_call(agent, tool_call_layer_info)

#     # extract from analysis message via LM reasoning, update KG
#     update_graph_from_analysis_reasoning_msg(agent, messages, prev_msg_idx, nodes_in_layer, task)


def update_graph_from_tool_call(agent: AcrAgent, tool_call_layer_info):
    entities_in_layer = []
    for tool_call_info in tool_call_layer_info:
        tool_call = tool_call_info['tool_call']
        tool_call_result = tool_call_info['result']
        entities, triplets = agent.graph_ele_extract.from_tool_call(tool_call, tool_call_result)

        # print("\nTool call:")
        # pp(tool_call)
        # print("\nTool call result:", tool_call_result)
        # print("\nEntities:")
        # pp(entities)
        # print("\ntriplets:")
        # pp(triplets)

        entities_in_layer.extend([entity_instance.dict_clean() for entity_instance in entities])
        agent.declarative_mem.add_graph_elements(nodes=entities, edges=triplets, verbose=True)
        # agent.declarative_mem.add_graph_elements(nodes=entities, edges=triplets)
        # time.sleep(0.1)
    unique_nodes_in_layer = ie_utils.deduplicate_nodes(entities_in_layer)
    return unique_nodes_in_layer


def update_graph_from_analysis_msg(agent: AcrAgent, analysis_msg, unique_nodes_in_layer, task):
    """
    Extracts graph elements from reasoning and analysis messages during context collection
    Args:
        messages:
        tool_msg_idx:
        agent:
        nodes_in_layer:

    Returns:

    """
    # update KG from code summaries in analysis message
    numbered_nodes_str, number_to_node_id = ie_utils.create_numbered_nodes_str(unique_nodes_in_layer)
    code_summaries = agent.info_extract.extract_code_summaries(analysis_msg['content'], numbered_nodes_str)
    node_updates, edge_updates = ie_utils.prepare_code_summary_updates(code_summaries, number_to_node_id, task)
    agent.declarative_mem.add_graph_elements(nodes=node_updates, edges=edge_updates, verbose=True)
    # agent.declarative_mem.add_graph_elements(nodes=node_updates, edges=edge_updates)


def update_graph_from_agent_choice(agent, message_thread, nodes):
    """
    Extracts graph elements from agent choice message
    Args:
        agent:
        message_thread:
        unique_nodes_in_layer:
    """
    updated_nodes = [agent.declarative_mem.dbs['knowledge_graph'].get_node(node['node_id'], return_id=True) for node in nodes]
    
    # Use the modified function to get the numbered nodes string with importance details
    numbered_nodes_str, number_to_node_id = ie_utils.create_numbered_nodes_str(
        updated_nodes, 
        include_importance=True
    )

    # TODO: use graph reasoner to take in message_thread n numbered nodes string, lm_reason to get entity updates
    # TODO: entity updates in the form of entity_id, importance score, importance reason. entity id is numbered node id if old entity, otherwise new entity id as str. existing entities not mention will not be updated

    # TODO: from obs, LM propose new relations, prompt for causal rs

    # TODO: get related triplets by all entities mentioned

    # TODO: LM propose edits (maybe prioritize replacement) to triplets, prompt for causal rs. rmb use numbered interface

    # TODO: store results


def update_graph_from_issue_loc_msg(agent: AcrAgent, run_path, search_path, task):
    """
    Extracts graph elements from bug location message (the tool call on the buggy location)
    Args:
        agent:
        run_path:
        search_path:
        task:

    Returns:

    """
    # handle bug location messages
    bug_loc_proxy_messages = tfu.get_latest_convo(search_path, prefix='agent_proxy')
    # outer list is a list of retries due to parsing errors so only the final one might be valid
    bug_loc_proxy_message = bug_loc_proxy_messages[-1][-1]
    assert bug_loc_proxy_message['role'] == 'assistant', "bug location message should be from the assistant"
    try:
        bug_loc_call = json.loads(bug_loc_proxy_message['content'])['bug_locations']
        assert bug_loc_call, "bug locations should not be empty"
        # Note: these bug locations are parsed by LM, havent verified via API call yet, so they are only used for
        # intended behavior as its harder to parse from patch convo
    except Exception as e:
        print("Error parsing bug location message. possibly proxy failed to extract bug locations\n")
        print(f"error message: {repr(e)}")

    bug_loc_search_results = tfu.get_bug_loc_search_results(run_path)
    n_updates, e_updates = agent.graph_ele_extract.from_issue_loc(bug_loc_call, bug_loc_search_results, task)
    agent.declarative_mem.add_graph_elements(nodes=n_updates, edges=e_updates, verbose=True)
    # agent.declarative_mem.add_graph_elements(nodes=n_updates, edges=e_updates)


# TODO: consider deprecating since theres also patch summary in test summary
def update_graph_from_patch_write(agent: AcrAgent, raw_patch, extracted_patch, patch_convo):
    """
    Extracts graph elements from patch write conversation
    Args:
        agent:

    Returns:

    """

    patch_summary = agent.traj_analysis.summarize_patch(raw_patch)
    n_updates, e_updates, patch_id, change_location_info = agent.graph_ele_extract.from_patch(
        raw_patch,
        extracted_patch,
        patch_summary,
        patch_convo
    )
    # crossref methods n warn if no match
    for change_location in change_location_info:
        change_location_id = change_location['change_location_id']
        if change_location_id not in agent.declarative_mem.dbs['knowledge_graph'].graph.nodes:
            print(f"\nWARNING: change location node {change_location_id} not found in knowledge graph\n")
    agent.declarative_mem.add_graph_elements(nodes=n_updates, edges=e_updates, verbose=True)
    # agent.declarative_mem.add_graph_elements(nodes=n_updates, edges=e_updates)
    return patch_id, change_location_info


def update_graph_from_test_suite_results(agent: AcrAgent, failed_test_results, patch_id, change_location_info, patch_convo):
    """
    Extracts graph elements from test suite results and updates the knowledge graph.

    Args:
        agent: The agent responsible for managing the knowledge graph.

        failed_test_results: list of dictionaries containing failed test cases and their tracebacks.
            keys:
            `test_name`, `test_path`, `traceback`.
    """

    n_updates, e_updates = agent.graph_ele_extract.from_tests(patch_id, failed_test_results)

    # TODO: future: rmb formatting is for django, need to make it more general
    
    # Analyze test failure
    # future: success analysis?
    if failed_test_results:
        patch_analysis_out = agent.patch_analysis.analyze_test_failure(
            patch_convo,
            u.format_failed_tests(failed_test_results),
            change_location_info
        )

        reasoning_nodes, reasoning_edges = ie_utils.create_reasoning_nodes_and_edges(
            patch_id=patch_id, 
            change_location_info=change_location_info, 
            **patch_analysis_out
        )

        n_updates.extend(reasoning_nodes)
        e_updates.extend(reasoning_edges)

    agent.declarative_mem.add_graph_elements(nodes=n_updates, edges=e_updates, verbose=True)
    # agent.declarative_mem.add_graph_elements(nodes=n_updates, edges=e_updates)

    # TODO: retrieval
    # TODO: have generic method for access ele so it updates frequency of access, list of access times, last accessed time
    # TODO: node-triplet similarity
    # TODO: obs-triplet similarity
    # TODO: final score: importance + similarity + frequency (so rule based nodes will only score on similarity so its like hiding them, prioritizing LM based stuff)

    # TODO: reasoning after test results
    # TODO: mention that only need tests related to issue to pass
    # TODO: do the usual maintenance (importance update, edge replacement or deletion)
    # TODO: when reasoning, upvote by actual use in frequency (real importance)
    # TODO: any new info wna search (to carry over to ctx collection)

def kg_construct_main(agent:AcrAgent, task:str):
    i = 0
    while True:
        run_path = os.path.join(results_folder_path, task, f"output_{i}")
        if os.path.exists(run_path):
            print(f"Processing run {i}")
            i += 1
        else:
            break

        search_path = os.path.join(run_path, 'search')

        # Load tool call layers and the messages associated with ctx retrieval
        tool_call_layers = tfu.get_tool_call_layers(search_path)
        messages = tfu.get_latest_convo(search_path, prefix='search_round')

        front_messages = ie_utils.get_messages_up_to_assistant(messages)

        prev_msg_idx, issue_statement = ta_utils.get_issue_statement(messages)
        agent.traj_analysis.issue_statement = issue_statement
        issue_node = IssueNode(node_id=task, description=issue_statement)
        agent.declarative_mem.add_node_with_checks(verbose=True, **issue_node.dict_clean())

        for tool_call_layer in tool_call_layers:
            # invalid API call has [] as tool_call_layer for v1. in v2, final blank is tool call on buggy loc
            # future: handle API call errors? might contain reasoning info in failed calls
            if not tool_call_layer:
                continue

            tool_call_msg, tool_msg_idx, tool_call_layer_info = ta_utils.find_tool_call_msg(
                messages,
                prev_msg_idx,
                tool_call_layer,
                version=2,
            )

            # Combine the updates from tool call and analysis reasoning message
            # update_graph_from_context_step(agent, tool_call_layer_info, messages, tool_msg_idx, task)

            # extract entities from tool call via rule based n update KG
            unique_nodes_in_layer = update_graph_from_tool_call(agent, tool_call_layer_info)

            context_step_msgs = ta_utils.get_reasoning_and_analysis_messages(messages, tool_msg_idx, include_between=True)
            analysis_msg = context_step_msgs[-1]
            # TODO: future: extract from reasoning msg

            update_graph_from_analysis_msg(agent, analysis_msg, unique_nodes_in_layer, task)

            # TODO: LM constructed entities and relations
            update_graph_from_agent_choice(agent, front_messages + context_step_msgs, unique_nodes_in_layer)
            
            prev_msg_idx = tool_msg_idx + 2

        update_graph_from_issue_loc_msg(agent, run_path, search_path, task)

        extracted_patch_fnames = tfu.get_all_convo_fname(run_path, prefix='extracted_patch', suffix='diff')

        # extract from execution on test suite results
        test_suite_fnames = tfu.get_all_convo_fname(run_path, prefix='run_test_suite', suffix='log')
        # check that each extracted patch has its corresponding test suite results
        # md raw patch file not asserted cos can have raw patch but cant extract
        int_suffixes = ie_utils.assert_same_int_suffixes(extracted_patch_fnames, test_suite_fnames)

        for suffix, extracted_patch_fname, test_suite_fname in zip(int_suffixes, extracted_patch_fnames, test_suite_fnames):
            raw_patch, extracted_patch, patch_convo = tfu.load_patch_data(suffix, run_path, extracted_patch_fname)
            # TODO: future: extract from patchwrite convo
            patch_id, change_location_info = update_graph_from_patch_write(agent, raw_patch, extracted_patch, patch_convo)

            test_suite_results = tfu.extract_failed_tests(os.path.join(run_path, test_suite_fname), verbose=True)
            update_graph_from_test_suite_results(agent, test_suite_results, patch_id, change_location_info, patch_convo)
            # agent.declarative_mem.update_time()

    try:
        agent.declarative_mem.visualize_knowledge_graph(figsize=(30, 20), task_name=task)
    except Exception as e:
        print(f"Error visualizing knowledge graph: {e}")


if __name__ == "__main__":
    # import here to prevent circular imports
    from app.main import add_task_related_args
    from app.model.register import register_all_models

    register_all_models()
    parser = ArgumentParser()
    add_task_related_args(parser)
    args = parser.parse_args()

    # LM caching
    lm_cache_init("lm_cache")

    # task = "django__django-14608"
    task = "django__django-13321"

    ckpt_dir = args.ckpt_dir if args.ckpt_dir else args.output_dir
    agent = AcrAgent(
        agent_model=args.model,
        ckpt_dir=ckpt_dir,
        verbose=args.verbose,
        debug_mode=args.debug_mode,
    )

    kg_construct_main(agent, task)

