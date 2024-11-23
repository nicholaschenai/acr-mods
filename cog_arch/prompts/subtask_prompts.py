api_definitions = (
    "\n- search_class(class_name: str): Search for a class in the codebase"
    "\n- search_method_in_file(method_name: str, file_path: str): Search for a method in a given file"
    "\n- search_method_in_class(method_name: str, class_name: str): Search for a method in a given class"
    "\n- search_method(method_name: str): Search for a method in the entire codebase"
    "\n- search_code(code_str: str): Search for a code snippet in the entire codebase"
    "\n- search_code_in_file(code_str: str, file_path: str): Search for a code snippet in a given file"
)

api_prompt = (
    "Based on the files, classes, methods, and code statements from the issue related to the bug, you can use the following search APIs to get more context of the project."
    f"{api_definitions}"
    "\n\nNote that you can use multiple search APIs in one round."
    "\n\nNow analyze the issue and select necessary APIs to get more context of the project. Each API call must have concrete arguments as inputs."
)

sys_prompt = """
You are an assistant for a software engineering team. An engineering manager will delegate an information gathering task to you, specifying what information needs to be collected to address issues or bugs in the project.

You have been equipped with a set of search APIs that allow you to navigate the codebase efficiently. Your task is to use these tools to gather detailed information according to the manager's specifications.
"""

extract_ans_prompt = """
Below is a conversation where someone is instructed by an engineering manager to use search APIs to gather information about a codebase, in order to address an issue.

The issue contains a description marked between <issue> and </issue>.

# Your task
- First, extract out the answer to the engineering manager's question.
- Next, in a separate section, summarize the areas searched.
- Last, in a separate section, include any details during information gathering that might help address the issue.
"""

next_step_prompt = """
Based on your analysis, answer the question: Do we need more context / info to complete the manager's task?
- If so, construct search API calls to get more context of the project
- If not, reply strictly with "task_completed"
"""

