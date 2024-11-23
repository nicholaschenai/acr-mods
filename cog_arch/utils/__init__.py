from copy import deepcopy

def parse_chat_history(chat_history):
    # TODO: for all uses, if possible, use the messages directly rather than concat into one msg
    #  LLMs tend to fail when one msg is too long
    human_msg = ''
    for message in chat_history:
        # human_msg += f"{message['role']}: {message['content']}\n\n"
        content_lines = message['content'].split('\n')
        indented_content = '\n    '.join(content_lines)
        human_msg += f"**{message['role']}**:\n    {indented_content}\n\n"
    return human_msg


def format_failed_tests(failed_tests):
    """
    Formats a list of failed tests into a string.

    :param failed_tests: List of dictionaries containing 'test' and 'traceback' keys.
    :return: A formatted string of failed tests.
    """
    formatted_output = ""
    for test in failed_tests:
        formatted_output += f"Test: {test['test']}\n"
        formatted_output += f"Traceback:\n{test['traceback']}\n"
        formatted_output += "-" * 70 + "\n"
    return formatted_output


def path_to_module_notation(file_path):
    # Remove the file extension
    no_extension = file_path.rsplit('.', 1)[0]
    # Replace slashes with dots
    module_notation = no_extension.replace('/', '.').replace('\\', '.')
    return module_notation


def safe_msg_append(msg, chat_history):
    """
    Appends a message to the chat history but deepcopy the history first

    :param msg: The message to append.
    :param chat_history: The current chat history.
    :return: The updated chat history.
    """
    chat_history_copy = deepcopy(chat_history)
    chat_history_copy.append(msg)
    return chat_history_copy
