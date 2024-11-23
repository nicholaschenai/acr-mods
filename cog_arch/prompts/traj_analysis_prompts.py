traj_sys_prompt = """
You will be given a series of messages, showing how someone is attempting to address an issue in a repo.
This issue could be a bug, a feature request, or a code improvement task.
The person was given search APIs to search through the codebase.

Later, you will be given an instruction to extract specific information from the messages.
"""

traj_human_template = """
# Issue
{issue_prompt}

# API Definitions
{api_definitions}

# Messages
{messages}

# Your task
Answer the following questions if the information is available in the messages above, and keep your answers straight to the point:
{traj_task_prompt}
"""

questions_asked_prompt = """
The message above shows the person thinking through how to address the issue in the repo, potentially by using search APIs to understand the codebase.

Your task is to extract the intents and hypotheses of the person whenever a search API is planned, and phrase them as questions.

Before finalizing your answer, think through step-by-step. You could list down the raw intents and hypotheses first, and then convert them into questions later.

For example, if the person intends to search for a keyword to understand how errors are handled in feature Y, the question could be "How are errors handled in feature Y?"

For each question (one sentence per question), also provide the associated subject (e.g., a specific method of a class or area of the codebase) if any.

Also, the questions below have already been asked. If they reappear, you can skip them in your reply:

{open_questions_formatted}
"""

answer_extraction_prompt = """
The person made the API calls above because they asked the question:
{question}
{partial_answer}

The person now receives the results of the API calls and analyzes them in the messages section above.

Now, based on combining both existing and new info above, reason out step-by-step in the `reasoning` section whether the person's question is fully, partially, not answered.

If the person's question is fully or partially answered by the info, answer the person's question (or provide relevant info if partially answered) in the `answer` section.

Then, in `is_fully_answered`, state whether the person's question is fully answered by the info or not.
"""

tool_call_help_prompt = """
The person made the API calls above because they asked the question:
{question}

The person's question is answered by:
{answer}

Now, read the messages above and reason out step-by-step to determine which API call(s) contributed to the answer. For these contributing API calls, lookup their associated indices below, and then reply with the indices as a list.

{tool_call_display}
"""

result_snippets_prompt = """
## Prelude
The person made the API call in the Messages section above and managed to (at least partially) answer the following questions about the codebase:

{questions_answered}

## Task
Now, reply with the following: 

Reason out, step by step, which snippets of the API call result contributed to answering the person's questions about the codebase. 

Then, copy and paste the contributing snippets of the API call from the Messages section into the `relevant_result_snippets` section below. The info in the Prelude section is not the API call.
"""

edit_area_snippets_prompt = """
The API calls above were made to search for code that triggered the issue.
Let's focus on the result for this API call:
{api_call}

Now, reply with the following: 
Reason out, step by step, which snippets of the API call result are relevant to the issue in general
"""

summarize_patch_prompt = """
The above message is the attempted patch to address the issue in the repo (but failed to resolve the issue).
Reply with a summary of the patch.
What key areas are changed?
What is the high level concept of the patch?
"""


summarize_traj_prompt = """
The messages above are summaries of a series of attempts at addressing the issue in the repo.
Summarize the information in the messages with the aim that someone else can understand what has been attempted, and continue debugging from there.
"""

pattern_analysis_prompt = """
The person made several API calls to understand the codebase and received various results as seen in the messages above.
Analyze the search results above, and reason out step-by-step to identify any non-trivial patterns.

These patterns
- should help in future efforts to solve the issue
- are non-trivial observations or instructions that show a degree of reasoning or pattern recognition
- can be positive (e.g., identifying a common area of the codebase that is worth investigating, for example "The search results frequently mention the `X` class. This class appears to be central to the issue and should be investigated further.")
- can be negative (e.g., identifying areas of the codebase that seem to be important at first glance, but in reality are irrelevant, for example "The search results often include the `Logger` class, but it is generally irrelevant to the issue at hand.").

Reply with a list of patterns and the subject (eg a specific method of a class or area of the codebase) they pertain to, if any. 
If there are no patterns, reply with a blank list.
"""

positive_call_template = """
Relevant calls:
{relevant_calls_formatted}
"""

extract_edit_area_prompt = """
# Intro
You will be given a series of messages, showing how someone is attempting to address an issue in a repo, but failed to complete the task. 
This issue could be a bug, a feature request, or a code improvement task.
The person was given search APIs to search through code.

# Instruction
Extract the file paths and entities (class, method or function) that triggered the issue. 
This might be found the issue description early in the messages, or in the search API results used by the person.  

# Format
Respond in JSON, and follow the keys and expected format of the values strictly.
Response format:
{format_instructions}

## Example
{edit_area_example}

entity can be "your_function" for functions
"""

edit_area_example = [{
    'relative_path': "path/to/your/module.py",
    'entity': "YourClass.your_method",
}]

####################################################################################################
# old

hypothesis_validation_prompt = """
The person made the API calls above because they had a hypothesis or intent. The hypothesis / intent is:
{hypothesis}.

Now, answer the question: 
Based on the results and analysis above, reason out step-by-step whether the hypothesis / intent is validated, invalidated or not answered
"""

hypothesis_prompt = """
What is the intent of the person when issuing the search API commands? What are they trying to achieve?
Did they have a hypothesis in mind when issuing the search API commands? If so, what was it?
If the issue is a bug, what did they think was causing the bug?
"""

summarize_failed_traj_prompt = """
# Intro
You will be given a series of messages, showing how someone is attempting to fix bugs in a repo, but failed to finish debugging. 
The person was given search APIs to search through code.

# Instruction
Read the issue carefully (usually found at the beginning of the messages). Summarize the information in the messages with the aim that someone new can understand what has been attempted, what works and what does not, and continue debugging from there.

# Format
In your summary, include the following sections:
- **Explored areas** in the codebase. State the files, functions, or classes that were looked at or modified. 
- **Relevant code snippets** that can help in debugging. These could be snippets that confirm or refute a hypothesis.
- **Hypotheses formed** by the person. What did they think was causing the bug? What did they do to confirm or refute the hypotheses?
- **Other potentially relevant info or code snippets** that could be useful in future debugging efforts, and why. These could be patterns noticed, recurring errors, or any insights that emerged during the debugging process.
"""

summarize_failed_traj_prompt_v1 = """
# Intro
You will be given a series of messages, showing how someone is attempting to fix bugs in a repo, but failed to finish debugging. 
The person was given search APIs to search through code.

# Instruction
Summarize the information in the messages with the aim that someone else can understand what has been attempted, and continue debugging from there.

In your summary, include things like:
- The areas in the codebase that were explored. State the files, functions, or classes that were looked at. Include code snippets if necessary.
- The hypotheses formed by the person. What did they think was causing the bug? What did they try to fix?
- Any interesting observations that could be useful in future debugging efforts, and why. These could be patterns noticed, recurring errors, or any insights that emerged during the debugging process.
"""

result_snippets_old = """
The person made the API call above because they had a hypothesis or intent. 
The results of the API calls, relative to the hypothesis / intent, is:
{hypothesis_validation}

Now, reply with the following: 
Reason out, step by step, which snippets of the API call result are 
- relevant to the hypothesis / intent
- relevant to the issue in general,
or if the result of the API call is irrelevant.
"""

deduplicate_layers_prompt = """
The messages above are summaries of a series of attempts at addressing the issue in the repo.
First read the messages above carefully. Next, reply with a condensed version of the messages.

For example, if a hypothesis being tested initially returned no results, and eventually returned results, then only the final result should be included.
"""