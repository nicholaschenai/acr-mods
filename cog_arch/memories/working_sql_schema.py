# Define the schema
schema_sql = """

CREATE TABLE questions_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    answer TEXT,
    is_fully_answered BOOLEAN
);

CREATE TABLE api_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_name TEXT,
    arguments TEXT,
    result TEXT,
    reasoning TEXT,
    is_relevant BOOLEAN,
    relevant_result_snippets TEXT,
    file_name TEXT,
    class_name TEXT,
    method_name TEXT
);

CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    type TEXT,
    summary TEXT
);

CREATE TABLE question_api_result_associations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    api_result_id INTEGER,
    FOREIGN KEY (question_id) REFERENCES questions_table (id),
    FOREIGN KEY (api_result_id) REFERENCES api_results (id)
);

CREATE TABLE call_graphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    call_graph TEXT
);
"""

# Define the view
views_sql = """
CREATE VIEW detailed_trajectory AS
SELECT
    ts.id AS trajectory_id,
    ts.issue_statement,
    ts.layer_summary,
    la.attempt,
    la.hypothesis,
    la.hypothesis_validation,
    la.relevant_code_snippets,
    la.tool_call_layer,
    la.tool_call_msg
FROM
    trajectory_summary ts
JOIN
    layer_analysis la ON ts.id = la.trajectory_id;
"""


####################################################################################################
# future: traj id
todo_schema_sql = """
CREATE TABLE trajectory_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_statement TEXT,
    layer_summary TEXT
);

CREATE TABLE layer_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trajectory_id INTEGER,
    attempt INTEGER,
    hypothesis TEXT,
    hypothesis_validation TEXT,
    tool_call_layer TEXT,
    tool_call_msg TEXT,
    FOREIGN KEY (trajectory_id) REFERENCES trajectory_summary (id)
);
"""

###### old ####
"""
CREATE TABLE layer_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis TEXT,
    hypothesis_validation TEXT,
    tool_call_msg TEXT
);
"""