"""
utils for parsing impt info from trajectories, mainly focused on ACRv2
"""
import re


def parse_api_result(result: str) -> dict:
    parsed_data = {}

    # Define patterns for each key
    patterns = {
        'file': r'<file>(.*?)</file>',
        'class': r'<class>(.*?)</class>',
        'func': r'<func>(.*?)</func>',
        'code': r'<code>(.*?)</code>',
    }

    # Extract data using regex patterns
    for key, pattern in patterns.items():
        match = re.search(pattern, result, re.DOTALL)
        if match:
            parsed_data[key] = match.group(1).strip()

    return parsed_data


def separate_code_blocks(text: str):
    code_block_pattern = re.compile(r'```(.*?)```', re.DOTALL)
    code_blocks_list = code_block_pattern.findall(text)
    non_code_blocks_list = code_block_pattern.split(text)[::2]
    return code_blocks_list, non_code_blocks_list
