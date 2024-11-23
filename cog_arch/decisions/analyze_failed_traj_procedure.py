from typing import TYPE_CHECKING

from .. import utils as u

if TYPE_CHECKING:
    # prevent circular import
    from ..agents.acr_agent import AcrAgent


class AnalyzeFailedTrajProcedure:
    # def run(agent: AcrAgent, task):
    @staticmethod
    def run(agent: 'AcrAgent', task):
        """
        Analyzes a failed trajectory to summarize the issue and attempt. 
        also call graph analysis of the faulty method.
        """
        # TODO: split into info gather n write patch
        print('load_trajectory')
        msgs, additional_info = u.traj_file_io.load_trajectory(
            task.task_id,
            agent.kwargs['results_folder_path'],
            agent.kwargs['project_folders_relative_path'],
            return_tool_call_layers=True,
            eval_relative_path=agent.kwargs['eval_relative_path'],
        )

        tool_call_layers = additional_info['tool_call_layers']
        agent.failed_tests = additional_info['failed_tests']

        # TODO: consider renaming this to sth related to tool calls n analysis, cos trajectory is more than that
        #   and dont confuse with trajectory analysis (method we are in rn)
        traj_analysis_result = agent.traj_analysis.analyze_tool_calls(msgs, tool_call_layers)
        agent.working_mem.update_trajectory_analysis(traj_analysis_result)

        # extract relevant code in buggy area
        buggy_layer_analysis = agent.traj_analysis.analyze_buggy_location(
            traj_analysis_result['buggy_location_msg'],
            traj_analysis_result['buggy_tool_call_layer'],
        )
        agent.working_mem.update_buggy_layer_analysis_db(buggy_layer_analysis)

        # summarize patch
        agent.latest_patch = traj_analysis_result['patch_msg']
        patch_summary = agent.traj_analysis.summarize_patch(agent.latest_patch)
        patch_info = {'patch_msg': agent.latest_patch, 'patch_summary': patch_summary}
        agent.working_mem.upload_patch_summary(patch_info)

        # summarize traj
        traj_summary = agent.traj_analysis.construct_summarize_traj(
            traj_analysis_result['tool_call_sequence_info'],
            traj_analysis_result['open_questions'],
            traj_analysis_result['fully_answered_qns'],
            buggy_layer_analysis,
            patch_info,
        )
        agent.failed_traj_summary = traj_summary
        agent.working_mem.upload_trajectory_summary(traj_summary)

        # future: maybe try to extract from issue statement, if cant find then view entire thread?
        print('extract_edit_areas')
        # TODO: might have overlaps with graph ele extract's from_patch
        edit_areas = agent.traj_analysis.extract_edit_areas(u.parse_chat_history(msgs))
        agent.call_graph_analysis_procedure(edit_areas, task.setup_info["repo_path"])

        agent.analyze_failed_patch()

        # print to debug only
        agent.working_mem.print_all_sqlite()
