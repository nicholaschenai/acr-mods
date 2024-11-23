sys_template = """
# Intro
You will be given a series of messages, showing how someone is attempting to find buggy locations in code. 
The person was given search APIs to search through code.

# Instruction
Complete these 4 tasks

## Summarize the problem
Your first task is to summarize the problem that the person was trying to solve. 
This should appear early on in the series of messages.
The summary should be enclosed in backticks (see formatting below).

## Summarize the attempts
Your next task is to summarize the attempts made by the person.

Structure the attempt summary into steps of Observation, Thought, or Action if possible.
Usually these steps follow each other in a cycle.
- Observation: 
    - What facts was the person aware of at that point in time?
    - Or, what were the outcomes of the person's previous actions? Did it lead to useful information or dead ends?
- Thought: What are the reasoning steps of the person based on the observation, to arrive at a decision?
- Action: What actions did the person take? This is usually in the form of search APIs or writing code 

## Reason out the correct steps
Only do this if the result was a failure to resolve the problem.
- Use the info from the messages and reason out step by step what the correct series of actions should be.
- Use broad concepts if details are missing. 

## Write a high-level plan
Based on the earlier sections, distil the steps towards the correct series of actions into an actionable high-level plan 

Here are some things to note:
- The plan should be a numbered list enclosed in backticks (see formatting below).
- The plan should, as much as possible, lead towards a resolution of the problem.
- This plan should be a generic reusable framework that you can refer to when localizing new bugs in the future.
- Within the plan itself, consider emphasizing key principles, concepts and strategies that can be applied to a variety of scenarios.
- Avoid including specific details or code snippets that are unique to the current scenario.

# Format
Problem summary:
```summary
...
```

Attempt summary:
...

Reasoning:
...

High-level Plan:
```plan
1) ...
2) ...
3) ...
...
```
"""

plans_msg_intro = 'Here are summaries of related tasks and its corresponding high-level plans which you can reference'

gt_intro = ("Here are the results of your suggested patch compared to the accepted patch. "
            "Use this info to figure out the right steps if you made errors.\n")

# old

sys_template_v1 = """
# Intro
You will be given a series of messages, showing how someone is attempting to find buggy locations in code. The person was given search APIs to search through code.

# Instruction
Your task is to 
- summarize the problem that the person was trying to solve.
- summarize the attempts into an actionable high-level plan as a numbered list. 

Here are some things to note:

- This plan should be a reusable framework that you can refer to when localizing new bugs in the future.
- Highlight the key principles, concepts and strategies that can be applied to a variety of scenarios.
- Avoid including specific details or code snippets that are unique to the current scenario.
- If the result was a failure to resolve the problem, use the info from the messages and reason out step by step what the correct plan should be (under the "Problem summary" section), before writing the high-level plan (which should be as close to correct as possible)

## Format
Problem summary:
...

High-level Plan:
1) ...
2) ...
3) ...
...
"""

sys_template_v2 = """
# Intro
You will be given a series of messages, showing how someone is attempting to find buggy locations in code. 
The person was given search APIs to search through code.

# Instruction
Complete these 4 tasks

## Summarize the problem
Your first task is to summarize the problem that the person was trying to solve. 
This should appear early on in the series of messages

## Summarize the attempts
Your next task is to summarize the attempts made by the person.

Structure the attempt summary into steps of (Observation, Thought, Action) cycles if possible
- Observation: What facts was the person aware of at that point in time, or what were the outcomes of the person's previous actions? Did it lead to useful information or dead ends?
- Thought: What are the reasoning steps of the person based on the observation, to arrive at a decision?
- Action: What actions did the person take? This is usually in the form of search APIs or writing code 

## Reason out the correct steps
Only do this if the result was a failure to resolve the problem.
- Use the info from the messages and reason out step by step what the correct series of actions should be.
- Use broad concepts if details are missing. 

## Write a high-level plan
Based on the earlier sections, distil the steps towards the correct series of actions into an actionable high-level plan 

Here are some things to note:
- The plan should be a numbered list.
- The plan should, as much as possible, lead towards a resolution of the problem.
- This plan should be a generic reusable framework that you can refer to when localizing new bugs in the future.
- Highlight the key principles, concepts and strategies that can be applied to a variety of scenarios.
- Avoid including specific details or code snippets that are unique to the current scenario.

# Format
Problem summary:
...

Attempt summary:
...

Reasoning:
...

High-level Plan:
1) ...
2) ...
3) ...
...
"""

sys_template_v3 = """
# Intro
You will be given a series of messages, showing how someone is attempting to find buggy locations in code. 
The person was given search APIs to search through code.

# Instruction
Complete these 4 tasks

## Summarize the problem
Your first task is to summarize the problem that the person was trying to solve. 
This should appear early on in the series of messages.
The summary should be enclosed in backticks (see formatting below).

## Summarize the attempts
Your next task is to summarize the attempts made by the person.

Structure the attempt summary into steps of Observation, Thought, or Action if possible.
Usually these steps follow each other in a cycle.
- Observation: 
    - What facts was the person aware of at that point in time?
    - Or, what were the outcomes of the person's previous actions? Did it lead to useful information or dead ends?
- Thought: What are the reasoning steps of the person based on the observation, to arrive at a decision?
- Action: What actions did the person take? This is usually in the form of search APIs or writing code 

## Reason out the correct steps
Only do this if the result was a failure to resolve the problem.
- Use the info from the messages and reason out step by step what the correct series of actions should be.
- Use broad concepts if details are missing. 

## Write a high-level plan
Based on the earlier sections, distil the steps towards the correct series of actions into an actionable high-level plan 

Here are some things to note:
- The plan should be a numbered list enclosed in backticks (see formatting below).
- The plan should, as much as possible, lead towards a resolution of the problem.
- This plan should be a generic reusable framework that you can refer to when localizing new bugs in the future.
- Within the plan itself, consider emphasizing key principles, concepts and strategies that can be applied to a variety of scenarios.
- Avoid including specific details or code snippets that are unique to the current scenario.

# Format
Problem summary:
```summary
...
```

Attempt summary:
...

Reasoning:
...

High-level Plan:
```plan
1) ...
2) ...
3) ...
...
```
"""
