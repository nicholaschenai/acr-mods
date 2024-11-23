import copy
from ..prompts import patch_analysis_prompts as patch_prompts
from ..prompts.subtask_prompts import api_definitions

from cognitive_base.reasoning.base_lm_reasoning import BaseLMReasoning

from ..utils import parse_chat_history, safe_msg_append
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from typing import List, Dict


class ReasoningUpdate(BaseModel):
    index: int = Field(description="The index of the change location in the change_location_info list.")
    reasoning_update: str = Field(description="The flaw in the original reasoning for this location.")
    is_suspicious: bool = Field(description="Indicates if the location is still suspicious.")


class NewLocationReasoningUpdate(BaseModel):
    file_name: str = Field(description="File name of unmodified location")
    class_name: str = Field(description="Class name of unmodified location")
    method_name: str = Field(description="Method or function name of unmodified location")
    reasoning_update: str = Field(description="The flaw in the original reasoning for this location.")
    is_suspicious: bool = Field(description="Indicates if the location is still suspicious.")


class CombinedReasoningUpdates(BaseModel):
    existing_updates: List[ReasoningUpdate] = Field(description="List of reasoning updates for locations modified in the patch.")
    new_updates: List[NewLocationReasoningUpdate] = Field(description="List of reasoning updates for locations not modified in the patch.")


# Define the message template as a class-level constant
REASONING_UPDATE_PROMPT = """
Below is a numbered list of modified locations in module notation:
{numbered_list}

## Instructions
With your reasoning flaws identified just now, organize them by location.

### Modified locations
For each modified location, if the reasoning behind it is flawed, create an object where
- identify which location it belongs to and state the number associated with it in the `index` field
- extract the flaw in the original reasoning into the `reasoning_update` field
- indicate if the flaw still renders the location suspicious by filling in the `is_suspicious` field (boolean)
Put the list of these objects is the `existing_updates` field.

### New locations
If there are flaws in the reasoning behind any location that was not modified in the patch,
(e.g. the test results might suggest that the code should be modified in a new location),
then for each such location, create an object where
- state the file, class, and method name of the new location in the `file_name`, `class_name`, and `method_name` fields respectively, and if any of them are not applicable, leave them blank
- extract the flaw in the original reasoning into the `reasoning_update` field
- indicate if the flaw still renders the location suspicious by filling in the `is_suspicious` field (boolean)
Put the list of these objects is the `new_updates` field.

## Response format
{format_instructions}
"""

class PatchAnalysis(BaseLMReasoning):
    def __init__(
            self,
            name='patch_analysis',
            **kwargs
    ):
        super().__init__(
            name=name,
            **kwargs
        )
    """
    helper fns
    """

    """
    Reasoning Actions (from and to working mem)
    """
    # TODO: deprecate or at least continue existing chat rather that parse as string
    def summarize_patch_attempt(self, chat_history):
        """
        Summarizes a patch attempt based on the chat history.

        Parameters:
            chat_history (list): A list of chat messages.

        Returns:
            str: A formatted summary of the patch attempt.
        """
        summary = self.lm_reason(
            patch_prompts.summarize_patch_attempt_prompt,
            parse_chat_history(chat_history),
        )
        return summary

    def analyze_failed_patch(
            self,
            patch,
            issue,
            context,
            err_message,
            localization_prompt=''
    ):
        failed_patch_analysis = self.lm_reason(
            patch_prompts.analyze_failed_patch_prompt,
            patch_prompts.human_prompt,
            sys_vars={'api_definitions': api_definitions},
            human_vars={
                'issue': issue,
                'localization_prompt': localization_prompt,
                'patch': patch,
                'err_message': err_message,
                'context': context,
            },
        )

        return failed_patch_analysis

    def identify_reasoning_updates(self, msg_thread, patch_reasoning_flaws, change_location_info):
        """
        Identifies the reasoning updates based on the patch writing conversation history, test results, and change location information.

        Updates reasoning for existing locations
        Identifies new locations (probably from test results)

        Parameters:
            msg_thread (list): A list of chat messages
            change_location_info (list): A list of dictionaries containing change location information.
        
        """
        # TODO: future: update more attributes?
        msg = {'role': 'assistant', 'content': patch_reasoning_flaws}
        msg_thread = safe_msg_append(msg, msg_thread)

        # Transform change_location_info into a numbered list
        numbered_list = "\n".join(
            [f"{i}. {loc.get('change_location_id')}" for i, loc in enumerate(change_location_info)]
        )

        # Create a Pydantic parser for the combined model
        combined_parser = PydanticOutputParser(pydantic_object=CombinedReasoningUpdates)
        combined_format_instructions = combined_parser.get_format_instructions()

        # Construct the message for both existing and new locations
        combined_msg = {
            'role': 'user',
            'content': REASONING_UPDATE_PROMPT.format(
                numbered_list=numbered_list,
                format_instructions=combined_format_instructions
            )
        }

        # Call lm_reason for both existing and new locations
        combined_out = self.lm_reason(
            messages=safe_msg_append(combined_msg, msg_thread),
            structured=True,
            pydantic_model=CombinedReasoningUpdates,
            fallback={'existing_updates': [], 'new_updates': []}
        )

        return combined_out

    def analyze_test_failure(self, chat_history, test_results, change_location_info):
        """
        Analyzes test failures based on the patch writing conversation history and test results.

        Parameters:
            chat_history (list): A list of chat messages from the patch writing conversation.
            test_results (str): A formatted string of test results after applying the patch.

        Returns:
            str: A formatted analysis of why the test failed.
        """
        msg = {'role': 'user', 'content': patch_prompts.patch_fail_template.format(
            test_results=test_results, 
            patch_fail_task=patch_prompts.summary_task
            )}
        patch_test_summary = self.lm_reason(messages=chat_history+[msg])

        msg = {'role': 'user', 'content': patch_prompts.patch_fail_template.format(
            test_results=test_results, 
            patch_fail_task=patch_prompts.fail_analysis_task
            )}
        patch_fail_analysis = self.lm_reason(messages=chat_history+[msg])

        msg = {'role': 'user', 'content': patch_prompts.patch_fail_template.format(
            test_results=test_results, 
            patch_fail_task=patch_prompts.reasoning_flaws_task
            )}
        # msg = {'role': 'user', 'content': patch_prompts.patch_reasoning_prompt.format(test_results=test_results)}
        msg_thread = safe_msg_append(msg, chat_history)
        patch_reasoning_flaws = self.lm_reason(messages=copy.deepcopy(msg_thread))

        reasoning_updates = self.identify_reasoning_updates(msg_thread, patch_reasoning_flaws, change_location_info)
        return {
            'patch_fail_analysis': patch_fail_analysis,
            'patch_reasoning_flaws': patch_reasoning_flaws,
            'patch_test_summary': patch_test_summary,
            'reasoning_updates': reasoning_updates
        }
