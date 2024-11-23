import json
import re

from cognitive_base.utils.database.relational_db.sqlite_db import SQLiteDB


# TODO: use updated cognitive base memory schema so can update sqlite with less code
class WorkingMem(SQLiteDB):
    def __init__(self, db_path=':memory:', schema_script="", schema_path=""):
        super().__init__(db_path, schema_script, schema_path)
        self.context_memory = {
            "questions_table": [],
            "api_results": [],
            "summaries": [],
            "call_graphs": [],
        }
        self.current_index = 0

    """
    helper fns
    """

    def _add_entry_with_index(self, table_name, entry):
        entry['index'] = self.current_index
        self.context_memory[table_name].append(entry)
        self.current_index += 1

    def get_context_tables(self):
        """
        Formats the context memory as tables in a string.
        """
        formatted_tables = []

        for table_name, entries in self.context_memory.items():
            if not entries:
                continue

            # Get the headers from the keys of the first entry
            # headers = entries[0].keys()
            headers = ['index'] + [header for header in entries[0].keys() if header != 'index']
            table_str = f"Table: {table_name}\n"
            table_str += " | ".join(headers) + "\n"
            table_str += "-" * (len(headers) * 15) + "\n"

            for entry in entries:
                row = " | ".join(
                    "\n".join("    " + line if i > 0 else line for i, line in
                              enumerate(str(entry.get(header, "")).split("\n")))
                    for header in headers
                )
                table_str += row + "\n"

            formatted_tables.append(table_str)

        return "\n\n".join(formatted_tables)

    @staticmethod
    def get_subjects_from_patch(patch_msg):
        subjects = re.findall(r'<file>(.*?)</file>', patch_msg)
        deduplicated_subjects = list(set(subjects))
        concatenated_subjects = ', '.join(deduplicated_subjects)
        return concatenated_subjects

    """
    Retrieval
    """

    """
    update
    """

    def upload_patterns(self, patterns_dict):
        """
        Uploads patterns to the summaries table.
        """
        cursor = self.conn.cursor()

        for pattern_subject in patterns_dict['patterns']:
            cursor.execute(
                """
                INSERT INTO summaries (subject, type, summary)
                VALUES (?, ?, ?)
                """,
                (pattern_subject['subject'], 'observation', pattern_subject['pattern'])
            )
            self._add_entry_with_index("summaries", {
                "subject": pattern_subject['subject'],
                "type": 'observation',
                "summary": pattern_subject['pattern']
            })

        self.conn.commit()

    def upload_patch_summary(self, patch_analysis):
        if not patch_analysis:
            return
        cursor = self.conn.cursor()

        # Extract subjects from patch_msg
        concatenated_subjects = self.get_subjects_from_patch(patch_analysis['patch_msg'])
        # must explicitly mention fail cos mgr dunno
        summary = f"{patch_analysis['patch_summary']} The patch did not manage to resolve the issue."

        cursor.execute(
            """
            INSERT INTO summaries (subject, type, summary)
            VALUES (?, ?, ?)
            """,
            (concatenated_subjects, 'patch_summary', summary)
        )
        self._add_entry_with_index("summaries", {
            "subject": concatenated_subjects,
            "type": 'patch_summary',
            "summary": summary
        })

        self.conn.commit()

    def update_failed_patch_analysis(self, failed_patch_analysis, patch_msg):
        cursor = self.conn.cursor()

        # Extract subjects from patch_msg
        concatenated_subjects = self.get_subjects_from_patch(patch_msg)

        cursor.execute(
            """
            INSERT INTO summaries (subject, type, summary)
            VALUES (?, ?, ?)
            """,
            (concatenated_subjects, 'failed_patch_analysis', failed_patch_analysis)
        )
        self._add_entry_with_index("summaries", {
            "subject": concatenated_subjects,
            "type": 'failed_patch_analysis',
            "summary": failed_patch_analysis
        })

        self.conn.commit()

    def update_buggy_layer_analysis_db(self, buggy_layer_analysis):
        """
        Populates the api_results table from the buggy_layer_analysis data.

        Parameters:
            buggy_layer_analysis (dict): Dictionary containing buggy layer analysis information.
        """
        if not buggy_layer_analysis:
            return
        cursor = self.conn.cursor()

        tool_call_layer_info = buggy_layer_analysis['tool_call_layer_info']
        for tool_call_d in tool_call_layer_info:
            tool_call = tool_call_d['tool_call']
            api_name = tool_call['func_name']
            arguments = json.dumps(tool_call['arguments'])
            result = buggy_layer_analysis['tool_call_msg']
            reasoning = tool_call_d.get('reasoning', '')
            is_relevant = True
            relevant_result_snippets = tool_call_d.get('relevant_result_snippets', '')

            file_name = tool_call['arguments'].get('file_name', '')
            class_name = tool_call['arguments'].get('class_name', '')
            method_name = tool_call['arguments'].get('method_name', '')

            cursor.execute(
                """
                INSERT INTO api_results (
                    api_name, arguments, result, reasoning, is_relevant, relevant_result_snippets,
                    file_name, class_name, method_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (api_name, arguments, result, reasoning, is_relevant, relevant_result_snippets,
                 file_name, class_name, method_name)
            )
            # if is_relevant:
            self._add_entry_with_index("api_results", {
                "api_name": api_name,
                "arguments": arguments,
                "relevant_result_snippets": relevant_result_snippets,
            })

        self.conn.commit()

    def update_api_results_db(self, tool_call_sequence_info):
        """
        Populates the api_results table from the tool_call_sequence_info data.

        Parameters:
            tool_call_sequence_info (list): List of tool call sequence information dictionaries.
        """
        cursor = self.conn.cursor()
        uid_to_db_id = {}

        for tool_call_d in tool_call_sequence_info:
            tool_call = tool_call_d['tool_call']
            api_name = tool_call['func_name']
            arguments = json.dumps(tool_call['arguments'])
            result = tool_call_d['result']
            reasoning = tool_call_d.get('reasoning', '')
            is_relevant = tool_call_d.get('is_relevant', False)
            relevant_result_snippets = tool_call_d.get('relevant_result_snippets', '')
            # each tool call is associated with its subject / area
            file_name = tool_call['arguments'].get('file_name', '')
            class_name = tool_call['arguments'].get('class_name', '')
            method_name = tool_call['arguments'].get('method_name', '')

            cursor.execute(
                """
                INSERT INTO api_results (
                    api_name, arguments, result, reasoning, is_relevant, relevant_result_snippets,
                    file_name, class_name, method_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (api_name, arguments, result, reasoning, is_relevant, relevant_result_snippets,
                 file_name, class_name, method_name)
            )

            db_id = cursor.lastrowid
            if 'uid' in tool_call:
                uid_to_db_id[tool_call['uid']] = db_id
            # if is_relevant:
            self._add_entry_with_index("api_results", {
                "api_name": api_name,
                "arguments": arguments,
                "relevant_result_snippets": relevant_result_snippets,
            })
        self.conn.commit()
        return uid_to_db_id

    def store_questions_and_associations(self, traj_analysis_result, uid_to_db_id):
        """
        Stores questions and their associations with API results in the database.

        Parameters:
            traj_analysis_result (dict): The result of trajectory analysis containing questions and answers.
            uid_to_db_id (dict): Dictionary mapping tool call UIDs to database IDs.
        """
        cursor = self.conn.cursor()

        # Insert questions into questions_table
        for question_type in ['open_questions', 'fully_answered_qns']:
            questions = traj_analysis_result.get(question_type, [])
            for question in questions:
                cursor.execute(
                    """
                    INSERT INTO questions_table (question, answer, is_fully_answered)
                    VALUES (?, ?, ?)
                    """,
                    (question['question_asked'], question.get('answer', ''), question_type == 'fully_answered_qns')
                )
                question_id = cursor.lastrowid

                self._add_entry_with_index("questions_table", {
                    "question": question['question_asked'],
                    "answer": question.get('answer', ''),
                    "is_fully_answered": question_type == 'fully_answered_qns'
                })

                # Insert associations into question_api_result_associations
                for uid in question.get('tool_call_uids', []):
                    api_result_id = uid_to_db_id.get(uid)
                    if api_result_id:
                        cursor.execute(
                            """
                            INSERT INTO question_api_result_associations (question_id, api_result_id)
                            VALUES (?, ?)
                            """,
                            (question_id, api_result_id)
                        )

        self.conn.commit()

    def upload_trajectory_summary(self, traj_summary):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO summaries (subject, type, summary)
            VALUES (?, ?, ?)
            """,
            ('', 'trajectory_summary', traj_summary)
        )

        self._add_entry_with_index("summaries", {
            "subject": '',
            "type": 'trajectory_summary',
            "summary": traj_summary
        })
        self.conn.commit()

    def update_trajectory_analysis(self, traj_analysis_result):
        uid_to_db_id = self.update_api_results_db(traj_analysis_result['tool_call_sequence_info'])
        # self.update_layer_analyses_db(traj_analysis_result['layer_analyses'])
        self.store_questions_and_associations(traj_analysis_result, uid_to_db_id)

        # For now we put patterns frm both positive and negative calls in the same table
        self.upload_patterns(traj_analysis_result['positive_patterns'])
        self.upload_patterns(traj_analysis_result['negative_patterns'])

    def update_call_graph(self, subject, call_graph):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO call_graphs (subject, call_graph)
            VALUES (?, ?)
            """,
            (subject, call_graph)
        )

        self._add_entry_with_index("call_graphs", {
            "subject": subject,
            "call_graph": call_graph
        })
        self.conn.commit()

    def prune_context_memory(self, indices_to_keep):
        for table in self.context_memory:
            self.context_memory[table] = [
                entry for entry in self.context_memory[table] if entry['index'] in indices_to_keep
            ]

    # deprecated
    def update_layer_analyses_db(self, layer_analyses):
        """
        Populates the api_results table from the layer_analyses data.

        Parameters:
            db_path (str): Path to the SQLite database.
            layer_analyses (list): List of layer analysis dictionaries.
        """
        cursor = self.conn.cursor()

        for layer_analysis in layer_analyses:
            cursor.execute(
                """
                INSERT INTO layer_analysis (
                    hypothesis, hypothesis_validation, tool_call_msg
                ) VALUES (?, ?, ?)
                """,
                (
                    layer_analysis['hypothesis'],
                    layer_analysis['hypothesis_validation'],
                    layer_analysis['tool_call_msg']
                )
            )
            layer_analysis_id = cursor.lastrowid

            tool_call_layer_info = layer_analysis['tool_call_layer_info']
            for tool_call_d in tool_call_layer_info:
                tool_call = tool_call_d['tool_call']
                api_name = tool_call['func_name']
                arguments = json.dumps(tool_call['arguments'])
                result = tool_call_d['result']
                reasoning = tool_call_d['reasoning']
                is_relevant = tool_call_d['is_relevant']
                relevant_result_snippets = tool_call_d['relevant_result_snippets']

                cursor.execute(
                    """
                    INSERT INTO api_results (
                        layer_analysis_id, api_name, arguments, result, reasoning, is_relevant, relevant_result_snippets
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (layer_analysis_id, api_name, arguments, result, reasoning, is_relevant, relevant_result_snippets)
                )

        self.conn.commit()
