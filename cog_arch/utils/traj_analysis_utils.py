"""
utils used during analysis / reasoning of ACR v1 trajectories. some are applicable to v2
The methods in the class is tied to v1 for now, if it is used for v2 it will be refactored out as a fn
"""


class TrajectoryAnalysisUtils:
    def format_relevant_tool_call_results(self, tool_call_list):
        relevant_snippets = ''
        for tool_call_d in tool_call_list:
            if tool_call_d.get('is_relevant', False):
                tool_call = tool_call_d['tool_call']
                relevant_snippets += f"\t- API Call: {construct_function_call(tool_call)}\n"
                relevant_snippets += f"\t- Result Snippet:\n{tool_call_d['relevant_result_snippets']}\n\n"
        return relevant_snippets

    def format_tool_calls(self, tool_call_list):
        formatted_tool_calls = ''
        for tool_call_d in tool_call_list:
            tool_call = tool_call_d['tool_call']
            formatted_tool_calls += f"API Call: {construct_function_call(tool_call)}\n"
        return formatted_tool_calls

    def format_layer_analyses(self, layer_analyses):
        formatted_layer_analyses = ''
        for idx, layer_analysis in enumerate(layer_analyses):
            formatted_layer_analysis = f"Attempt {idx + 1}:\n"
            formatted_layer_analysis += f"- Hypothesis / Intent:\n{layer_analysis['hypothesis']}\n\n"
            formatted_layer_analysis += f"- Hypothesis Validation:\n{layer_analysis['hypothesis_validation']}\n\n"

            relevant_snippets = self.format_relevant_tool_call_results(layer_analysis['tool_call_layer_info'])

            formatted_layer_analysis += f"- Relevant API Call Snippets:\n{relevant_snippets}\n\n"
            formatted_layer_analysis += "\n\n"
            formatted_layer_analyses += formatted_layer_analysis
        return formatted_layer_analyses


    @staticmethod
    def collate_api_calls(layer_or_seq, mode):
        relevant_calls, no_results_calls, irrelevant_results_calls = [], [], []
        seq = []
        if mode == 'layers':
            for layer_analysis in layer_or_seq:
                seq.extend(layer_analysis['tool_call_layer_info'])
        elif mode == 'seq':
            seq = layer_or_seq
        else:
            raise ValueError(f"Invalid mode: {mode}")

        for tool_call_d in seq:
            if tool_call_d.get('is_relevant', False):
                relevant_calls.append(tool_call_d)
            else:
                if tool_call_d['tool_call']['call_ok']:
                    # if `call_ok` is True, means results returned but not relevant
                    irrelevant_results_calls.append(tool_call_d)
                else:
                    #  if `call_ok` is False, means no results returned
                    no_results_calls.append(tool_call_d)
        return relevant_calls, no_results_calls, irrelevant_results_calls

    def append_buggy_layer_n_patch_info(self, deduplicated_layers, buggy_layer_analysis, patch_analysis):
        """
        Appends information from buggy_layer_analysis and patch_analysis to deduplicated_layers.

        Parameters:
            deduplicated_layers (str): The deduplicated layers as a string.
            buggy_layer_analysis (dict): The analysis of the buggy layer.
            patch_analysis (dict): The analysis of the patch.

        Returns:
            str: The combined information as a string.
        """
        # Append the information to deduplicated_layers
        combined_info = f"{deduplicated_layers}\n\n"

        buggy_layer_info = self.format_relevant_tool_call_results(buggy_layer_analysis.get('tool_call_layer_info', []))
        if buggy_layer_info:
            combined_info += f"## Edit Area Analysis\n{buggy_layer_info}\n\n"

        # Construct string from patch_analysis
        patch_summary = patch_analysis.get('patch_summary', '')
        if patch_summary:
            combined_info += f"## High-level summary of the patch\n{patch_summary}\n\n"

        return combined_info

    @staticmethod
    def append_tool_call_uid(tool_call_layers):
        counter = 0
        for tool_call_layer in tool_call_layers:
            for tool_call in tool_call_layer:
                tool_call['uid'] = counter
                counter += 1

    def format_qns_ans(self, tool_call_sequence_info, open_questions, fully_answered_qns):
        partially_answered_qns = [q for q in open_questions if q['answer']]
        not_answered_qns = [q for q in open_questions if not q['answer']]

        formatted_questions = ''
        seen_tool_calls = set()

        def format_question_list(questions, question_type):
            nonlocal formatted_questions, seen_tool_calls
            formatted_questions += f'\n## {question_type} Questions:\n\n'
            if not questions:
                formatted_questions += f"None\n\n"
                return
            for question_d in questions:
                formatted_questions += f"Question: {question_d['question_asked']}\n"
                if question_type == 'Not Answered':
                    continue
                formatted_questions += f"Answer: {question_d.get('answer', 'Not answered')}\n"

                for uid in question_d['tool_call_uids']:
                    if uid not in seen_tool_calls:
                        tool_call_d = next((tc for tc in tool_call_sequence_info if tc['tool_call']['uid'] == uid), None)
                        if tool_call_d:
                            formatted_questions += f"\t- API Call: {construct_function_call(tool_call_d['tool_call'])}\n"
                            formatted_questions += f"\t- Result Snippet:\n{tool_call_d['relevant_result_snippets']}\n\n"
                            seen_tool_calls.add(uid)

        format_question_list(fully_answered_qns, 'Fully Answered')
        format_question_list(partially_answered_qns, 'Partially Answered')
        format_question_list(not_answered_qns, 'Not Answered')

        return formatted_questions


