summarize_patch_attempt_prompt = """
Below is a conversation where someone is instructed to write a patch to fix a bug in a codebase.
Summarize the conversation, the patch attempt made and any details that might help fix the bug in future attempts. 
This will be read by the engineering manager who will decide on the next steps, so make sure to include all relevant details.
"""

analyze_failed_patch_prompt = """
# Intro
You are a software engineering manager maintaining a large project.
You are working on an issue submitted to your project.
The issue contains a description marked between <issue> and </issue>.

Your software engineers tried to navigate the codebase, understand the issue, and write a patch to address it.
However, the patch was not accepted.
You will be given a summarized report later.

Your software engineers have access to the following search APIs:
{api_definitions}

# Task
Given the info below, your task is to reason out step-by-step why the patch failed.
This is an analysis task that requires you to draw new insights, not to summarize information.
"""

human_prompt = """
# Issue
{issue}

# Patch applied
{patch}

# Error message (if any)
{err_message}

# Selected info from the patch attempt
{context}

# Results from software tools (if any)
{localization_prompt}
"""

fail_analysis_task = """
Reason out step-by-step why the patch failed.
This is an analysis task that requires you to draw new insights, not to summarize information.
"""

summary_task = """
Summarize the failed test results, and contextualize them with the patch attempt if it helps.
Focus on info which might help in future patch attempts. Do not make any recommendations.
"""

reasoning_flaws_task = """
Now, with new info from failed tests, reason out step-by-step the flaws in your original reasoning for the patch.
"""

patch_fail_template = """
We have received the following failed test results after applying the patch, and the patch was rejected.
{patch_fail_task}

# Failed Test Results
{test_results}
"""

# old
patch_fail_prompt = """
We have received the following failed test results after applying the patch.
Reason out step-by-step why the patch failed.
This is an analysis task that requires you to draw new insights, not to summarize information.

# Failed Test Results
{test_results}
"""

patch_reasoning_prompt = """
We have received the following failed test results after applying the patch.
Now, with new info from failed tests, reason out step-by-step the flaws in your original reasoning for the patch.

# Failed Test Results
{test_results}
"""

patch_fail_task = """
Reason out step-by-step why the patch failed.
This is an analysis task that requires you to draw new insights, not to summarize information.
"""

patch_reasoning_task = """
Read the developer's reasoning for the patch carefully.
Now, with new info from failed tests, reason out step-by-step the flaws in the developer's original reasoning.
"""

# System prompt for formatting test results
analyze_test_failure_sys_prompt = """
# Intro
Below is a conversation where someone is instructed to write a patch to fix a github issue.
The following are the failed test results after applying the patch.

# Your task
{task}

# Test Results:
{test_results}
"""
