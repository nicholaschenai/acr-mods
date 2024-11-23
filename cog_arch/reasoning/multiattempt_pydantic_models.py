from typing import List, Union, Dict, Any, Literal
from langchain_core.pydantic_v1 import BaseModel, Field


class DecideResponse(BaseModel):
    reasoning: str = Field(
        description="Step by step reasoning over the information at hand to decide next step."
    )
    decision: Literal["write_patch", "gather_info"] = Field(
        description="Your decision whether to write patch or gather info."
    )
    delegation_message: str = Field(
        description="Message to the person being delegated to."
    )


class DecidePatchResponse(BaseModel):
    reasoning: str = Field(
        description="Step by step reasoning over the information at hand to answer the question: "
                    "Do you have enough information at hand to write the patch?"
    )
    enough_info: bool = Field(
        description="Your answer to whether you have enough information to write the patch"
    )


class PruneResponse(BaseModel):
    reasoning: str = Field(
        description="Step by step reasoning over the information at hand to decide which database entries to keep."
    )
    indices_to_keep: List[int] = Field(
        description="Indices of the database to keep."
    )
