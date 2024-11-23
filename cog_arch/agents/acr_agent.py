"""
This module defines the AcrAgent class, which is a central component of the cognitive architecture.
The AcrAgent encapsulates the decision-making logic and memory management necessary for automated code repair tasks.
It integrates various cognitive modules, including procedural memory, planning, and rule extraction

The AcrAgent class is responsible for managing the agent's working memory and long-term memory modules,
executing decision procedures for generating and learning from plans and rules,
and handling the agent's interaction with the bugfixing environment.
It leverages the cognitive_base package to utilize primitives for cognitive architecture

Key Components:
- Working Memory: Stores temporary information relevant to the current bugfixing context,
such as the current plan and patch correctness status.
- Long Term Memory Modules: Includes procedural memory for storing and retrieving plans and actions.
- Reasoning Modules: Comprises planning and rule extraction modules for generating repair plans and
learning rules from bugfix examples.
"""
import json

from ..memories.declarative_mem import DeclarativeMem
from ..memories.working_mem import WorkingMem
from ..memories.procedural import ProceduralMem
from ..memories.working_sql_schema import schema_sql

from ..reasoning.planning import Planning
from ..reasoning.traj_analysis import TrajectoryAnalysis
from ..reasoning.rule_extract import BugfixRuleExtraction
from ..reasoning.patch_analysis import PatchAnalysis
from ..reasoning.generic_reasoner import GenericReasoner
from ..reasoning.graph_ele_extract import GraphEleExtract
from ..reasoning.info_extract import InfoExtract
from ..reasoning.graph_reasoner import GraphReasoner

from ..decisions.analyze_failed_traj_procedure import AnalyzeFailedTrajProcedure

from .. import utils as u


