import json

from cognitive_base.reasoning.base_lm_reasoning import BaseLMReasoning

from . import traj_analysis_pydantic_models as traj_pm
from .plan_pydantic_models import EditAreas
from .traj_analysis_pydantic_models import ToolCallRelevance, PatternAnalysis, EditAreaSnippets

from ..prompts import traj_analysis_prompts as traj_prompts
from ..prompts.subtask_prompts import api_definitions

from ..utils import parse_chat_history
# mixin to contain utils
from ..utils import traj_analysis_utils as ta_utils
from ..utils.traj_analysis_utils import TrajectoryAnalysisUtils


class TrajectoryAnalysis(BaseLMReasoning, TrajectoryAnalysisUtils):
    def __init__(
            self,
            name='traj_analysis',
            **kwargs
    ):
        super().__init__(
            name=name,
            **kwargs
        )
        self.issue_statement = ''
        self.qn_idx = 0

    """
    helper fns
    """

    """
    Reasoning Actions (from and to working mem)
    """
    def trajectory_reason(
            self,
            messages,
            traj_task_prompt,
            pydantic_model=None,
            structured=False,
    ):
        """
        generic template for reasoning over a trajectory
        """
        sys_template = traj_prompts.traj_sys_prompt
        if pydantic_model:
            structured = True
            sys_template += "# Response format\n{format_instructions}"
        out = self.lm_reason(
            sys_template=sys_template,
            human_template=traj_prompts.traj_human_template,
            human_vars={
                'issue_prompt': self.issue_statement,
                'api_definitions': api_definitions,
                'messages': messages,
                'traj_task_prompt': traj_task_prompt,
            },
            pydantic_model=pydantic_model,
            structured=structured,
        )
        return out

    def extract_result_snippets(self, indi_tool_call_msg, questions_answered):
        # extract snippets of tool call which answered questions
        out = self.trajectory_reason(
            messages=indi_tool_call_msg,
            traj_task_prompt=traj_prompts.result_snippets_prompt.format(questions_answered=questions_answered),
            pydantic_model=traj_pm.ToolCallSnippets,
        )
        return out

    def extract_edit_area_snippets(self, tool_call_msg, tool_call):
        # extract areas that exist and prompt ask which are / arent relevant,
        api_call = ta_utils.construct_function_call(tool_call)
        out = self.trajectory_reason(
            messages=tool_call_msg,
            traj_task_prompt=traj_prompts.edit_area_snippets_prompt.format(api_call=api_call),
            pydantic_model=EditAreaSnippets,
        )
        return out

    def lm_extract_patterns_from_calls(self, call_str):
        out = self.trajectory_reason(call_str, traj_prompts.pattern_analysis_prompt, pydantic_model=PatternAnalysis)
        return out

    def reasoning_tool_call_association(self, tool_call_analysis_msg, tool_call_display, question_d):
        """
        LM Reasoning to associate tool calls with questions
        Args:
            tool_call_analysis_msg:
            tool_call_display:
            question_d:

        Returns:

        """
        association_out = self.trajectory_reason(
            messages=tool_call_analysis_msg,
            traj_task_prompt=traj_prompts.tool_call_help_prompt.format(
                question=question_d['question_asked'],
                answer=question_d.get('answer', ''),
                tool_call_display=tool_call_display,
            ),
            pydantic_model=traj_pm.ToolCallHelpResponse,
        )
        return association_out

    def associate_questions_with_tool_calls(
            self,
            tool_call_layer_info,
            fully_answered_qns,
            partially_answered_qns,
            tool_call_analysis_msg,
    ):
        # Display tool calls and number them
        tool_call_display = "\n".join([f"{i}. {ta_utils.construct_function_call(tool_call_d['tool_call'])}"
                                       for i, tool_call_d in enumerate(tool_call_layer_info, 1)])

        tool_call_to_questions = {}

        for question_d in fully_answered_qns + partially_answered_qns:
            # Get LLM to reason out with which tool call(s) helped answer the questions
            association_out = self.reasoning_tool_call_association(
                tool_call_analysis_msg,
                tool_call_display,
                question_d,
            )

            # Map tool calls to the questions they helped answer
            ta_utils.update_tool_call_question_associations(
                association_out,
                tool_call_layer_info,
                tool_call_to_questions,
                question_d
            )

        return tool_call_to_questions

    def loop_extract_result_snippets(
            self,
            tool_call_to_questions,
            tool_call_numbering,
    ):
        # then for each tool call that answered any qns, extract relevant snippets
        for tool_call_index, questions_d_list in tool_call_to_questions.items():
            tool_call_d = tool_call_numbering[tool_call_index]
            relevant_result_snippets_info = {'reasoning': '', 'relevant_result_snippets': "", 'is_relevant': False}
            if tool_call_d["tool_call"]["call_ok"]:
                # Display questions answered by the tool call
                # questions_display = "\n".join(
                #     f"Question: {questions_d['question_asked']}\nAnswer: {questions_d['answer']}\n\n"
                #     for questions_d in questions_d_list
                # )
                questions_display = "\n".join(
                    f"Question: {questions_d['question_asked']}\n\n"
                    for questions_d in questions_d_list
                )
                # Extract relevant snippets via LLM
                relevant_result_snippets_info = self.extract_result_snippets(
                    tool_call_d["result"],
                    questions_display,
                )
                relevant_result_snippets_info['is_relevant'] = True
            tool_call_d.update(relevant_result_snippets_info)

    def extract_questions_asked(self, open_questions, reasoning_msg):
        # extract list of qns asked in reasoning_msg. dedupe with open_questions
        open_questions_formatted = '\n'.join(f'- {q}' for q in open_questions) if open_questions else 'None'
        out = self.trajectory_reason(
            reasoning_msg['content'],
            traj_prompts.questions_asked_prompt.format(open_questions_formatted=open_questions_formatted),
            pydantic_model=traj_pm.QuestionsAskedResponse,
        )
        return out['questions_asked']

    def extract_questions_validation(self, tool_call_analysis_msg, questions_asked, open_questions):
        """
        Given questions_asked and open_questions, looks at the messages and returns if the questions are
        fully / partially/ not answered,
        and if fully or partially answered, what is the answer then.
        """
        # future: can run in parallel

        # Initialize the list to store validation results
        fully_ans = []
        partially_ans = []
        partially_ans_carry = []
        not_ans = []

        # Iterate over each question in questions_asked and open_questions
        for question_d in questions_asked + open_questions:
            # Check if the question is answered in the messages
            ans = question_d.get("answer", '')
            out = self.trajectory_reason(
                messages=tool_call_analysis_msg,
                traj_task_prompt=traj_prompts.answer_extraction_prompt.format(
                    question=question_d['question_asked'],
                    partial_answer=f'Additionally, there was a partial answer: {ans}' if ans else '',
                ),
                pydantic_model=traj_pm.AnswerExtractionResponse,
            )
            if out['is_fully_answered']:
                question_d['answer'] = out['answer']
                fully_ans.append(question_d)
            elif out['answer']:
                question_d['answer'] = out['answer']
                partially_ans.append(question_d)
            elif question_d.get('answer', ''):  # if there was a partial answer, carry it over
                partially_ans_carry.append(question_d)
            else:
                question_d['answer'] = ''
                not_ans.append(question_d)

        return fully_ans, partially_ans, partially_ans_carry, not_ans

    def analyze_layer(
            self,
            tool_call_msg,
            reasoning_msg,
            analysis_msg,
            tool_call_layer_info,
            open_questions_d,
    ):
        """
        main method to perform analysis on a tool call layer. processes:
        - extract questions asked
        - check if questions are fully / partially/ not answered
        - check which API result(s) answered the qn,
        - and extract relevant snippets if so
        """
        # from reasoning msg, prompt ask what are the questions asked, and the subject (eg. method, class) if any
        # deduplicate with open qns frm prev layer
        questions_asked = self.extract_questions_asked(
            [q['question_asked'] for q in open_questions_d],
            reasoning_msg
        )

        # then frm results, ask if questions are fully / partially/ not answered
        # update open_questions
        tool_call_analysis_msg = parse_chat_history([tool_call_msg, analysis_msg])
        fully_ans, partially_ans, partially_ans_carry, not_ans = self.extract_questions_validation(
            tool_call_analysis_msg,
            questions_asked,
            open_questions_d,
        )

        # check which API result(s) answered the qn
        tool_call_to_questions = self.associate_questions_with_tool_calls(
            tool_call_layer_info,
            fully_ans,
            partially_ans,
            tool_call_analysis_msg
        )

        tool_call_numbering = {i: tool_call_d for i, tool_call_d in enumerate(tool_call_layer_info, 1)}

        # extract relevant snippets of API call that answered the qn
        self.loop_extract_result_snippets(
            tool_call_to_questions,
            tool_call_numbering,
        )

        return fully_ans, partially_ans + partially_ans_carry + not_ans

    def find_patterns_from_calls(self, layer_or_seq, mode='layers'):
        """
        # find patterns, eg blanket "this area all not relevant"
        """
        # collate calls
        relevant_calls, no_results_calls, irrelevant_results_calls = self.collate_api_calls(layer_or_seq, mode=mode)

        # from this, format into prompt and use lm_reason. output schema is list of strings

        # relevant calls: display call, relevant snippets, ask lm to reason for patterns
        positive_patterns = {'reasoning': '', 'patterns': []}
        if relevant_calls:
            positive_call_str = traj_prompts.positive_call_template.format(
                relevant_calls_formatted=self.format_relevant_tool_call_results(relevant_calls)
            )
            positive_patterns = self.lm_extract_patterns_from_calls(positive_call_str)

        # no_results_calls and irrelevant_results_calls: display calls, mention if they r no result or irrelevant
        #  then ask lm to reason for patterns
        negative_patterns = {'reasoning': '', 'patterns': []}
        negative_call_str = ''
        if no_results_calls:
            negative_call_str += f"These calls returned no results:\n{self.format_tool_calls(no_results_calls)}\n"
        if irrelevant_results_calls:
            irrelevant_call_str = self.format_tool_calls(irrelevant_results_calls)
            negative_call_str += f"These calls returned results that are irrelevant:\n{irrelevant_call_str}\n"
        if negative_call_str:
            negative_patterns = self.lm_extract_patterns_from_calls(negative_call_str)

        return positive_patterns, negative_patterns

    def analyze_buggy_location(self, buggy_location_msg, buggy_tool_call_layer):
        # extract relevant code in buggy area
        # check if API result is relevant, and extract relevant snippets if so
        # similar to loop_extract_result_snippets
        if not buggy_location_msg:
            return {}

        tool_call_layer_info = []
        for tool_call in buggy_tool_call_layer:
            relevant_result_snippets_info = {'reasoning': '', 'is_relevant': False, 'relevant_result_snippets': ""}
            if tool_call["call_ok"]:
                # for each successful tool call, ask if tool call result was relevant to the issue
                print('extracting relevant snippets frm buggy loc')
                relevant_result_snippets_info = self.extract_edit_area_snippets(
                    buggy_location_msg,
                    tool_call
                )
                relevant_result_snippets_info['is_relevant'] = True
            relevant_result_snippets_info['tool_call'] = tool_call
            tool_call_layer_info.append(relevant_result_snippets_info)

        buggy_layer_analysis = {
            'tool_call_msg': buggy_location_msg,
            'tool_call_layer_info': tool_call_layer_info,
        }
        return buggy_layer_analysis

    def summarize_patch(self, patch_msg):
        # patch get hi lvl concept
        if not patch_msg:
            return {}
        # future: results of patch if its run, and whats the outcome
        # future: actually need to take failed result into account for whether things are relevant?
        patch_summary = self.trajectory_reason(
            messages=patch_msg,
            traj_task_prompt=traj_prompts.summarize_patch_prompt
        )
        return patch_summary

    # TODO: this should probably be in a script. methods in this cls should focus on reasoning only
    def analyze_tool_calls(self, messages, tool_call_layers):
        """
        The main method to Analyze a failed trajectory
        """
        # append unique index in each tool call in each tool_call_layer for association
        self.append_tool_call_uid(tool_call_layers)

        prev_msg_idx, self.issue_statement = ta_utils.get_issue_statement(messages)

        # ACRv1: penultimate tool call layer gets code in buggy area (area to edit)
        # Note: buggy location call doesnt return full function call, and errors might not contain full args
        # so we handle them in bulk
        buggy_location_msg, buggy_tool_call_layer = '', []
        patch_msg = ''
        open_questions, fully_answered_qns = [], []

        tool_call_sequence_info = []
        for tool_call_layer in tool_call_layers:
            # invalid API call has [] as tool_call_layer for v1. in v2, final blank is tool call on buggy loc
            # future: handle API call errors? might contain reasoning info in failed calls
            if not tool_call_layer:
                continue

            # for each tool call layer, find the corresponding message ("Result of tool call")
            tool_call_msg, tool_msg_idx, tool_call_layer_info = ta_utils.find_tool_call_msg(
                messages,
                prev_msg_idx,
                tool_call_layer
            )

            # handle buggy location and patch messages
            if tool_call_layer_info is None:
                if ta_utils.is_v1_buggy_location_message(tool_call_msg):
                    buggy_location_msg = tool_call_msg['content']
                    buggy_tool_call_layer = tool_call_layer
                    prev_msg_idx = tool_msg_idx + 1
                    continue
                elif ta_utils.is_patch_message(tool_call_msg, tool_call_layer):
                    patch_msg = messages[tool_msg_idx + 1]['content']
                    prev_msg_idx = tool_msg_idx + 2
                    continue

            # get reasoning and analysis messages
            reasoning_msg, analysis_msg = ta_utils.get_reasoning_and_analysis_messages(messages, tool_msg_idx)

            # analyze layer
            new_fully_answered_qns, open_questions = self.analyze_layer(
                tool_call_msg,
                reasoning_msg,
                analysis_msg,
                tool_call_layer_info,
                open_questions,
            )
            fully_answered_qns.extend(new_fully_answered_qns)

            tool_call_sequence_info.extend(tool_call_layer_info)
            prev_msg_idx = tool_msg_idx + 2

        # find patterns, eg blanket "this area all not relevant"
        positive_patterns, negative_patterns = self.find_patterns_from_calls(tool_call_sequence_info, mode='seq')
        # Future: label submodules, class, methods, areas as relevant or not.
        # 	- extract frm tool call
        # 	- some of the search results, tho no path input, can give path output. also use this as info

        traj_analysis_result = {
            'tool_call_sequence_info': tool_call_sequence_info,
            'positive_patterns': positive_patterns,
            'negative_patterns': negative_patterns,
            'buggy_location_msg': buggy_location_msg,
            'buggy_tool_call_layer': buggy_tool_call_layer,
            'patch_msg': patch_msg,
            'open_questions': open_questions,
            'fully_answered_qns': fully_answered_qns,
        }
        return traj_analysis_result

    # iirc i separated this out cos ill be reusing this thruout. if not, merge back to construct_summarize_traj
    def summarize_trajectory(self, trajectory_reduced_info):
        out = self.trajectory_reason(trajectory_reduced_info, traj_prompts.summarize_traj_prompt)
        return out

    def construct_summarize_traj(
            self,
            tool_call_sequence_info,
            open_questions,
            fully_answered_qns,
            buggy_layer_analysis,
            patch_analysis
    ):
        """
        summarize trajectory from tool call layers, buggy layer analysis, patch analysis
        """
        layers_condensed = self.format_qns_ans(tool_call_sequence_info, open_questions, fully_answered_qns)
        trajectory_reduced_info = self.append_buggy_layer_n_patch_info(
            layers_condensed,
            buggy_layer_analysis,
            patch_analysis
        )
        traj_summary = self.summarize_trajectory(trajectory_reduced_info)

        return traj_summary

    def extract_edit_areas(self, parsed_chat_history):
        out = self.lm_reason(
            sys_template=traj_prompts.extract_edit_area_prompt,
            human_template=parsed_chat_history,
            sys_vars={'edit_area_example': json.dumps(traj_prompts.edit_area_example, indent=4)},
            pydantic_model=EditAreas,
            structured=True,
        )
        return out['edit_areas']
