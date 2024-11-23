from argparse import ArgumentParser


# TODO: refactor argparser from other project into cognitive base n reuse it
def add_agent_related_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--use_agent",
        action="store_true",
    )
    parser.add_argument(
        "--ckpt_dir",
        type=str,
        default="",
        help="CURRENT checkpoint"
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--debug_mode", action="store_true")

    parser.add_argument(
        "--results_folder_path",
        type=str,
        default="results/acr-run-1/",
        help="Path to the results folder"
    )
    parser.add_argument(
        "--json_relative_path",
        type=str,
        default="new_eval_results/report.json",
        help="Relative path to the JSON report"
    )
    parser.add_argument(
        "--eval_relative_path",
        type=str,
        default="new_eval_results/logs",
        help="Relative path to the eval logs"
    )
    parser.add_argument(
        "--projectname",
        type=str,
        default="",
        help="Name of the project"
    )
    parser.add_argument(
        "--project_folders_relative_path",
        type=str,
        default="applicable_patch/",
        help="Relative path to the project folders"
    )
    parser.add_argument(
        "--run_result",
        type=str,
        default="applied",
        help="Result of the run"
    )
    parser.add_argument(
        "--agent_mode",
        type=str,
        default="",
        help="agent mode"
    )
    parser.add_argument(
        "--max_multiattempt_iterations",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--patch_retries",
        type=int,
        default=1,
    )
    parser.add_argument("--edge_include_nodes", action="store_true", help="Include nodes data when edge data is displayed")
    