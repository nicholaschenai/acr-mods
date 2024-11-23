import json

sys_message = """
# Intro
You will be given a series of messages showing how someone is attempting to find buggy locations in code. 
The person was given search APIs to search through code.


# Instruction
Complete these 3 tasks:

## Summarize the problem
Your first task is to summarize the problem that the person was trying to solve. 
This should appear early on in the series of messages.

## Summarize the attempts
Your next task is to summarize the attempts made by the person.

Structure the attempt summary into steps of Observation, Thought, or Action if possible.
Usually, these steps follow each other in a cycle.
- Observation: 
    - What facts was the person aware of at that point in time?
    - Or, what were the outcomes of the person's previous actions? Did it lead to useful information or dead ends?
- Thought: What are the reasoning steps of the person based on the observation, to arrive at a decision?
- Action: What actions did the person take? This is usually in the form of search APIs or writing code 

## Infer Rules for Future Bug Fixing
Based on the information above, and the summaries you have written, infer rules ("If CONDITIONS, do ACTIONS") that will help others in bug fixing. 

This task is rather detailed so read the instructions carefully. You will first do step-by-step reasoning in the `reasoning` field as a scratchpad, before formally extracting the rules into the `rules` field.

### Identify Key Actions
Look for significant actions taken during the bug-fixing process (refer to the 'Action' steps you wrote in the attempt summary).

- These could include navigating to specific parts of the codebase, applying certain fixes, or using particular debugging techniques.
- Reason out, step-by-step, why they are important to the bugfix process.
- Write these down in the `reasoning` field.

### Determine Conditions
For each key action identified earlier, reason out, step-by-step, the conditions or contexts in which these actions were taken (Reference the 'Thought' and 'Observation' steps preceeding the 'Action' steps in your attempt summary). 

- This could be the type of bug, the symptoms observed, or specific code patterns.
- In your reasoning, think carefully about causal relationships between the conditions and actions to ensure that the right conditions are identified.
- Link the Actions-Conditions together as a rule for bugfixing, e.g. "When encountering a null pointer exception in module X, check for uninitialized variables in function Y."
- Write these down in the `reasoning` field.

### Repeat Actions-Conditions identification on a more general scale
Think in broader terms beyond the specific 'Action' step in the attempt summary. Repeat the Action-Condition identification steps where now, the 'Action' for the rule is an abstraction of a series of 'Action's in the attempt summary. For example, a series of actions in the problem summary (eg searching through areas of the codebase) might be abstracted to 'investigating the possibility of common causes X and Y as the root cause of bug Z'. Write these down in the `reasoning` field.

### Formally extract the rules into the `rules` field
Now, read through your thoughts written in the `reasoning` field. Abstract each rule into a JSON object with the following keys: `rigid_conditions`, `flexible_conditions`, and `actions`. The values of conditions are expressed as JSON objects where the values are strings or lists of strings. The value of actions is a list of strings. The `rules` field should be a list of such JSON rules.

Notice that we now separate conditions into two categories `rigid_conditions`, `flexible_conditions`. A rule can have any combination of these conditions. These conditions are explained as follows:

#### Rigid Conditions
Rigid conditions are those that require an exact match. They tend to be objective attributes. Some examples are (but not limited to):

- **Exception Type**: Identify the type of exception raised (e.g., `ValueError`, `KeyError`). Use the key `exception_type`.
- **Error Message**: Identify significant substrings or patterns in the error message (e.g., "cannot convert", "not found"). Use the key `error_message_contains`.
- **Module**: Note the module where the error occurred (e.g., `numpy`, `pandas`). Use the key `module`.
- **Platform**: Note the operating system or platform (e.g., Windows, Linux, macOS). Use the key `platform`.
- **Runtime Environment**: Record the runtime environment details (e.g., Python version, virtual environment). Use the key `runtime_environment`.

#### Flexible Conditions
Flexible conditions are those that require a semantic or partial match. Some examples are (but not limited to):

- **Error Context**: Describe the broader context within the code, including any flexible conditions (e.g., "after eliminating suspicious locations X and Z"). Use the key `error_context`.
- **Code Structure**: Identify general code patterns or structures involved (e.g., inheritance, method calls). Use the key `code_structure`.
- **Function and Class Names**: Identify the function and class names involved in the error. Use the keys `function_name` and `class_name`.
- **Variable Names**: Identify the names of the variables involved in the error. Use the key `variable_names`.
- **Dependencies**: Identify any external libraries or dependencies used. Use the key `dependency`.

### General Guidelines
- **Generalization**: Write rules as broadly as possible. They should be generic and reusable, such that others can reference them when localizing new bugs in the future.
    - If a condition is not necessary to trigger the action, do not include it. For example, if the problem is platform-agnostic, omit the `platform` key.
    - If possible, state broad concepts over specific locations, e.g. "the function that caused error Y" rather than the specific parameters to the search APIs.
- **Non-Triviality**: Ensure the rules are insightful and not obvious or trivial. Emphasize key principles, concepts and strategies in your thought process.
- **Generic Problem Solving**: Only write rules that apply to generic problem solving, not just the specific problem provided.
- **Self-Contained Rules**: Each rule must be self-contained. Ensure that someone reading only the rule can apply it to new problems. Include enough context for the external reader.

# Format
Respond in JSON, and follow the keys and expected format of the values strictly.
Response format:
{format_instructions}

"""


# TODO: if need be, esp when a lot of parse errors, include example
"""
Response example:
{response_example}
"""

response_example_d = {
    "problem_summary": "your problem summary here",
    "attempt_summary": "your attempt summary here",
    "reasoning": "your step-by-step reasoning here",
    "rules": [
        {
            "rigid_conditions": {
                "exception_type": "ValueError",
                "error_message_contains": ["cannot convert", "invalid literal"],
            },
            "heuristic_conditions": {
                "error_context": "after eliminating suspicious locations X and Z",
                "code_structure": "inheritance",
            },
            "actions": ["add_type_check"]
        }
    ]
}

response_example = json.dumps(response_example_d, indent=4)
