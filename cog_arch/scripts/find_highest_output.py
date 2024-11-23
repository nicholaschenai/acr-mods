"""
double check for resolved tasks, how many outputs are there for each (varies)
"""
import json
import os

def load_results(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def find_highest_output(results_folder_path, task):
    i = 0
    while True:
        run_path = os.path.join(results_folder_path, task, f"output_{i}")
        if not os.path.exists(run_path):
            break
        i += 1
    return i - 1

def main(results_file_path, results_folder_path):
    results = load_results(results_file_path)
    resolved_tasks = results.get('resolved', [])

    for task in resolved_tasks:
        highest_output = find_highest_output(results_folder_path, task)
        print(f"Task: {task}, Highest output: output_{highest_output}")

if __name__ == "__main__":
    results_file_path = 'data/20240621_autocoderover-v20240620/results/results.json'
    results_folder_path = './data/20240621_autocoderover-v20240620/trajs'
    main(results_file_path, results_folder_path)
