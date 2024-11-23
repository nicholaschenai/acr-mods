from typing import List, Union, Dict, Any
from langchain_core.pydantic_v1 import BaseModel, Field


class EditArea(BaseModel):
    relative_path: str = Field(
        description="relative path to the file that contains the entity that triggered the issue."
    )
    entity: str = Field(
        description="The entity (class, method or function) that triggered the issue."
    )


class EditAreas(BaseModel):
    edit_areas: List[EditArea] = Field(
        description="List of file paths and entities that triggered the issue."
    )
