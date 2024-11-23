from typing import List

from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

from cognitive_base.reasoning.base_lm_reasoning import BaseLMReasoning


class GraphReasoner(BaseLMReasoning):
    def __init__(
            self,
            name='graph_reasoner',
            **kwargs
    ):
        super().__init__(
            name=name,
            **kwargs
        )
        # Initialize the parser with the Pydantic model
        self.parser = PydanticOutputParser(pydantic_object=ExpansionRequest)
        self.format_instructions = self.parser.get_format_instructions()
        self.parallel_api = True

    def ask_for_expansion(self, chat_history: list[dict], info_str: str) -> dict:
        """
        Method where, given a chat history, reasoner is presented with a numbered list of nodes and edges 
        from the knowledge graph with info about previous attempts to resolve the issue
        reasoner must copy down relevant info, and choose which nodes or edges it needs more info about

        Parameters:
            chat_history (list[dict]): The chat history to consider.
            info_str (str): The string containing information about nodes and edges, in a numbered list

        Returns:
            dict: A structured response indicating which elements to expand.
        """
        human_msg = ask_for_expansion_prompt.format(
            info_str=info_str,
            format_instructions=self.format_instructions
        )
        out = self.lm_reason(
            messages=chat_history + [{"role": "user", "content": human_msg}],
            pydantic_model=ExpansionRequest,
            structured=True,
            fallback={'relevant_info': '', 'elements_to_expand': []},
        )
        return out

    def extract_important_info(self, chat_history: list[dict], expanded_elements: list[str]) -> str:
        """
        Extracts important information from the expanded elements.

        Parameters:
            chat_history (list[dict]): The chat history to consider.
            expanded_elements (list[str]): The expanded elements from the knowledge graph.

        Returns:
            str: A string containing the important information extracted.
        """
        # Construct a list of messages, each containing a chat history with one expanded element
        messages_list = [
            chat_history + [{"role": "user", "content": extraction_prompt.format(elements_info=ele)}]
            for ele in expanded_elements
        ]
        
        # Use the language model to extract important information

        # async ver, disable for now as ACR uses ProcessPoolExecutor
        # out = self.lm_reason(messages_list=messages_list, fallback=[])

        # sync ver
        out = []
        for messages in messages_list:
            extracted_str = self.lm_reason(messages=messages, fallback='')
            out.append(extracted_str)

        return '\n\n'.join(out)

class ExpansionRequest(BaseModel):
    relevant_info: str = Field(description='A space to copy down relevant info from the knowledge graph.')
    elements_to_expand: List[int] = Field(
        description="Index of relevant elements which you need more information about"
    )

ask_for_expansion_prompt = """
## Instruction
Later you will be given potentially relevant pieces of information from previous attempts at fixing the issue. 
It will be in the form of a knowledge graph, with nodes and edges in a numbered list format.

You must:
- If any part of the info below is relevant to your main goal, write it down in a way that is contextualized to your goal, into the `relevant_info` field. Leave a blank string if there is no relevant info.
- If you require further info about any of the nodes or edges, state their numbering from the list into the `elements_to_expand` field and you will be given more information about them.

### Format Instructions
{format_instructions}

## Knowledge graph info
{info_str}
"""

extraction_prompt = """
## Instruction
Later you will be given potentially relevant pieces of information from previous attempts at fixing the issue. 
It will be in the form of a knowledge graph, with nodes and edges

Your task: If any part of the info below is relevant to your main goal, write it down in a way that is contextualized to your goal.
Leave a blank string if there is no relevant info.

## Knowledge graph info
{elements_info}
"""

# old
extraction_prompt_v1 = """
## Instruction
Later you will be given potentially relevant pieces of information from previous attempts at fixing the issue. 
It will be in the form of a knowledge graph, with nodes and edges

Your task: Write down (from the knowledge graph) ONLY the info that is relevant to your main goal.
Leave a blank string if there is no relevant info.

## Knowledge graph info
{elements_info}
"""

ask_for_expansion_prompt_old = """
## Instruction
Later you will be given potentially relevant pieces of information from previous attempts at fixing the issue. 
It will be in the form of a knowledge graph, with nodes and edges in a numbered list format.

You must:
- Write down (from the knowledge graph) ONLY the info that is relevant to your main goal, into the `relevant_info` field. Leave a blank string if there is no relevant info.
- If you require further info about any of the nodes or edges, state their numbering from the list into the `elements_to_expand` field and you will be given more information about them.

### Format Instructions
{format_instructions}

## Knowledge graph info
{info_str}
"""