class AcrAgent:
    def __init__(
            self,
            agent_model,
            ckpt_dir,
            debug_mode=False,
            verbose=False,
            agent_mode='',
            max_multiattempt_iterations=5,
            patch_retries=1,
            workflow_retry_limit=0,
            edge_include_nodes=False,
            **kwargs,
    ):
        """
        AcrAgent encapsulates the decision-making logic and memory management

        It integrates procedural memory, planning, and rule extraction modules to facilitate the bugfixing process,
        managing both the agent's working memory and long-term memory modules.
        
        Attributes:
            verbose (bool): If set to True, enables verbose output.
            plan_retry_limit (int): The maximum number of retries for plan execution.
            edit_location_summary (list): A summary of edit locations in the current context.
            patch_is_correct (bool): Indicates whether the current patch is correct.
            current_plan (str): The current plan being executed.
            full_plan (str): The full plan derived from the planning module.
            plan_retry_count (int): The current count of plan retries.
            procedural_mem (ProceduralMem): The procedural memory module.
            planning_module (Planning): The planning module.
            rule_extraction_module (BugfixRuleExtraction): The rule extraction module.
        
        Parameters:
            agent_model (str): The model name for the planning and rule extraction modules.
            ckpt_dir (str): The directory for checkpoints.
            debug_mode (bool): If set to True, enables debug mode.
            verbose (bool): If set to True, enables verbose output.
        """
        # misc settings
        self.verbose = verbose
        self.kwargs = kwargs

        # args
        self.workflow_retry_limit = workflow_retry_limit
        self.max_multiattempt_iterations = max_multiattempt_iterations
        self.agent_mode = agent_mode
        self.patch_retries = patch_retries
        self.edge_include_nodes = edge_include_nodes
        # TODO: config args before composing just like og repo
        """
        Working Memory: short term memory reflecting current circumstances
        """
        self.edit_location_summary = []
        self.patch_is_correct = False
        self.current_plan = ''
        self.full_plan = ''
        self.workflow_retry_count = 0
        self.failed_traj_summary = ''
        self.call_graph = ''
        self.failed_tests = []
        self.layer_analyses = []
        self.latest_patch = ''
        self.localization_prompt = ''

        self.working_mem = WorkingMem(schema_script=schema_sql)

        """
        Long term memory modules
        """
        self.procedural_mem = ProceduralMem(ckpt_dir=ckpt_dir)
        self.declarative_mem = DeclarativeMem(ckpt_dir=ckpt_dir, vectordb_name='declarative')

        """
        Reasoning modules
        """
        self.planning_module = Planning(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )
        self.traj_analysis = TrajectoryAnalysis(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )
        self.rule_extraction_module = BugfixRuleExtraction(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )
        self.patch_analysis = PatchAnalysis(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )
        self.generic_reasoner = GenericReasoner(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )
        self.graph_ele_extract = GraphEleExtract(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )
        self.info_extract = InfoExtract(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )
        self.graph_reasoner = GraphReasoner(
            model_name=agent_model,
            debug_mode=debug_mode,
            verbose=verbose,
        )

        """
        decision procedure modules
        """
        self.analyze_failed_traj_procedure = AnalyzeFailedTrajProcedure()

    """
    helpers
    """
    def reset(self):
        self.edit_location_summary = []
        self.patch_is_correct = False
        self.current_plan = ''
        self.full_plan = ''
        self.workflow_retry_count = 0
        self.failed_traj_summary = ''
        self.call_graph = ''
        self.failed_tests = []
        self.layer_analyses = []
        self.latest_patch = ''
        self.localization_prompt = ''

    def exit_workflow(self):
        """
        Determines whether the agent should exit the planning loop based on the retry limit or patch correctness.
        
        Returns:
            bool: True if the plan retry count exceeds the limit or the patch is correct, False otherwise.
        """
        self.workflow_retry_count += 1
        return (self.workflow_retry_count > self.workflow_retry_limit) or self.patch_is_correct

    """
    decision procedures
    """
    def get_plans_msg(self, chat_history: list[dict], use_retrieved=True):
        """
        Generates a message containing plans based on the chat history and whether to use retrieved plans.
        
        Parameters:
            chat_history (list[dict]): The chat history to consider for plan generation.
            use_retrieved (bool): If True, uses retrieved plans; otherwise, uses the current plan.
        
        Returns:
            str: A message containing the generated plans.
        """
        if use_retrieved:
            retrieval_context = self.planning_module.render_plan_retrieval_context(chat_history)
            retrieved_plans = self.procedural_mem.retrieve_by_ebd(retrieval_context)
            plans = [plan.page_content for plan in retrieved_plans]
        else:
            plans = [self.current_plan] if self.current_plan else []

        plans_msg = self.planning_module.render_plans_message(plans)
        return plans_msg

    def extract_learn_plan(self, chat_history: list[dict]):
        """
        Extracts and learns a plan based on the chat history, updating the agent's current and full plans.
        
        Parameters:
            chat_history (list[dict]): The chat history to consider for plan extraction and learning.
        """
        full_plan, current_plan = self.planning_module.extract_plan(chat_history, self.edit_location_summary)
        self.full_plan, self.current_plan = full_plan, current_plan
        self.procedural_mem.update_ebd(current_plan)

    def extract_learn_rules(self, chat_history: list[dict]):
        """
        Extracts and learns rules based on the chat history, updating the procedural memory with new rules.
        
        Parameters:
            chat_history (list[dict]): The chat history to consider for rule extraction and learning.
        """
        response = self.rule_extraction_module.from_example(chat_history)
        if response.get('rules', {}):
            self.procedural_mem.update_rules(response['rules'])

    def call_graph_analysis_procedure(self, edit_areas, project_path):
        print('static call graph analysis')
        for edit_area in edit_areas:
            print('relative_path: {relative_path}, entity: {entity}'.format(**edit_area))
            call_graph, full_fn_name = u.static_analysis.call_graph_analysis(project_path, **edit_area)
            if call_graph:
                self.working_mem.update_call_graph(full_fn_name, call_graph)

    # TODO: this should be a script, esp scaffolding. only reasoning stuff be in the agent/reasoning module
    # future: if still wna use this, separate out reasoning for ctx, patchwrite, test analysis etc
    def analyze_failed_trajectory(self, task):
        """
        Analyzes a failed trajectory to summarize the issue and attempt. 
        also call graph analysis of the faulty method.
        """
        self.analyze_failed_traj_procedure.run(self, task)

    # Future: if still wna use this, manage context properly cos it seems spammy
    def analyze_failed_patch(self):
        """
        from summarized context, ask why patch failed
        """
        # TODO: handle failed extraction of patch
        failed_patch_analysis = self.patch_analysis.analyze_failed_patch(
            patch=self.latest_patch,
            issue=self.traj_analysis.issue_statement,
            context=self.working_mem.get_context_tables(),
            err_message=u.format_failed_tests(self.failed_tests),
            localization_prompt=self.localization_prompt,
        )
        self.working_mem.update_failed_patch_analysis(failed_patch_analysis, self.latest_patch)

    
    def graph_retrieval_procedure(self, chat_history: list[dict], query_msg=None):
        """
        Retrieval from KG and selection of relevant info.
        
        Parameters:
            chat_history (list[dict]): The chat history to consider for graph retrieval.
        """
        if not query_msg:
            query_msg = chat_history[-1]['content']
        # Retrieve relevant elements from the knowledge graph
        info_str, id_map = self.declarative_mem.hybrid_graph_retrieval(query_msg)
        
        out = self.graph_reasoner.ask_for_expansion(chat_history, info_str)

        expanded_elements = [format_element(include_nodes=self.edge_include_nodes, **id_map[index])
            for index in out['elements_to_expand']
            if id_map.get(index)
        ]

        # Use graph reasoner to extract important information from expanded elements
        important_info = self.graph_reasoner.extract_important_info(chat_history, expanded_elements)

        return out['relevant_info'] + '\n\n' + important_info

def format_element(element_id, data, include_nodes=False, subject_data=None, object_data=None):
    """
    Helper function to format a graph element into a string.

    Parameters:
        element_id: id of node (str) or edge (tuple)
        data: dict of data of node or edge
        include_nodes: bool, if True, include formatted strings for each node in an edge
        subject_data: dict, data of the subject node (optional)
        object_data: dict, data of the object node (optional)

    Returns:
        str: A formatted string representing the element.
    """
    if isinstance(element_id, tuple):  # It's an edge
        subject, obj = element_id
        edge_str = f"Edge: ({subject}, {obj}), Data: {json.dumps(data, indent=4)}"
        if include_nodes and subject_data and object_data:
            subject_str = f"Node: {subject}, Data: {json.dumps(subject_data, indent=4)}"
            obj_str = f"Node: {obj}, Data: {json.dumps(object_data, indent=4)}"
            return f"{edge_str}\n\n{subject_str}\n\n{obj_str}"
        return edge_str
    else:  # It's a node
        return f"Node: {element_id}, Data: {json.dumps(data, indent=4)}"
