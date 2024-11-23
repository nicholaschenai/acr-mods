## Prompt based rule extraction (condition-action)
aim: get agent to learn generic rules / subplans so these smaller chunks could be assembled into a larger plan

### status
- built base subplan extractor: summarize the trajectory, identify the Observations, Thoughts and Actions, then querying for a list of subplans (all in 1 prompt)
- challenges: subplans are occasionally poorly delineated, quality of subplans not good


### Code notes
- script to extract rules from trajectories: `cog_arch/scripts/extract_knowledge.py`
- `extract_learn_rules` in `cog_arch/agents/acr_agent.py`
