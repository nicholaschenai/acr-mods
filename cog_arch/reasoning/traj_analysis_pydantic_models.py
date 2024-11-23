from typing import List, Union, Dict, Any
from langchain_core.pydantic_v1 import BaseModel, Field


class ToolCallRelevance(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    is_relevant: bool = Field(
        description="Whether the result of the API call is relevant to the hypothesis / intent or issue."
    )
    relevant_result_snippets: str = Field(description='Extract relevant snippets of the API call result here')


class PatternSubject(BaseModel):
    pattern: str = Field(
        description=
        'Non-obvious pattern identified from the API call analyses, which can be an observation or instruction'
    )
    subject: str = Field(
        description=(
            'The subject of the pattern identified, if any. '
            'Eg. a specific method of a class or a folder in the repo.'
            'Use the full path or module notation if applicable.'
        )
    )


class PatternAnalysis(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    patterns: List[PatternSubject]


class EditAreaSnippets(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    relevant_result_snippets: str = Field(description='Extract relevant snippets of the API call result here')


class QuestionsAskedSubject(BaseModel):
    question_asked: str = Field(description='Intent / hypothesis of the person, phrased as a question in 1 sentence')
    subject: str = Field(
        description=(
            'The subject of the pattern identified, if any. '
            'Eg. a specific method of a class or a folder in the repo.'
            'Use the full path or module notation if applicable.'
        )
    )


class QuestionsAskedResponse(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'You could state the raw intents and hypotheses of the person here.'
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    questions_asked: List[QuestionsAskedSubject]


class AnswerExtractionResponse(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    answer: str = Field(
        description=(
            "The answer to the person's question (be it full or partial), if available. "
            "Reply with a blank string if the is no new information towards the answer. "
            "(Partial answers previously will be carried over if you reply with a blank string)"
            "If you are including new info when there is a previous partial answer, treat this as an UPDATE operation "
            "and copy over the relevant parts of the previous partial answer in your reply."
        )
    )
    is_fully_answered: bool = Field(description="Whether the question is fully answered")


class ToolCallHelpResponse(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    tool_call_indices: List[int] = Field(
        description='List of the API call indices that contributed to the answer'
    )


class ToolCallSnippets(BaseModel):
    reasoning: str = Field(
        description=(
            'A blank space for you to write down your reasoning step by step. '
            'This reasoning section will be discarded later so distil the results into the sections below.'
        )
    )
    relevant_result_snippets: str = Field(
        description=(
            "Extract snippets of the API call result which contributed to answering "
            "the person's questions about the codebase here."
        )
    )


