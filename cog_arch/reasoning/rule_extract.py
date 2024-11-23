from pprint import pp

from cognitive_base.reasoning.rule_extraction import RuleExtraction

from ..prompts.rule_extract_prompts import sys_message
from .rule_extract_pydantic_models import RuleExtractResponse

from app.log import print_acr
from ..utils import parse_chat_history


class BugfixRuleExtraction(RuleExtraction):
    """
    A class for extracting bugfix rules from chat history.

    This class extends the RuleExtraction class to specifically handle
    the extraction of bugfix rules from a given chat history. rules
    can be rigid or soft

    Attributes:
        verbose (bool): A flag to enable verbose logging of the extraction process.
    """
    def __init__(
            self,
            **kwargs,
    ):
        super().__init__(
            **kwargs,
        )

    """
    helper fns
    """

    """
    Reasoning Actions (from and to working mem)
    """

    def from_example(self, chat_history):
        """
        Extracts bugfix rules from the given chat history.

        This method processes the chat history to extract insights and
        formulates them into rules. These rules are categorized into rigid
        and soft based on their nature. The extraction process leverages
        the `extract_rules` method from the parent class.

        Args:
            chat_history (str): The chat history containing the bugfix conversation.

        Returns:
            dict: A dictionary containing the extracted rules and summaries of the problem,
            attempt, and reasoning behind the bugfix.
        """
        out = self.extract_rules(
            sys_message,
            parse_chat_history(chat_history),
            pydantic_model=RuleExtractResponse,
        )

        if self.verbose:
            print_acr(out.get('problem_summary', ''), 'problem_summary')
            print_acr(out.get('attempt_summary', ''), 'attempt_summary')
            print_acr(out.get('reasoning', ''), 'reasoning')
            pp(out.get('rules', {}))
        return out
