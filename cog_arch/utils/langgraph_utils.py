import operator

from typing import Annotated, Literal, TypedDict, Sequence
from langchain_core.messages import BaseMessage

from app.data_structures import MessageThread


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    info: str
    start_round_no: int
    iterations: int
    correct_patch: bool
    agent_decision: str
    msg_thread: MessageThread
    valid_buggy_areas: bool
    buggy_area_msg: str


def create_agent(llm, tools, system_message: str):
    """Create an agent. example from langgraph for reference"""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful AI assistant, collaborating with other assistants."
                " Use the provided tools to progress towards answering the question."
                " If you are unable to fully answer, that's OK, another assistant with different tools "
                " will help where you left off. Execute what you can to make progress."
                " If you or any of the other assistants have the final answer or deliverable,"
                " prefix your response with FINAL ANSWER so the team knows to stop."
                " You have access to the following tools: {tool_names}.\n{system_message}",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
    return prompt | llm.bind_tools(tools)


def parse_decide_response(json_output):
    # Initialize an empty string to hold the parsed information
    parsed_info = ""

    # Extracting information from the JSON output
    reasoning = json_output.get("reasoning", "No reasoning provided.")
    decision = json_output.get("decision", "No decision made.")
    delegation_message = json_output.get("delegation_message", "No delegation message.")

    # Formatting the extracted information into a presentable string
    parsed_info += f"# Reasoning:\n{reasoning}\n"
    parsed_info += f"# Decision:\n{decision}\n"
    parsed_info += f"# Delegation Message:\n{delegation_message}\n"

    return parsed_info
