sys_prompt = """
# Intro
You are a software engineering manager maintaining a large project.
You are working on an issue submitted to your project.
The issue contains a description marked between <issue> and </issue>.

# Instruction
You will be given various info by the software engineers working on the issue.
From this, you will be tasked later to perform analyses or make decisions.

# API Definitions
Your software engineers have access to the following search APIs:
{api_definitions}
"""

human_prompt = """
# Issue
{issue_prompt}

# Results from software tools (if any)
{localization_prompt}
"""

multiattempt_decide_prompt = """
# Task
First, analyze the information given above and the selected info from your software engineers given below.
Reason out step-by-step: Do you have enough information at hand to write the patch?
This also means you know where the edit locations are.
"""

multiattempt_decide_template = """
## Response Format
Respond in JSON, and follow the keys and expected format of the values strictly.
{format_instructions}

# Selected info from past patch attempts
{context}
"""

delegate_prompt = """
Write a message containing enough information for the person you are delegating to.
Keep it straight to the point and avoid formalities.
They are aware of the issue and search APIs, so you do not need to repeat these.
"""

delegate_write_patch_prompt = f"""
# Task
You will be delegating the patch writing task to a software engineer.
{delegate_prompt}

Provide the files and methods to be edited, and any other relevant information.
"""

context_template = """
# Selected info from past patch attempts to help you understand the situation better
{context}
"""

decide_info_to_gather_prompt = """
# Task
Since you do not have enough information to write the patch, hypothesize the root cause of the issue. 
What information do you need to confirm or refute this hypothesis? 
What is the high-level next step to take? (eg 'eliminate this hypothesis')
"""

delegate_gather_info_prompt = f"""
# Task
You will be delegating the info gathering task to a software engineer.
{delegate_prompt}

Provide any specific information you need them to gather, and any information that could help them in their search.
"""

prune_working_mem_prompt = """
# Task
Your software engineers have gathered a lot of information while attempting to resolve the issue.
Analyze the information given above and the info from your software engineers (in a database) given below.
Think step-by-step: What information is relevant to the current task? What can be pruned?
Then, return the indices of the entries of the database to keep (so those indices not mentioned will be deleted).

## Response Format
Respond in JSON, and follow the keys and expected format of the values strictly.
{format_instructions}

# Database
{context}
"""

shared_context_template = """
# Additional info
Your fellow software engineers have gathered information while attempting to resolve the issue.
They are represented by database entries given below.
It can be quite voluminous, so exercise discretion in what info you choose to use.

## Database
{context}
"""

# old
sys_prompt_old = """
# Intro
You are a software engineering manager maintaining a large project.
You are working on an issue submitted to your project.
The issue contains a description marked between <issue> and </issue>.

# Task
At each step, you will 
- be given additional information about the issue and codebase
- be asked to decide on the next steps to take (via delegation) to resolve the issue, given this new information.

Your software engineers have access to the following search APIs:
{api_definitions}

Each step can be broken down into 3 parts:

## Analyze
First, analyze the information at hand. Reason out step-by-step:
- Do you have enough information to delegate patch writing? This means you know where the edit locations are, and you have enough information at hand to know how to write the patch.
- If not, hypothesize the root cause of the bug. What information do you need to confirm or refute this hypothesis? What is the high-level next step to take?
Fill this in the `reasoning` key

## Decide
Next, decide if you should delegate patch writing ("write_patch"), or delegate information gathering ("gather_info").
Fill this in the `decision` key

## Delegate
Finally, write a message containing enough information for the person you are delegating to. Keep it straight to the point.
They are aware of the issue and search APIs, so you do not need to repeat these.
- If you are delegating the write patch task, provide the buggy files and methods, and relevant information.
- If you are delegating the information gathering task, provide the high level next step (eg 'eliminate this hypothesis'), any specific information you need them to gather, and any information that could help them in their search.
Fill this in the `delegation_message` key

# Format
Respond in JSON, and follow the keys and expected format of the values strictly.
Response format:
{format_instructions}
"""

human_prompt_old = """
# Issue
{issue_prompt}

# Summary of attempts
{failed_traj_summary}

# Results from software tools (if any)
{localization_prompt}
{call_graph}
"""
