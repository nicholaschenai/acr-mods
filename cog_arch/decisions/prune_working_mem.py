from ..utils import agent_globals


def prune_working_mem(state):
    # agent chooses which working mem to retain.
    # choose via index numbers to reduce context n preserve accuracy
    messages = state['messages']
    context = agent_globals.agent.working_mem.get_context_tables()
    out = agent_globals.agent.generic_reasoner.prune_working_mem(
        messages,
        context,
    )
    agent_globals.agent.working_mem.prune_context_memory(out['indices_to_keep'])


def prune_router(state):
    agent_decision = state['agent_decision']
    if agent_decision == 'gather_info':
        return 'gather_info'
    elif agent_decision == 'write_patch':
        return 'validate_buggy_areas'
