"""
utils for extracting info from ACR v2 trajectories, with a focus on building up a knowledge graph
"""
import copy
import json
import os
import uuid
import re

from cog_arch.memories import kg_data_models as km
from cog_arch.utils import path_to_module_notation

from ..memories import kg_data_models as km

namespace = uuid.NAMESPACE_DNS


def deduplicate_nodes(nodes):
    deduplicated_nodes = []
    seen_node_ids = set()
    for node in nodes:
        if node.get('exists', 'False') == 'True':
            node_id = node['node_id']
            if node_id not in seen_node_ids:
                seen_node_ids.add(node_id)
                deduplicated_nodes.append(node)
    return deduplicated_nodes


def create_numbered_nodes_str(nodes, include_importance=False):
    """
    Assumes unique nodes. Optionally includes importance score and reason.
    """
    numbered_nodes_str = ''
    counter = 1
    number_to_node_id = {}
    for node in nodes:
        node_id = node['node_id']
        node_type = node['node_type']
        numbered_nodes_str += f"entity_number {counter}. Name: {node_id}, Type: {node_type}"
        
        if include_importance:
            importance = node.get('importance')
            importance_reason = node.get('importance_reason')
            if importance is not None:
                numbered_nodes_str += f", Importance: {importance}"
            if importance_reason:
                numbered_nodes_str += f", Reason: {importance_reason}"
        
        numbered_nodes_str += "\n"
        number_to_node_id[counter] = node_id
        counter += 1
    return numbered_nodes_str, number_to_node_id


def prepare_code_summary_updates(code_summaries, number_to_node_id, issue_node_id):
    node_updates = []
    edge_updates = []
    for code_summary in code_summaries:
        if code_summary['entity_number'] not in number_to_node_id:
            print(f"Entity number {code_summary['entity_number']} not found in the nodes")
            continue
        node_id = number_to_node_id[code_summary['entity_number']]

        if code_summary['functionality']:
            functionality_node = km.FunctionalityNode(
                node_id=f"functionality_{str(uuid.uuid5(namespace, code_summary['functionality']))}",
                description=code_summary['functionality']
            )
            node_updates.append(functionality_node)
            edge_updates.append(km.BaseEdge(node_id, 'has_functionality', functionality_node.node_id))

        issue_relation_desc = code_summary['relationship_to_issue']
        if issue_relation_desc:
            prepare_issue_relation_update(node_id, issue_relation_desc, issue_node_id, edge_updates)

        intended_behavior = code_summary['intended_behavior']
        if intended_behavior:
            prepare_intended_behavior_updates(intended_behavior, node_updates, edge_updates, node_id)

        if code_summary['additional_info']:
            node_updates.append({'node_id': node_id, 'additional_info': code_summary['additional_info']})

    return [node.dict_clean() if hasattr(node, '__dict__') else node for node in node_updates], edge_updates


def prepare_intended_behavior_updates(intended_behavior, node_updates, edge_updates, node_id):
    behavior_node = km.IntendedBehaviorNode(
        node_id=f"intended_behavior_{str(uuid.uuid5(namespace, intended_behavior))}",
        node_type='intended_behavior',
        description=intended_behavior
    )
    node_updates.append(behavior_node)
    edge_updates.append(km.BaseEdge(node_id, 'has_intended_behavior', behavior_node.node_id))


def prepare_issue_relation_update(node_id, issue_relation_desc, issue_node_id, edge_updates):
    issue_edge = km.BaseEdge(node_id, 'relation_to_issue', issue_node_id, issue_relation_desc)
    edge_updates.append(issue_edge)


def is_v2_buggy_location_message(message):
    # for ACR v2
    cond_1 = message['role'] == 'user'
    return "Here are the possible buggy locations collected by someone else." in message['content'] and cond_1


def assert_same_int_suffixes(convo_files1, convo_files2):
    def extract_int_suffixes(files):
        return sorted([int(re.search(r'\d+', f).group()) for f in files])

    int_suffixes1 = extract_int_suffixes(convo_files1)
    int_suffixes2 = extract_int_suffixes(convo_files2)

    assert int_suffixes1 == int_suffixes2, f"Int suffixes do not match: {int_suffixes1} != {int_suffixes2}"
    print("Both lists of convo files have the same int suffixes.")
    return int_suffixes1


