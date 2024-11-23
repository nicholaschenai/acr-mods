## Prompt based Plan extraction
aim: get agent to learn generic useful plans

### Algo
- run the agent forward, retrieve relevant plans
    - upon the failure of localization, show it the ground truth
- get agent to extract generic plan, store in long term memory
- retry with this generic plan in the context to see if it helps

### Status
- many reasoning steps missing between ground truth and current knowledge, still doesnt solve long horizon prob
- need to adjust prompts to get generalizeable plan (currently have prompts that give the 2 extremes: too specific and too generic)
- Saw that Graham Neubig's group is also working on something similar (Agent workflow memory), pause for now until we have some idea that

### Code notes
- `extract_learn_plan` and `get_plans_msg` in `cog_arch/agents/acr_agent.py`, called in `app/inference.py` in `start_conversation_round_stratified` function at the start for retrieval and at the end for extraction
