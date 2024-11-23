## Multiattempt via langgraph w SQL mem
aim: finer-grained summarization / info extraction from a trajectory so that core info is still preserved (direct prompting for summary can lose a lot of info, and is already being done by CodeR), and allow the agent to attempt multiple times with choice of context collection or patchwrite rather than looping the ACRv1 workflow

### algo
- reasoning over previous trajectories (triggered in `app/main.py:run_raw_task_agent` which calls `AnalyzeFailedTrajProcedure.run` in `cog_arch/decisions/analyze_failed_traj_procedure.py`)
	- LM analyze ACRv1 trajectories for useful info: track questions asked and which were answered + associate tool calls that resulted in answer, and those left unanswered (implemented in `cog_arch/reasoning/traj_analysis.py`:
		- `analyze_tool_calls` orchestrates the analysis
		- `extract_questions_asked` extracts questions from reasoning messages
		- `extract_questions_validation` checks if questions were answered
		- `associate_questions_with_tool_calls` links tool calls to questions they helped answer)
	- LM reason to find patterns over relevant tool calls and irrelevant tool calls (`find_patterns_from_calls` in `cog_arch/reasoning/traj_analysis.py`)
	- LM summarize patch and trajectory (in `cog_arch/reasoning/traj_analysis.py`:
		- patch summary via `summarize_patch` 
		- trajectory summary via `construct_summarize_traj` and `summarize_trajectory`)
	- call graph analysis on edit area (`call_graph_analysis_procedure` in `cog_arch/agents/acr_agent.py`)
	- LM reason over patch failure (`analyze_failed_patch` in `cog_arch/agents/acr_agent.py` which uses `patch_analysis.analyze_failed_patch`)
	- all generated info stored in SQL mem (via `cog_arch/memories/working_mem.py`:
		- `update_trajectory_analysis` stores tool calls, questions, and patterns
		- `update_buggy_layer_analysis_db` stores buggy location analysis
		- `upload_patch_summary` stores patch summaries
		- `upload_trajectory_summary` stores trajectory summaries
		- `update_call_graph` stores call graph analysis)
- main loop (implemented as a langgraph workflow in `cog_arch/decisions/multiattempt_main_loop.py`)
	- manager agent looks at existing info at hand, perform reasoning (eg why patch fail, next high level step) and decide if should collect more context or attempt to write patch again (`agent_decide_process` in `cog_arch/decisions/agent_decide.py` using `agent.generic_reasoner.multiattempt_decide`)
	- manager selects snippets of info at hand (to manage context and prevent confusion), and write instructions along with the snippets to delegate to context collection agent or patchwrite agent (in `cog_arch/decisions/agent_decide.py`:
		- `delegate_write_patch` using `agent.generic_reasoner.delegate_write_patch`
		- `delegate_gather_info` using `agent.generic_reasoner.delegate_gather_info`)
	- patchwrite / context collection process happens (implemented in respective nodes:
		- `start_agent_gather_info` in `cog_arch/decisions/gather_info.py` which uses shared context from `working_mem.get_context_tables`
		- `start_agent_write_patch` in `cog_arch/decisions/write_patch.py` which also uses shared context)
	- result / new info passed back to manager agent (via langgraph edges back to agent node, with pruning of working memory via `prune_working_mem` in `cog_arch/decisions/prune_working_mem.py`)
	- (not yet implemented) result / new info stored in SQL mem for future retrieval

### Status
- algo fully implemented except for last step
- problem: manager instruction + snippets of info still causes confusion for context collection agent / patchwrite agent and need to debug that
- potential future work: if task success, all high level steps are reasoned over to form reusable generic plans.

### Code notes
- called via `debug_multiattempt.sh` which calls `app/main.py` with `agent_mode` set to `multi_attempt`

#### reasoning over prev trajectories
- analysis of failed trajectory happens in `app/main.py`'s `run_raw_task_agent` function
- The agent's `analyze_failed_trajectory` method calls `AnalyzeFailedTrajProcedure` in `cog_arch/decisions/analyze_failed_traj_procedure.py` which is the main part of this step
- default uses data in `results/acr-run-1/`. see `cog_arch/utils/argparsers.py` for default settings

#### langgraph main loop
- in `app/main.py`'s `do_inference` fn, instead of running `inference.run_one_task`, it runs `cog_arch/decisions/multiattempt_main_loop.py`'s `run_one_task_multi_attempt`
- the various nodes and edges in the graph can be found in the folder `cog_arch/decisions/`