def create_reasoning_nodes_and_edges(patch_fail_analysis, patch_reasoning_flaws, patch_id, patch_test_summary, change_location_info, reasoning_updates):
    patch_fail_analysis_id = f"reasoning_{str(uuid.uuid5(namespace, patch_fail_analysis))}"
    patch_reasoning_flaws_id = f"reasoning_{str(uuid.uuid5(namespace, patch_reasoning_flaws))}"

    patch_fail_analysis_node = km.ReasoningNode(node_id=patch_fail_analysis_id, description=patch_fail_analysis)
    patch_reasoning_flaws_node = km.ReasoningNode(node_id=patch_reasoning_flaws_id, description=patch_reasoning_flaws)

    fail_analysis_edge = km.BaseEdge(patch_fail_analysis_id, 'analyzes_failure_of', patch_id)
    reasoning_flaws_edge = km.BaseEdge(patch_reasoning_flaws_id, 'identifies_reasoning_flaws_in', patch_id)

    # Create a new TestSuiteNode with the test_summary
    test_suite_node_id = f"test_suite_{patch_id}"
    test_suite_node = km.TestSuiteNode(node_id=test_suite_node_id, failed_tests_summary=patch_test_summary)

    node_updates = [patch_fail_analysis_node, patch_reasoning_flaws_node, test_suite_node]
    edge_updates = [fail_analysis_edge, reasoning_flaws_edge]

    # Process existing_updates
    for existing_update in reasoning_updates['existing_updates']:
        index = existing_update['index']
        reasoning_update = existing_update['reasoning_update']
        is_suspicious = existing_update['is_suspicious']

        # Use index to get change_location_id and patch_reason_id
        change_location_id = change_location_info[index]['change_location_id']
        patch_reason_id = change_location_info[index]['patch_reason_id']

        # Create a CodebaseLocationNode
        codebase_location_node = km.CodebaseLocationNode(
            node_id=change_location_id,
            relevance='suspicious' if is_suspicious else 'False'
        )
        node_updates.append(codebase_location_node)

        # Create a ReasoningNode
        reasoning_node_id = f"reasoning_{str(uuid.uuid5(namespace, reasoning_update))}"
        reasoning_node = km.ReasoningNode(
            node_id=reasoning_node_id,
            description=reasoning_update
        )
        node_updates.append(reasoning_node)

        # Create an edge from the new reasoning node to the patch_reason_id
        reasoning_flaw_edge = km.BaseEdge(reasoning_node_id, 'identifies_reasoning_flaws_in', patch_reason_id)
        edge_updates.append(reasoning_flaw_edge)

        # Add ContainsEdge from patch_reasoning_flaws_node to reasoning_node
        contains_edge = km.ContainsEdge(patch_reasoning_flaws_id, 'contains', reasoning_node_id)
        edge_updates.append(contains_edge)

    # Process new_updates
    for new_update in reasoning_updates['new_updates']:
        merge_arg_n_search_results_d(new_update, {}, node_updates, edge_updates, keys_mapping)
        codebase_location_node = node_updates[-1]
        codebase_location_node.relevance = 'suspicious' if new_update['is_suspicious'] else 'False'

        reasoning_update = new_update['reasoning_update']
        # Create a ReasoningNode
        reasoning_node_id = f"reasoning_{str(uuid.uuid5(namespace, reasoning_update))}"
        reasoning_node = km.ReasoningNode(
            node_id=reasoning_node_id,
            description=reasoning_update
        )
        node_updates.append(reasoning_node)

        # Create an edge from the new reasoning node to the patch_id
        reasoning_flaws_edge = km.BaseEdge(reasoning_node_id, 'updates_reasoning_of', codebase_location_node.node_id)
        edge_updates.append(reasoning_flaws_edge)

        # Add ContainsEdge from patch_reasoning_flaws_node to reasoning_node
        contains_edge = km.ContainsEdge(patch_reasoning_flaws_id, 'contains', reasoning_node_id)
        edge_updates.append(contains_edge)

    return node_updates, edge_updates


def merge_arg_n_search_results_d(arguments, api_result_d, entities, triplets, keys_mapping):
    accumulated_prefix = ''
    current_entity = km.CodebaseLocationNode(node_id='', node_type='', exists='True')
    for key, arg_key in keys_mapping.items():
        value = api_result_d.get(key) or arguments.get(arg_key)
        if value:
            subject = accumulated_prefix
            if key == 'code':
                accumulated_prefix += ':code'
                if 'code_str' in arguments:
                    # we create a separate node for the keywords (snippets) used to search the actual code
                    code_snippet_node = km.CodeSnippetNode(
                        node_id=f"code_snippet_{str(uuid.uuid5(namespace, arguments['code_str']))}",
                        code_str=arguments['code_str']
                    )
                    entities.append(code_snippet_node)
                    triplets.append(km.ContainsEdge(accumulated_prefix, 'contains', code_snippet_node.node_id))
            elif key == 'file':
                accumulated_prefix += path_to_module_notation(value)
            else:
                accumulated_prefix += f'.{value}'

            setattr(current_entity, arg_key, value)
            current_entity.node_type = arg_key.split('_')[0]
            current_entity.node_id = accumulated_prefix

            entities.append(copy.deepcopy(current_entity))

            if subject:
                triplets.append(km.ContainsEdge(subject, 'contains', accumulated_prefix))


keys_mapping = {
    'file': 'file_name',
    'class': 'class_name',
    'func': 'method_name',
    'code': 'code_str'
}

def get_messages_up_to_assistant(message_thread):
    """
    Extracts the front part of the message thread up to the first message where "role" is "assistant" (exclusive).
    
    Args:
        message_thread (list of dict): The message thread to process.
        
    Returns:
        list of dict: The front part of the message thread.
    """
    result = []
    for message in message_thread:
        if message.get('role') == 'assistant':
            break
        result.append(message)
    return result


