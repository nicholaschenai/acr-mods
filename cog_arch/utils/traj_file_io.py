"""
utils used during loading of ACR v1 trajectories and identifying the impt info. some are applicable to v2
"""
import os
import re

from pprint import pp

from cognitive_base.utils import load_json
from .info_extraction_utils import is_v2_buggy_location_message


def get_all_convo_fname(folder_path, prefix='debug_agent_write_patch', suffix='json'):
    """
    gets all convo files of the specified format
    """
    print(f'folder_path: {folder_path}')
    # TODO: for v2, will have 2 integers so handle that
    # Note: cant put full path here cos path can have other ints
    convo_files = [f for f in os.listdir(folder_path) if re.match(fr'{prefix}_\d+\.{suffix}', f)]
    convo_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    print(f'convo_files: {convo_files}')
    return convo_files


def get_latest_convo_fname(folder_path, prefix='debug_agent_write_patch', suffix='json'):
    """
    gets the file that has the most updated conversation
    """
    convo_files = get_all_convo_fname(folder_path, prefix=prefix, suffix=suffix)
    if not convo_files:
        return None
    # TODO: for v2, will have 2 integers so handle that
    # most_updated_convo_file = max(convo_files, key=lambda x: int(re.search(r'\d+', x).group()))
    most_updated_convo_file = convo_files[-1]
    print(f'most_updated_convo_file: {most_updated_convo_file}')
    return os.path.join(folder_path, most_updated_convo_file)


def prepare_entries_by_result(results_folder_path, json_relative_path, projectname='', run_result='wrong_patch'):
    """
    Prepares the list of entries to be processed based on its results in ACR

    :param results_folder_path: The base path to the results folder.
    :param json_relative_path: The relative path to the JSON file containing the results.
    :param projectname: The project name to filter entries by.
    :param run_result: type of run result to filter by. Default is 'wrong_patch'.
    :return: A list of filtered entries based on the project name and the specified key ('resolved' or 'applied').
    """
    # Load the main JSON file
    json_file_path = os.path.join(results_folder_path, json_relative_path)
    data = load_json(json_file_path)

    if run_result == 'wrong_patch':
        applied_entries = set(data.get('applied', []))
        resolved_entries = set(data.get('resolved', []))
        entries_to_use = list(applied_entries - resolved_entries)
    elif run_result == 'resolved':
        entries_to_use = data.get('resolved', [])
    else:
        raise ValueError(f"Invalid run_result: {run_result}")

    # Filter the entries by projectname
    if projectname:
        return [entry for entry in entries_to_use if entry.startswith(projectname)]
    return entries_to_use


def find_log_file(entry, eval_folder_path):
    """
    Searches the folder for files where the name starts with `entry` and the extension is `.log`.

    :param entry: The starting name of the file.
    :param eval_folder_path: The folder path to search in.
    :return: The file name if it exists, otherwise None.
    """
    for file_name in os.listdir(eval_folder_path):
        if file_name.startswith(entry) and file_name.endswith('.log'):
            return file_name
    return None


def get_tool_call_layers(folder_path):
    tool_call_layers_path = os.path.join(folder_path, 'tool_call_layers.json')
    # check if tool_call_layers.json exists
    tool_call_layers = load_json(tool_call_layers_path)
    if not tool_call_layers:
        print(f"No tool call layers found in {folder_path}")
    return tool_call_layers


def get_latest_convo(folder_path, prefix='debug_agent_write_patch', suffix='json'):
    messages = []
    latest_convo_fname = get_latest_convo_fname(folder_path, prefix=prefix, suffix=suffix)
    if latest_convo_fname:
        messages = load_json(latest_convo_fname)
        print(f"Loaded data from {latest_convo_fname}:")
    else:
        print(f"No files found in {folder_path}")
    return messages


