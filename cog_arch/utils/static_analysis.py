import os
import subprocess

from . import path_to_module_notation


def call_graph_analysis(project_path: str, relative_path: str, entity: str):
    """
    Perform static call graph analysis on a specified function or method.

    :param project_path: Absolute path to the project directory.
    :param relative_path: Relative path from the project directory to the Python file.
    :param entity: The function or class.method to analyze.
    """
    print('static call graph analysis')
    # Construct the full path to the target Python file
    target_file_path = os.path.join(project_path, relative_path)

    # This command generates a call graph in DOT format
    full_function_name = path_to_module_notation(relative_path) + '.' + entity
    # TODO: some zoom out fn for target file path and error handling if cant construct call graph
    # TODO: generate viz but also generate bare minimum for AI (no colors etc)
    # command = f"pyan3 {target_file_path} --dot --no-defines --colored --grouped --annotated -e --function {full_function_name}"
    command = f"pyan3 {target_file_path} --dot --no-defines --grouped --annotated -e --function {full_function_name}"
    print(f"Running command: {command}")
    try:
        # Execute the command and capture the output
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # The result.stdout contains the DOT format graph
        print(f"Call graph generated successfully.\n{result.stdout}")
        return result.stdout, full_function_name
    except subprocess.CalledProcessError as e:
        print(f"Error generating call graph: {e.stderr}")
        return None
