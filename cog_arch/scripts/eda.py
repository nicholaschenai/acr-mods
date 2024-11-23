"""
explore specrover trajectories
"""
import json
import os

def find_tool_call_layers_files(folder):
    tool_call_layers_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file == 'tool_call_layers.json':
                tool_call_layers_files.append(os.path.join(root, file))
    return tool_call_layers_files


def collate_inner_dict_keys(files):
    keys_set = set()
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            for outer_list in data:
                for item in outer_list:
                    if 'arguments' in item and isinstance(item['arguments'], dict):
                        keys_set.update(item['arguments'].keys())
    return keys_set


def check_tool_call_args(folder):
    # collate tool call arguments in ACRv2 to see what has changed compared to ACRv1
    tool_call_layers_files = find_tool_call_layers_files(folder)
    keys = collate_inner_dict_keys(tool_call_layers_files)
    print("Collated keys from inner dicts:", keys)

if __name__ == "__main__":
    results_folder_path = './data/20240621_autocoderover-v20240620/trajs'
    check_tool_call_args(results_folder_path)

    max_i = 0
    for task_dir in os.listdir(results_folder_path):
        task_path = os.path.join(results_folder_path, task_dir)
        if os.path.isdir(task_path):
            print(task_path)
            for output_dir in os.listdir(task_path):
                if output_dir.startswith('output_'):
                    try:
                        i = int(output_dir.split('_')[1])
                        if i > max_i:
                            max_i = i
                    except ValueError:
                        continue

    print(f"Maximum i value: {max_i}")
