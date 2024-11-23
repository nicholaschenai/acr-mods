import copy
import uuid
import re

from typing import List, Dict, Tuple
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

from ..memories import kg_data_models as km

from ..utils import path_to_module_notation
from ..utils.traj_parsers import parse_api_result, separate_code_blocks
from ..utils import info_extraction_utils as ie_utils
from ..utils import traj_analysis_utils as ta_utils
from ..utils.info_extraction_utils import keys_mapping

from cognitive_base.reasoning.base_lm_reasoning import BaseLMReasoning

namespace = uuid.NAMESPACE_DNS


# TODO
class EntityExtractionOutput(BaseModel):
    node_id: str
    node_type: str


# TODO
class RelationshipOutput(BaseModel):
    entity1: str
    entity2: str
    relation: str


class PatchLocationReasoning(BaseModel):
    index: int = Field(description="The index of the change location in the numbered list.")
    func: str = Field(description="The function or method that was edited, if any. Leave blank if not applicable.")
    patch_location_reasoning: str = Field(description="The reasoning behind the patch for the specific location.")


class PatchLocationReasoningList(BaseModel):
    patch_location_reasoning_list: List[PatchLocationReasoning]


patch_location_reasoning_prompt = """
Below is a numbered list of change locations up to the class level:
{numbered_list}

## Instructions
For each modification in the patch, 
- identify which change location it belongs to and state the number associated with it in the `index` field
- state the function/method that was edited if any in the `func` field (leave a blank string if not applicable)
- extract the reasoning behind the patch for that location into the `patch_location_reasoning` field

## Response format
{format_instructions}
"""