def is_tool_call_in_message(message, tool_call):
    func_name = tool_call["func_name"]
    arguments = tool_call["arguments"]
    if len(arguments) == 1:
        # Single argument case
        argument_value = next(iter(arguments.values()))  # Get the first value from the dict
        fmt_arg_value_double = argument_value.replace("\"", "\\\"")
        fmt_arg_value_single = argument_value.replace("'", "\\'")
        constructed_call_double = f'{func_name}("{fmt_arg_value_double}")'
        constructed_call_single = f"{func_name}('{fmt_arg_value_single}')"
        return constructed_call_double in message or constructed_call_single in message
    elif len(arguments) > 1:
        # Multiple arguments case
        checks_double = ([func_name in message] + [f'"{arg_value}"' in message for arg_value in arguments.values()])
        checks_single = ([func_name in message] + [f"'{arg_value}'" in message for arg_value in arguments.values()])
        return all(checks_double) or all(checks_single)


def split_tool_call_results(message_content, tool_call_layer):
    """
    Splits the message_content into individual tool call results based on the tool_call_layer.

    Parameters:
        message_content (str): The content containing results of tool calls.
        tool_call_layer (list): A list of tool calls, each a dict with 'func_name' and 'arguments'.

    Returns:
        list: A list of dictionaries with 'tool_call' and 'result' keys.
    """
    results = []
    lines = message_content.splitlines()
    tool_call_iter = iter(tool_call_layer)
    current_tool_call = next(tool_call_iter, None)
    current_index = 0

    while current_tool_call and current_index < len(lines):
        line = lines[current_index]
        func_name = current_tool_call['func_name']
        arguments = current_tool_call['arguments']
        if line.startswith(f"Result of {func_name}"):
            if all(str(value) in line for value in arguments.values()):
                start_index = current_index
                # Find the end of the result
                end_index = start_index + 1
                while end_index < len(lines) and not lines[end_index].startswith("Result of "):
                    end_index += 1
                result = "\n".join(lines[start_index:end_index]).strip()
                results.append({"tool_call": current_tool_call, "result": result})
                current_tool_call = next(tool_call_iter, None)
                current_index = end_index - 1
        current_index += 1

    return results


def is_v1_buggy_location_message(message):
    # for ACR v1
    return "the code in buggy locations:\n" in message['content']


def is_patch_message(message, tool_call_layer):
    # for v1
    write_patch_msg = message['content'].startswith("Write a patch for the issue")
    is_write_patch_layer = len(tool_call_layer) == 1 and tool_call_layer[0]["func_name"] == "write_patch"
    # print(f"Checking if message is a patch message: {write_patch_msg and is_write_patch_layer}")
    return write_patch_msg and is_write_patch_layer


def find_tool_call_msg(messages, prev_msg_idx, tool_call_layer, version=1):
    """
    Extracts the relevant messages from the tool call layer.

    Parameters:
        messages (list): A list of chat messages.
        prev_msg_idx (int): The index of the previous message.
        tool_call_layer (list): The tool call layer.
        version (int): The ACR version used to produce the result.
    Returns:
        tuple: A tuple containing the relevant message and the index of the message.
    """
    for idx, message in enumerate(messages[prev_msg_idx:], start=prev_msg_idx):
        if message['role'] != 'user':
            continue
        # print(f"Checking message: {message['content']}")
        if version == 1:
            if is_v1_buggy_location_message(message) or is_patch_message(message, tool_call_layer):
                return message, idx, None
        found_tool_msg = True
        for tool_call in tool_call_layer:
            found_tool_msg = is_tool_call_in_message(message['content'], tool_call)
            if not found_tool_msg:
                break
        if found_tool_msg:
            tool_call_layer_info = split_tool_call_results(message['content'], tool_call_layer)
            return message, idx, tool_call_layer_info
    raise ValueError("Tool call message not found in chat history.")


