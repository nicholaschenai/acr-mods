import json
import random
import sys

def load_results(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def get_experiment_sets(results):
    full_set = set(results['generated']) | set(results['no_generation'])
    resolved_set = set(results['resolved'])
    unresolved_set = full_set - resolved_set
    return full_set, resolved_set, unresolved_set

def filter_by_project(experiment_set, project_name):
    return {exp for exp in experiment_set if exp.startswith(project_name)}

def sample_experiments(resolved_set, unresolved_set, num_samples):
    resolved_list = list(resolved_set)
    unresolved_list = list(unresolved_set)

    random.shuffle(resolved_list)
    random.shuffle(unresolved_list)

    resolved_samples = resolved_list[:num_samples]
    unresolved_samples = unresolved_list[:num_samples]

    if len(resolved_samples) < num_samples:
        print(f"Warning: Only {len(resolved_samples)} resolved samples available.")
    if len(unresolved_samples) < num_samples:
        print(f"Warning: Only {len(unresolved_samples)} unresolved samples available.")

    return resolved_samples, unresolved_samples

def main(file_path, project_name=None, num_samples=5):
    results = load_results(file_path)
    _, resolved_set, unresolved_set = get_experiment_sets(results)

    if project_name:
        resolved_set = filter_by_project(resolved_set, project_name)
        unresolved_set = filter_by_project(unresolved_set, project_name)

    resolved_samples, unresolved_samples = sample_experiments(resolved_set, unresolved_set, num_samples)

    print("Resolved Samples:", resolved_samples)
    print("Unresolved Samples:", unresolved_samples)

if __name__ == "__main__":
    # if len(sys.argv) < 2:
    #     print("Usage: python filter_experiments.py <results_file_path> [project_name] [num_samples]")
    # else:
    #     file_path = sys.argv[1]
    #     project_name = sys.argv[2] if len(sys.argv) > 2 else None
    #     num_samples = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    #     main(file_path, project_name, num_samples)

    # Set variables directly
    random.seed(42)
    file_path = 'data/20240621_autocoderover-v20240620/results/results.json'
    project_name = 'django'
    num_samples = 5
    main(file_path, project_name, num_samples)
