from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from ..utils import agent_globals

from ..prompts import multi_attempt_prompts as mp

from ..utils.langgraph_utils import AgentState, parse_decide_response

from app.log import print_acr


def agent_decide_process(state: AgentState):
    iterations = state['iterations'] + 1
    if iterations >= agent_globals.agent.max_multiattempt_iterations:
        return {'agent_decision': 'END'}

    # step 1: analyze info at hand, decide if enough info to write patch
    messages = state['messages']
    context = agent_globals.agent.working_mem.get_context_tables()
    out = agent_globals.agent.generic_reasoner.multiattempt_decide(
        messages,
        context,
    )
    # step 2: extract out decision
    agent_decision = "write_patch" if out['enough_info'] else "gather_info"

    formatted_msg = out['reasoning']
    print_acr(
        formatted_msg,
        f"multiattempt decision iter {iterations}",
    )

    return {
        'messages': [HumanMessage(content=mp.multiattempt_decide_prompt), AIMessage(content=formatted_msg)],
        'agent_decision': agent_decision,
        'iterations': iterations,
    }


def decision_router(state: AgentState):
    agent_decision = state['agent_decision']
    if agent_decision == 'gather_info':
        return 'decide_info_to_gather'
    elif agent_decision == 'write_patch':
        return 'delegate_write_patch'
    elif agent_decision == 'END':
        return END


def delegate_write_patch(state):
    messages = state['messages']
    context = agent_globals.agent.working_mem.get_context_tables()
    out = agent_globals.agent.generic_reasoner.delegate_write_patch(
        messages,
        context,
    )
    return {
        'messages': [HumanMessage(content=mp.delegate_write_patch_prompt), AIMessage(content=out)],
        'info': out,
    }


def decide_info_to_gather(state):
    context = agent_globals.agent.working_mem.get_context_tables()
    out = agent_globals.agent.generic_reasoner.decide_info_to_gather(
        state['messages'],
        context,
    )
    return {
        'messages': [HumanMessage(content=mp.decide_info_to_gather_prompt), AIMessage(content=out)],
        'info': out,
    }


def delegate_gather_info(state):
    messages = state['messages']
    context = agent_globals.agent.working_mem.get_context_tables()
    out = agent_globals.agent.generic_reasoner.delegate_gather_info(
        messages,
        context,
    )
    return {
        'messages': [HumanMessage(content=mp.delegate_gather_info_prompt), AIMessage(content=out)],
        'info': out,
    }


# deprecated
def agent_decide_process_old(state: AgentState):
    iterations = state['iterations'] + 1
    if iterations >= agent_globals.agent.max_multiattempt_iterations:
        return {'agent_decision': END}

    out = agent_globals.agent.planning_module.multiattempt_decide(state['messages'])

    formatted_msg = parse_decide_response(out)
    print_acr(
        formatted_msg,
        f"multiattempt decision iter {iterations}",
    )

    return {
        'messages': [AIMessage(content=formatted_msg)],
        'info': out['delegation_message'],
        'agent_decision': out['decision'],
        'iterations': iterations,
    }