def get_issue_statement(messages):
    """
    Extracts the issue statement from the chat messages.

    Parameters:
        messages (list): A list of chat messages.
    """
    for idx, message in enumerate(messages):
        if message['role'] != 'user':
            continue
        if '<issue>' in message['content'] and '</issue>' in message['content']:
            return idx, message['content']
    raise ValueError("Issue statement not found in chat history.")


def get_reasoning_and_analysis_messages(messages, tool_msg_idx, include_between=False):
    """
    During context retrieval, the AI reasons and issues which API(s) to use, and after the results are returned,
    analyzes it. we want these 2 messages
    """
    # get reasoning and analysis messages
    # TODO: future: maybe include analysis frm 1 msg before reasoning
    reasoning_msg = messages[tool_msg_idx - 1]
    assert reasoning_msg['role'] == 'assistant', 'Reasoning message should be from assistant'
    analysis_msg = messages[tool_msg_idx + 2]
    assert analysis_msg['role'] == 'assistant', 'Analysis message should be from assistant'
    if include_between:
        return messages[(tool_msg_idx-1):(tool_msg_idx+3)]
    return reasoning_msg, analysis_msg


def update_tool_call_question_associations(association_out, tool_call_layer_info, tool_call_to_questions, question_d):
    """
    updates the various data so that the associations are stored pairwise
    (tool call to question and question to tool call)
    """
    for tool_call_index in association_out['tool_call_indices']:
        if tool_call_index < 1 or tool_call_index > len(tool_call_layer_info):
            continue
        tool_call = tool_call_layer_info[tool_call_index - 1]['tool_call']
        question_d['tool_call_uids'] = question_d.get('tool_call_uids', []) + [tool_call['uid']]
        if tool_call_index not in tool_call_to_questions:
            tool_call_to_questions[tool_call_index] = []
        tool_call_to_questions[tool_call_index].append(question_d)


# Old stuff, to deprecate if v1 works with new strategy
def is_tool_call_in_message_old(message, tool_call):
    # this only checks for double quotes, for v1. we upgrade to double OR single quotes for v2.
    # leave this here incase the new strategy fails for v1
    func_name = tool_call["func_name"]
    arguments = tool_call["arguments"]
    if len(arguments) == 1:
        # Single argument case
        argument_value = next(iter(arguments.values()))  # Get the first value from the dict
        fmt_arg_value = argument_value.replace("\"", "\\\"")
        constructed_call = f'{func_name}("{fmt_arg_value}")'
        return constructed_call in message
    elif len(arguments) > 1:
        # Multiple arguments case
        checks = ([func_name in message] + [f'"{arg_value}"' in message for arg_value in arguments.values()])
        return all(checks)


def split_tool_call_results_old(message_content, tool_call_layer):
    """
    message contains multiple tool calls, reflected in tool_call_layer.
    Extracts the individual tool call messages from the message,
    and pairs them with the corresponding tool call.

    we will be trying a new strategy that can accommodate ACR v1 and v2, keep this here incase it fails for v1
    """
    # v1 consistently uses 2 newlines as delimiter, v2 uses 3 newlines if success but 2 newlines if no results
    delimiter = "\n\n"
    indi_tool_call_msgs = message_content.split(delimiter)
    indi_tool_call_msgs = [msg for msg in indi_tool_call_msgs if msg.strip()]

    assert len(indi_tool_call_msgs) == len(tool_call_layer), "Mismatch between tool calls and messages"

    tool_call_layer_info = []
    for tool_call, tool_call_result in zip(tool_call_layer, indi_tool_call_msgs):
        assert is_tool_call_in_message(tool_call_result, tool_call), "Tool call not found in message"
        tool_call_layer_info.append({"tool_call": tool_call, "result": tool_call_result})

    return tool_call_layer_info


def construct_function_call(tool_call):
    func_name = tool_call["func_name"]
    arguments = tool_call["arguments"]

    if len(arguments) == 1:
        # Single argument case
        argument_value = next(iter(arguments.values()))  # Get the first value from the dict
        fmt_arg_value = argument_value.replace("\"", "\\\"")
        constructed_call = f'{func_name}("{fmt_arg_value}")'
    else:
        # Multiple arguments case
        args_str = ", ".join(
            [f'{arg_name}="{arg_value}"' for arg_name, arg_value in arguments.items()]
        )
        constructed_call = f'{func_name}({args_str})'

    return constructed_call
    