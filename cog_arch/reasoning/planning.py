from langchain.output_parsers import PydanticOutputParser

from ..prompts import plan_extract_prompts as plan_prompts
from ..prompts import subtask_prompts

from .multiattempt_pydantic_models import DecideResponse

from cognitive_base.reasoning.base_lm_reasoning import BaseLMReasoning

from ..utils import parse_chat_history


class Planning(BaseLMReasoning):
    """
    A reasoning module within a cognitive architecture that specializes in extracting, formatting, and presenting plans. This module leverages language models to generate human-readable summaries and plans from chat history

    Attributes:
        name (str): The name of the module, defaulting to 'planning'.
        **kwargs: Additional keyword arguments passed to the BaseLMReasoning class.

    Methods:
        render_plans_message(plans): Static method that formats and returns a message summarizing the plans.
        render_plan_retrieval_context(chat_history): Static method that formats the chat history for plan retrieval.
        format_locations(locations, label): Static method that formats the locations of edits for display.
        render_gt_msg(edit_location_summary): Formats and returns a message comparing the suggested patch to the accepted patch.
        extract_plan(chat_history, edit_location_summary=None): Extracts and formats a plan based on the chat history and optionally an edit location summary.
    """

    def __init__(
            self,
            name='planning',
            **kwargs
    ):
        """
        Initializes the Planning module with a specified name and additional keyword arguments.

        Parameters:
            name (str): The name of the module, defaulting to 'planning'.
            **kwargs: Additional keyword arguments passed to the BaseLMReasoning superclass.
        """
        super().__init__(
            name=name,
            **kwargs
        )
        self.multiattempt_parser = PydanticOutputParser(pydantic_object=DecideResponse)

    """
    helper fns
    """

    @staticmethod
    def render_plans_message(plans):
        """
        Formats and returns a message of the plans.

        Parameters:
            plans (list): A list of plans to be summarized.

        Returns:
            str: A formatted message of the plans.
        """
        if not plans:
            return ''
        human_msg = plan_prompts.plans_msg_intro
        for plan in plans:
            human_msg += f"\n{'=' * 30 + ' Summary ' + '=' * 30}\n{plan}\n{'=' * 80}"
        return human_msg

    @staticmethod
    def render_plan_retrieval_context(chat_history):
        """
        Formats the chat history for plan retrieval.

        Parameters:
            chat_history (list): A list of chat messages.

        Returns:
            str: A formatted string representing the retrieval context.
        """
        retrieval_context = ''
        for message in chat_history:
            if message['role'] == 'user':
                retrieval_context += f"{message['content']}\n"
        return retrieval_context

    @staticmethod
    def format_locations(locations, label):
        """
        Formats the locations of edits for display.

        Parameters:
            locations (list): A list of(filename, MethodId) tuples. MethodId is called by str(MethodId) which gives class_name.method_name.
            label (str): A label for the type of locations (e.g., "Wrong Locations").

        Returns:
            str: A formatted string listing the locations.
        """
        if not locations:
            return f"{label}: None\n"
        formatted = f"{label}:\n"
        for filename, method_id in locations:
            formatted += f"  - File: {filename}, Method: {str(method_id)}\n"
        return formatted

    def render_gt_msg(self, edit_location_summary):
        """
        Formats and returns a message comparing the suggested patch to the accepted patch.

        Parameters:
            edit_location_summary (tuple): A tuple containing lists of wrong, correct, and missing locations.

        Returns:
            str: A formatted summary message.
        """
        wrong_locations, correct_locations, missing_locations = edit_location_summary

        summary = plan_prompts.gt_intro
        summary += self.format_locations(wrong_locations, "Wrong Locations")
        summary += self.format_locations(correct_locations, "Correct Locations")
        summary += self.format_locations(missing_locations, "Missing Locations")

        return summary

    """
    Reasoning Actions (from and to working mem)
    """

    def extract_plan(self, chat_history, edit_location_summary=None):
        """
        Extracts and formats a plan based on the chat history and optionally an edit location summary.

        Parameters:
            chat_history (list): A list of chat messages.
            edit_location_summary (tuple, optional): A tuple containing lists of wrong, correct, and missing locations.

        Returns:
            tuple: A tuple containing the full plan and the current plan formatted as strings.
        """
        # flexible: allow no location summary, for future use eg more efficient plan
        if edit_location_summary:
            chat_history.append(
                {
                    "role": "user",
                    "content": self.render_gt_msg(edit_location_summary)
                }
            )

        human_msg = parse_chat_history(chat_history)

        full_plan = self.lm_reason(
            plan_prompts.sys_template,
            human_msg,
            fallback=''
        )

        problem_summary = self.extract_blocks(full_plan, identifier='summary')
        plan = self.extract_blocks(full_plan, identifier='plan')
        current_plan = f"# Problem Summary\n{problem_summary}\n# High-level plan\n{plan}\n"

        return full_plan, current_plan

    # for deprecated multiattempt_decide
    def multiattempt_decide(self, messages):
        out = self.structured_lm_reason(
            messages=messages,
            pydantic_model=DecideResponse,
        )
        return out

    def subtask_extract_ans(self, chat_history, issue_prompt):
        """
        Extracts answers to subtasks based on the chat history and issue prompt.

        Parameters:
            chat_history (list): A list of chat messages.
            issue_prompt (str): The issue prompt.

        Returns:
            str: A formatted message containing the extracted answers.
        """
        parsed_chat_history = parse_chat_history(chat_history)
        human_msg = f"# Issue\n\n{issue_prompt}\n\n# Conversation\n\n{parsed_chat_history}"
        out = self.lm_reason(
            subtask_prompts.extract_ans_prompt,
            human_msg,
        )
        return out