class GraphEleExtract(BaseLMReasoning):
    def __init__(
            self,
            name='info_extraction',
            **kwargs
    ):
        super().__init__(
            name=name,
            **kwargs
        )

    def from_tool_call(self, fn_call: dict, call_result_str: str):
        """
        Extract entities and relations from API calls and results.

        function call output formats:
        search_class: file, class, code, where code only shows till method level, wrapped in code blks
          if too many, will just contain the file part with (n matches), without code block
        search_class_in_file: code blocks of file, class, code. somehow examples show full code while
         the search fn seems to suggest only till method level? no truncation if too many results
        search_method_in_file : same as above except with func. note that sometimes its a fn so no cls.
         no truncate, full code
        search_method_in_class: shows up to n results, anything above will collapse to file lvl. shows fullcode
        search_method: if too many, collapse to file level. else show in code blocks
        search_code: same as above
        search_code_in_file: if too many, collapse to method level (file, func), else in code blocks

        # specrover has extra args line_no_str, window_size_str
        #             line_no_str (str): The line number. (1-based)
        #             window_size_str (str): The number of lines before and after the line number.

        Args:
            fn_call (dict): A dictionary of function call info. It contains the following keys:
                func_name: The name of the function being called ("search_method_in_class").
                arguments: A dictionary of arguments passed to the function, which can have:
                    file_name, class_name, method_name, code_str for ACR v1 and 20240621 eval
                call_ok: A boolean indicating whether the API call was successful.
        """
        # TODO: future: read error msgs for more info. sometimes when finding X in Y, err msg
        #   gives clues to whether Y exists or X exists
        # TODO: future: can disambiguate when subject does not contain object,
        #  by checking for individual entities existence
        # TODO: future: Create a node for the tool call result

        entities = []
        triplets = []
        arguments = fn_call.get('arguments', {})
        # TODO: future: add search query nodes so that we can know some form of 'completeness'
        #   eg if we search_class('foo') and returns 2 results, then can say there are only these 2 and
        #   not more.

        if fn_call['call_ok']:
            # if results too long, truncated to non code blocks list
            code_blocks_list, non_code_blocks_list = separate_code_blocks(call_result_str)
            for call_result in code_blocks_list:
                merge_arg_n_search_results(arguments, call_result, entities, triplets, keys_mapping)
            for call_result_text in non_code_blocks_list:
                for line in call_result_text.split('\n'):
                    merge_arg_n_search_results(arguments, line, entities, triplets, keys_mapping)
        else:
            # Create a single codebase location node with all arguments
            node_id = ta_utils.construct_function_call(fn_call)
            location_node = km.CodebaseLocationNode(node_id=node_id, node_type='failed_tool_call', exists='False')
            
            # Fill in the node with all arguments
            for key, value in arguments.items():
                setattr(location_node, key, value)
            
            entities.append(location_node)

        return entities, triplets

    def from_issue_loc(self, bug_loc_call_list, bug_location_search_results, issue_node_id):
        """
        Extract entities from suspected issue locations.

        Args:
            bug_loc_call_list (List[Dict[str, str]]): A list of dictionaries containing suspected issue locations.
            bug_location_search_results (List[str]): A list of messages containing suspected issue locations.
        """
        # TODO: future: handle case where if no method in bug location call, means AI wants to add a new method to the cls
        # TODO: disambiguate if during patchwrite, the iterations are for reproducer or non reproducer
        nodes = []
        triplets = []

        # parse intended behavior from bug_loc_call_list
        intended_behavior_dict = prepare_bug_loc_intended_behavior_dict(bug_loc_call_list)

        # TODO: future: sometimes bug loc search results contain a cls level code search, or more comprehensive code,
        #  so when replacing, need to check if the new code is more comprehensive than the old one

        # extract entities from bug_location_search_results
        for message_content in bug_location_search_results:
            code_blocks_list, non_code_blocks_list = separate_code_blocks(message_content)
            for call_result in code_blocks_list:
                merge_arg_n_search_results({}, call_result, nodes, triplets, keys_mapping)

        # fill in intended behavior
        # separate list for new intended behavior nodes since we r iterating thru a node list
        new_nodes = merge_intended_behavior_to_issue_loc(nodes, intended_behavior_dict, issue_node_id, triplets)
        return nodes + new_nodes, triplets

    def from_patch(self, raw_patch, extracted_patch, patch_summary, chat_history):
        """
        Extracts graph elements from the patch.

        Args:
            raw_patch: The raw patch content.
            extracted_patch: The extracted patch content in git diff

        Returns:
            tuple: (node_updates, edge_updates) containing the extracted nodes and edges.
        """
        entities = []
        triplets = []

        patch_id = f"patch_{str(uuid.uuid5(namespace, extracted_patch))}"
        prepare_patch_node(patch_id, extracted_patch, raw_patch, patch_summary, entities)

        cls_change_locs = extract_file_and_class_from_diff(extracted_patch)

        # Create a numbered list of file and class changes
        numbered_list = "\n".join([f"{i}. file: {loc.get('file')}, class: {loc.get('class', 'N/A')}" for i, loc in enumerate(cls_change_locs)])

        # Create a Pydantic parser for the new model
        parser = PydanticOutputParser(pydantic_object=PatchLocationReasoningList)
        # Construct the message for lm_reason
        msg = {
            'role': 'user',
            'content': patch_location_reasoning_prompt.format(
                numbered_list=numbered_list,
                format_instructions=parser.get_format_instructions()
            )
        }

        # Call lm_reason once for all changes
        out = self.lm_reason(
            messages=chat_history + [msg],
            structured=True,
            pydantic_model=PatchLocationReasoningList,
            fallback={'patch_location_reasoning_list': []}
        )

        # change_location_info = {}
        change_loc_info = []
        # Process the results
        merge_patch_loc_and_reasoning(out['patch_location_reasoning_list'], cls_change_locs, patch_id, entities, triplets, change_loc_info)
        
        return entities, triplets, patch_id, change_loc_info

    def from_tests(self, patch_node_id, failed_test_results):
        """
        Extract entities n triplets from patches and test results.

        Args:
            failed_test_results (List[Dict[str, str]]): list of dictionaries containing failed test cases and their tracebacks.
            keys:
            `test_name`, `test_path`, `traceback`.
        """
        entities = []
        triplets = []

        # Create a TestSuiteNode
        test_suite_node_id = f"test_suite_{patch_node_id}"
        test_suite_node = km.TestSuiteNode(
            node_id=test_suite_node_id,
            tests_passed=len(failed_test_results) == 0
        )
        entities.append(test_suite_node)

        # TODO: future: 'applied_to' edge from patch to issue node
        for test_result in failed_test_results:
            test_case_node_id = f"{test_result['test_path']}.{test_result['test_name']}"
            test_case_node = km.TestCaseNode(
                node_id=test_case_node_id,
                test_name=test_result['test_name'],
                test_path=test_result['test_path'],
                description=test_result['description']
            )
            entities.append(test_case_node)

            traceback = test_result['traceback']
            test_result_node_id = f"test_result_{test_case_node_id}_{str(uuid.uuid5(namespace, traceback))}"
            test_result_node = km.TestResultNode(
                node_id=test_result_node_id,
                test_name=test_result['test_name'],
                test_path=test_result['test_path'],
                traceback=traceback,
                test_passed=False,
            )
            entities.append(test_result_node)

            # Create an edge between the test suite and the test result
            test_suite_to_result_edge = km.BaseEdge(test_suite_node_id, 'contains', test_result_node_id)
            triplets.append(test_suite_to_result_edge)

            # Create an edge between the test case and the test result
            test_case_to_result_edge = km.BaseEdge(test_case_node_id, 'has_test_result', test_result_node_id)
            triplets.append(test_case_to_result_edge)

            # Create an edge between the patch and the failed test
            patch_to_test_result_edge = km.BaseEdge(patch_node_id, 'causes_failure', test_result_node_id)
            triplets.append(patch_to_test_result_edge)

        return entities, triplets

    # TODO
    def entities_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Extract entities from text via reasoning

        Args:
            text (str): The input text.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing extracted entities.
        """
        sys_template = "You are an AI that extracts entities from text."
        human_template = "Extract entities from the following text: {text}"
        sys_vars = {}
        human_vars = {'text': text}

        result = self.lm_reason(
            sys_template=sys_template,
            human_template=human_template,
            sys_vars=sys_vars,
            human_vars=human_vars,
            structured=True,
            pydantic_model=List[EntityExtractionOutput],
            fallback=[]
        )
        return [entity.dict() for entity in result]


    # TODO
    def extract_relationships(self, analysis_message: str) -> List[Dict[str, str]]:
        """
        Extract relationships between entities from AI's analysis message.

        Args:
            analysis_message (str): The AI's analysis message.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing relationships between entities.
        """
        sys_template = "You are an AI that extracts relationships between entities from analysis messages."
        human_template = "Extract relationships from the following analysis message: {analysis_message}"
        sys_vars = {}
        human_vars = {'analysis_message': analysis_message}

        result = self.lm_reason(
            sys_template=sys_template,
            human_template=human_template,
            sys_vars=sys_vars,
            human_vars=human_vars,
            structured=True,
            pydantic_model=List[RelationshipOutput],
            fallback=[]
        )
        return [relationship.dict() for relationship in result]


def merge_arg_n_search_results(arguments, call_result, entities, triplets, keys_mapping):
    api_result_d = parse_api_result(call_result)
    # handle truncated results where not every line is a result, might be explanatory text
    if not api_result_d:
        return
    ie_utils.merge_arg_n_search_results_d(arguments, api_result_d, entities, triplets, keys_mapping)


def prepare_bug_loc_intended_behavior_dict(bug_loc_call_list):
    # create dict of node id to intended behavior
    intended_behavior_dict = {}
    for bug_location_call in bug_loc_call_list:
        accumulated_prefix = ''
        for key in ['file', 'class', 'method']:
            value = bug_location_call.get(key)
            if value:
                if key == 'file':
                    accumulated_prefix += path_to_module_notation(value)
                else:
                    accumulated_prefix += f'.{value}'
        intended_behavior_dict[accumulated_prefix] = bug_location_call.get('intended_behavior')
    return intended_behavior_dict


def merge_intended_behavior_to_issue_loc(location_nodes, intended_behavior_dict, issue_node_id, triplets):
    intended_behavior_nodes = []
    for node in location_nodes:
        node_id = node.node_id
        if node_id in intended_behavior_dict:
            node.relevance = 'suspected_issue_location'
            edge_desc = "is suspected location for issue"
            ie_utils.prepare_issue_relation_update(node_id, edge_desc, issue_node_id, triplets)
        intended_behavior = intended_behavior_dict.get(node_id, '')
        if intended_behavior:
            ie_utils.prepare_intended_behavior_updates(intended_behavior, intended_behavior_nodes, triplets, node_id)
    return intended_behavior_nodes


def extract_file_and_class_from_diff(diff_content: str) -> List[Dict[str, str]]:
    file_pattern = re.compile(r'^diff --git a/(.+) b/(.+)$')
    class_pattern = re.compile(r'^@@ .+ @@\s*class\s+(\w+)')

    changes = []
    current_file = None
    current_class = None

    for line in diff_content.split('\n'):
        file_match = file_pattern.match(line)
        if file_match:
            if current_file:
                change = {'file': current_file}
                if current_class:
                    change['class'] = current_class
                changes.append(change)
            current_file = file_match.group(2)
            current_class = None
            continue

        class_match = class_pattern.match(line)
        if class_match:
            current_class = class_match.group(1)
            continue

    if current_file:
        change = {'file': current_file}
        if current_class:
            change['class'] = current_class
        changes.append(change)

    return changes


def prepare_patch_node(patch_id, extracted_patch, raw_patch, patch_summary, entities):
    patch_node = km.PatchNode(
        node_id=patch_id,
        diff=extracted_patch,
        description=raw_patch,
        summary=patch_summary
    )
    entities.append(patch_node)



def merge_patch_loc_and_reasoning(patch_loc_reasoning_list, cls_change_locs, patch_id, entities, triplets, change_loc_info):
    for patch_location_reasoning_d in patch_loc_reasoning_list:
        index = patch_location_reasoning_d['index']
        cls_change_location = copy.deepcopy(cls_change_locs[index])

        if patch_location_reasoning_d['func']:
            cls_change_location['func'] = patch_location_reasoning_d['func']

        ie_utils.merge_arg_n_search_results_d({}, cls_change_location, entities, triplets, keys_mapping)
        change_location_id = entities[-1].node_id
        edge = km.BaseEdge(patch_id, 'applied_to_location', change_location_id)
        triplets.append(edge)
        
        reasoning_result = patch_location_reasoning_d['patch_location_reasoning']
        # Extract reasoning from the raw_patch using lm_reason
        # originally for bulk patch instead of fine grained location
        # reasoning_result = self.lm_reason(
        #     sys_template=patch_reasoning_prompt,
        #     human_template=raw_patch,
        # )

        # Create a ReasoningNode
        patch_reason_id = f"reasoning_{str(uuid.uuid5(namespace, reasoning_result))}"
        reasoning_node = km.ReasoningNode(
            node_id=patch_reason_id,
            description=reasoning_result
        )
        entities.append(reasoning_node)

        # Create an edge linking the reasoning to the patch node
        # reasoning_to_patch_edge = km.BaseEdge(reasoning_node.node_id, 'explains', patch_node_id)
        # triplets.append(reasoning_to_patch_edge)

        reasoning_to_loc_edge = km.BaseEdge(reasoning_node.node_id, 'explains_patch_location', change_location_id)
        triplets.append(reasoning_to_loc_edge)

        patch_to_reason_edge = km.BaseEdge(patch_id, 'has_reasoning', reasoning_node.node_id)
        triplets.append(patch_to_reason_edge)

        # change_location_info[change_location_id] = patch_reason_id
        change_loc_info.append({'change_location_id': change_location_id, 'patch_reason_id': patch_reason_id})

# deprecated
patch_reasoning_prompt = """
Below is a developer's justification for the patch they are about to write. 
Your task is to extract the reasoning behind the patch.
Remove redundant info, but ensure all details are captured.
"""

# old code for failed tool call
# # future: not as consistent with positive tool call esp the id; reconcile one day
# for key in list(keys_mapping.values()):
#     if key in arguments:
#         entity = None
#         if key in ['file_name', 'class_name', 'method_name']:
#             entity = km.CodebaseLocationNode(node_id=arguments[key], node_type=key.split('_')[0])
#             setattr(entity, key, arguments[key])
#         elif key == 'code_str':
#             entity = km.CodeSnippetNode(
#                 node_id=f"code_snippet_{str(uuid.uuid5(namespace, arguments[key]))}",
#                 code_str=arguments[key]
#             )
#         entities.append(entity)

# if len(entities) == 1:
#     # call not ok and only 1 entity, means doesnt exist
#     entities[0].exists = 'False'
# else:
#     # call not ok and 2 entities, both unknown
#     for entity in entities:
#         entity.exists = 'Unknown'

# # Determine relationships
# if len(entities) == 2:
#     triplets.append(km.ContainsEdge(entities[0].node_id, 'does_not_contain', entities[1].node_id))
