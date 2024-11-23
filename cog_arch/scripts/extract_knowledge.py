"""
This script is designed to extract procedural and semantic knowledge from successful trajectories.
It scans through a specified results folder to identify and process JSON files that represent
successful trajectories. The agent then learns from these trajectories by extracting rules and patterns.


Usage:
    The script is executed with command-line arguments specifying the checkpoint directory, output directory, model,
    verbosity, and debug mode. It initializes the agent and sets up local caching for language models before
    proceeding to process the specified project's trajectories.
"""

from argparse import ArgumentParser
from pathlib import Path

from langchain.globals import set_llm_cache
from langchain.cache import SQLiteCache

from ..agents.acr_agent import AcrAgent
from cog_arch.utils.traj_file_io import prepare_entries_by_result, load_trajectory

from app.main import add_task_related_args
from app.model.register import register_all_models

if __name__ == "__main__":
    register_all_models()
    parser = ArgumentParser()
    add_task_related_args(parser)
    args = parser.parse_args()

    results_folder_path = 'results/acr-run-1/'
    json_relative_path = 'new_eval_results/report.json'
    projectname = 'django__django'
    project_folders_relative_path = 'applicable_patch/'
    run_result = 'applied'

    # LM caching
    LM_CACHE_FOLDER = "lm_cache"
    Path(LM_CACHE_FOLDER).mkdir(parents=True, exist_ok=True)
    db_path = LM_CACHE_FOLDER + "/lm_cache.db"
    set_llm_cache(SQLiteCache(database_path=db_path))

    ckpt_dir = args.ckpt_dir if args.ckpt_dir else args.output_dir
    agent = AcrAgent(
        agent_model=args.model,
        ckpt_dir=ckpt_dir,
        verbose=args.verbose,
        debug_mode=args.debug_mode,
    )

    entries = prepare_entries_by_result(results_folder_path, json_relative_path, projectname, run_result)

    # Process each filtered entry
    for entry in entries:
        messages = load_trajectory(entry, results_folder_path, project_folders_relative_path)
        agent.extract_learn_rules(messages)
