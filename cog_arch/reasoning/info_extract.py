from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List
from cognitive_base.reasoning.base_lm_reasoning import BaseLMReasoning

from ..prompts.traj_analysis_prompts import traj_sys_prompt


code_summary_prompt = """
# Intro
The person received the results of the API calls (snippets of the codebase) and analyzed them in the message section below.
The person was tasked to answer some questions about the code

# Your task
Your task is to extract the answers to those questions in a specified format.
Optionally, if there is any additional information about the entities that the person thinks is important, you can include that as well.

## Questions to extract the answers for
1. What does this part of the code do? (`functionality`)
2. What is the relationship between this part of the code and the bug? (`relationship_to_issue`)
3. Given the issue description, what would be the intended behavior of this part of the code? (`intended_behavior`)

## Formatting
You will be given a numbered list of entities (files, classes, methods, or code associated with them).
From the analysis in the message below, extract the answers to the questions and associate them with their respective entities.
Use the numbering from the "Entities and numbering" section, NOT the message section.
If the analysis only gives partial answers for an entity, fill in the info to the best of your ability and leave the unanswered questions as a blank string.
You can skip an entity if the analysis does not provide any information about it.
Your reply should be a list of entities along with their answers to the questions.

## Entities and numbering
{numbered_nodes_str}

# Message containing the analysis
{message}
"""

class CodeSummary(BaseModel):
    entity_number: int = Field(
        description='The list number associated with the entity in the "Entities and numbering" section'
    )
    functionality: str = Field(description='Answer to: What does this part of the code do?')
    relationship_to_issue: str = Field(
        description='Answer to: What is the relationship between this part of the code and the bug?'
    )
    intended_behavior: str = Field(
        description=(
            "Answer to: Given the issue description, what would be the intended behavior of this part of the code?"
        )
    )
    additional_info: str = Field(
        description='Any additional information about the entity which the person thinks is important'
    )


class CodeSummaryOutput(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    code_summary_list: List[CodeSummary] = Field(
        description="List of entities by number and their answers to the questions"
    )


class InfoExtract(BaseLMReasoning):
    def __init__(
            self,
            name='info_extraction',
            **kwargs
    ):
        super().__init__(
            name=name,
            **kwargs
        )


    def extract_code_summaries(self, reasoning_output: str, numbered_nodes_str: str):
        """
        Extract code summaries from AI's reasoning.
        The code summary includes the functionality, relationship to the issue, and intended behavior.
        Intended behavior refers to what change the issue wants to see

        Args:
            reasoning_output (str): The AI's reasoning output.

        """
        result = self.lm_reason(
            sys_template=traj_sys_prompt + "\n# Response format\n{format_instructions}",
            human_template=code_summary_prompt,
            human_vars={
                'numbered_nodes_str': numbered_nodes_str,
                'message': reasoning_output,
            },
            structured=True,
            pydantic_model=CodeSummaryOutput,
            fallback={'code_summary_list': []}
        )
        return result['code_summary_list']
    