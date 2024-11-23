from typing import List, Union, Dict, Any
from langchain_core.pydantic_v1 import BaseModel, Field

from cognitive_base.reasoning.pydantic_models import BaseRule


class RuleExtractResponse(BaseModel):
    problem_summary: str = Field(
        description="Summary of the problem that the person was trying to solve."
    )
    attempt_summary: str = Field(
        description="Summary of the attempts made by the person, in terms of Observation, Thought, or Action."
    )
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the rules into the section below.'
        )
    )
    rules: List[BaseRule]

