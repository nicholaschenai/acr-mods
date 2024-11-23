## Knowledge graph (KG) memory
aim: long term accumulation of knowledge over time and appropriate retrieval to facilitate long horizon tasks. Graphs so that relationships between concepts and areas of codebase are explicitly reasoned about and constructed. Inspired by AriGraph which uses KG memory to manage long horizon tasks in text-based games, beating LM-based summarization of knowledge

### algo
- construct KG from ACRv2 trajectories (`kg_construct_main` in `cog_arch/scripts/kg_construct.py`. called in `app/main.py`'s `run_raw_task_agent` function)
	- Store Issue as node (`kg_construct_main` in `cog_arch/scripts/kg_construct.py` creates `IssueNode` and adds it to graph)
	- tool call layer: extract codebase location (file / cls / method / code string) and store as nodes, form edges for 'contains' relation (`update_graph_from_tool_call` in `cog_arch/scripts/kg_construct.py`)
	- LM extract code summary (functionality node, relationship_to_issue edge, intended behavior node) and link to codebase location node (`update_graph_from_analysis_msg` in `cog_arch/scripts/kg_construct.py` using `extract_code_summaries`)
	- rule based extraction from bug location tool call, similar to above (`update_graph_from_issue_loc_msg` in `cog_arch/scripts/kg_construct.py`)
	- LM summarize patch (attribute of patch node), LM extract reasoning (node) for editing specific locations (node), link these up in KG (`update_graph_from_patch_write` in `cog_arch/scripts/kg_construct.py`)
	- test result analysis (`update_graph_from_test_suite_results` in `cog_arch/scripts/kg_construct.py`)
		- rule based extract failed test case n result as nodes and link them up (`graph_ele_extract.from_tests` in `cog_arch/reasoning/graph_ele_extract.py`)
		- LM summarizes patch result (attribute), reasons why patch fail (node) (`patch_analysis.analyze_test_failure` in `cog_arch/reasoning/patch_analysis.py`)
		- LM identifies flaws in original patch reasoning (node and linked to original reasoning nodes as a sign of updating its own understanding), and updates suspiciousness of codebase locations. applies to both locations modified in patch and not modified in patch (maybe it realizes it modified the wrong area and should modify somewhere else instead)(implemented in `patch_analysis.analyze_test_failure` in `cog_arch/reasoning/patch_analysis.py` and `create_reasoning_nodes_and_edges` in `cog_arch/utils/info_extraction_utils.py`)
- ACRv1 inference (triggered via `cog_arch/scripts/debug_kg_inference.sh`)
	- Custom retrieval algo that uses both embeddings and graph distance to get relevant nodes and edges. use LM to selectively expand graph elements (eg attributes) and copy down only relevant info, to manage context length (`graph_retrieval_procedure` in `cog_arch/agents/acr_agent.py`)
	- retrieval and append info to msg thread during:
		- context collection phase (`start_conversation_round_stratified` in `app/inference.py`, inserted just before the "Based on your analysis, answer below questions:" message)
		- patch generation phase (`run_with_retries` in `app/api/agent_write_patch.py` - called in two scenarios:
			- when patch is applicable but fails tests (just after the "Written an applicable patch, but it did not resolve the issue" message)
			- when patch cannot be extracted/applied (just after the "Your edit could not be applied to the program. " message)
	- (not yet implemented) result / new info stored in KG mem for future retrieval (marked as TODO in `update_graph_from_test_suite_results` in `cog_arch/scripts/kg_construct.py`)

### Status
- fully implemented the algo except for last step as still need to resolve issue below
- eval on 5 previously 'unresolved' tasks and one managed to get resolved, but turns out that one task (and 2 other tasks) were actually resolved by ACRv2 eventually. the trajectories suggest that the retrieved and appended info to the ACRv1 message thread doesnt seem to help
	- KG construction still needs to be adjusted from largely handcrafted process (I mostly defined the schema of the KG) to more LLM choice as the handcrafted process is a bit voluminous
	- Retrieval algorithm could be refined

### Other Code written
- Knowledge graph memory class (`cog_arch/memories/declarative_mem.py`)
	- retrieve by keyword / attributes, suspiciousness, but not yet used (`get_suspicious_nodes` in `cog_arch/memories/declarative_mem.py`, `get_nodes_by_attribute` in `cognitive_base/utils/database/graph_db/nx_db.py`)
	- visualization (`visualize_knowledge_graph` in `cog_arch/memories/declarative_mem.py`)

### Code notes
- Assumes v2 trajectories in `data/20240621_autocoderover-v20240620`

- To run only KG construction from data: `cog_arch/scripts/debug_kg.sh` which calls `cog_arch/scripts/kg_construct.py` which calls the main function `kg_construct_main`. It uses various subfunctions in `kg_construct.py` representing construction of KG from different parts of the trajectory.

- To run KG construction + inference: `cog_arch/scripts/debug_kg_inference.sh` which calls the main `app/main.py` and before the inference is started, calls `kg_construct_main` to construct the KG. At various points in the inference, the functions in `kg_construct.py` is also called to update the KG.

#### TODO
- find n commit sample trajectories
	- esp the one that looks up test cases