def load_trajectory(
        entry,
        results_folder_path,
        project_folders_relative_path,
        return_tool_call_layers=False,
        eval_relative_path='',
):
    """
    Processes a single trajectory by finding the most updated conversation file and loading its data.

    :param entry: The entry to process.
    :param results_folder_path: The base path to the results folder.
    :param project_folders_relative_path: The relative path to the project folders.
    :param return_tool_call_layers: Whether to return the tool call layers.
    eval_relative_path: The relative path to the eval logs. include this arg if you want to return eval results
    """
    parent_folder_path = os.path.join(results_folder_path, project_folders_relative_path)

    # Find the folder that matches the pattern
    matching_folders = [f for f in os.listdir(parent_folder_path) if f.startswith(entry)]
    if not matching_folders:
        print(f"No matching folders found for {entry} in {parent_folder_path}")
        return

    additional_info = {}

    # Assuming there's only one matching folder per entry
    project_folder_path = os.path.join(parent_folder_path, matching_folders[0])
    print(f'attempt loading from {project_folder_path}')

    messages = []
    if os.path.exists(project_folder_path) and os.path.isdir(project_folder_path):
        print(f'loading from {project_folder_path}')
        messages = get_latest_convo(project_folder_path)

        if return_tool_call_layers:
            tool_call_layers = get_tool_call_layers(project_folder_path)
            additional_info['tool_call_layers'] = tool_call_layers
    else:
        print(f"Folder {project_folder_path} does not exist or is not a directory")

    failed_tests = []
    if eval_relative_path:
        eval_folder_path = os.path.join(results_folder_path, eval_relative_path)
        logfile = find_log_file(entry, eval_folder_path)
        if logfile:
            print(f"Found log file: {logfile}")
            failed_tests = extract_failed_tests(os.path.join(eval_folder_path, logfile))
        additional_info['failed_tests'] = failed_tests

    if additional_info:
        return messages, additional_info
    return messages


# TODO: currently this is for django, need to make it more general
# TODO: see app/api/eval_helper.py (v1) and maybe the v2 equivalent for quick parsing!
def extract_failed_tests(logfile, verbose=False):
    with open(logfile, 'r') as file:
        log_content = file.read()

    # Regular expression to match failed test cases and their tracebacks
    # pattern = re.compile(r'={70}\nFAIL: (.*?)\n-{70}\n(.*?)\n\n', re.DOTALL)
    # pattern = re.compile(r'={70}\nFAIL: (.*?) \((.*?)\)\n-{70}\n(.*?)\n\n', re.DOTALL)
    # pattern = re.compile(r'={70}\nFAIL: (.*?) \((.*?)\)\n(.*?)\n-{70}\n(.*?)\n\n', re.DOTALL)
    # pattern = re.compile(r'={70}\nFAIL: (.*?) \((.*?)\)(.*?)\n-{70}\n(.*?)\n\n', re.DOTALL)
    pattern = re.compile(r'={70}\n(?:FAIL|ERROR): (.*?) \((.*?)\)(.*?)\n-{70}\n(.*?)\n\n', re.DOTALL)
    failed_tests = pattern.findall(log_content)

    results = []
    # for test, traceback in failed_tests:
    #     results.append({
    #         'test': test.strip(),
    #         'traceback': traceback.strip()
    #     })
    # for test_name, test_path, traceback in failed_tests:
    #     result = {
    #         'test_name': test_name.strip(),
    #         'test_path': test_path.strip(),
    #         'test': test_name.strip() + ' (' + test_path.strip() + ')',
    #         'traceback': traceback.strip()
    #     }
    for test_name, test_path, description, traceback in failed_tests:
        result = {
            'test_name': test_name.strip(),
            'test_path': test_path.strip(),
            'description': description.strip(),
            'test': test_name.strip() + ' (' + test_path.strip() + ')',
            'traceback': traceback.strip()
        }
        results.append(result)
        if verbose:
            pp(result)
    return results


def get_bug_loc_search_results(run_path):
    """
    for ACR v2
    gets the messages showing code search results for bug locations
    Returns:

    """
    all_patch_convo_fnames = get_all_convo_fname(run_path, prefix='conv_patch')
    scanned_message_content = set()
    for patch_convo_fname in all_patch_convo_fnames:
        patch_convo = load_json(os.path.join(run_path, patch_convo_fname))
        for message in patch_convo:
            if is_v2_buggy_location_message(message):
                scanned_message_content.add(message['content'])
                break
    return list(scanned_message_content)


def load_patch_data(suffix, run_path, extracted_patch_fname):
    """
    for ACR v2
    Args:
        suffix:
        run_path:
        extracted_patch_fname:

    Returns:

    """
    raw_patch_fname = f"patch_raw_{suffix}.md"
    with open(os.path.join(run_path, raw_patch_fname), 'r') as file:
        raw_patch = file.read()
    with open(os.path.join(run_path, extracted_patch_fname), 'r') as file:
        extracted_patch = file.read()
    patch_convo_fname = f"conv_patch_{suffix}.json"
    patch_convo = load_json(os.path.join(run_path, patch_convo_fname))
    return raw_patch, extracted_patch, patch_convo
