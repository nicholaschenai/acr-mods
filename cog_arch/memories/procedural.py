import json
import logging

from cognitive_base.memories.procedural.base_procedural_mem import BaseProceduralMem

logger = logging.getLogger("logger")


class ProceduralMem(BaseProceduralMem):
    """
    A class representing the procedural memory component of a cognitive architecture.
    This class is responsible for managing and interacting with a vector database and others to store,
    retrieve, and update procedural knowledge in the form of rules and embeddings.

    Attributes:
        retrieval_top_k (int): The maximum number of entries to retrieve from the vector database.
        ckpt_dir (str): The directory where checkpoints are stored.
        vectordb_name (str): The name of the vector database.
    """
    def __init__(
            self,
            retrieval_top_k=5,
            ckpt_dir="ckpt",
            vectordb_name="procedural",
            **kwargs,
    ):
        super().__init__(
            retrieval_top_k=retrieval_top_k,
            ckpt_dir=ckpt_dir,
            vectordb_name=vectordb_name,
            **kwargs,
        )

    """
    helper fns
    """
    @staticmethod
    def construct_text_rule(rule):
        """
        Converts a JSON rule into a text format suitable for embedding.

        Args:
            rule (dict): The rule to be converted, containing 'actions', 'flexible_conditions',
                         and 'rigid_conditions'.

        Returns:
            tuple[str, str]: A tuple containing the conditions and actions as JSON strings.
        """
        actions = rule['actions']
        conditions = rule['flexible_conditions']
        if not conditions:
            # in case no flexible conditions
            conditions = rule['rigid_conditions']
        return json.dumps(conditions, indent=4), json.dumps(actions, indent=4)

    """
    Retrieval Actions (to working mem / decision procedure)
    """
    # TODO: doublecheck below can be removed cos base mem has it
    # def retrieve_by_ebd(self, query, db=None, db_name=""):
    #     """
    #     Retrieves entries from the vector database based on similarity to a query embedding.
    #
    #     Args:
    #         query: The query embedding.
    #         db: The database to query. If None, the default database is used.
    #         db_name (str): The name of the database. If empty, the default database name is used.
    #
    #     Returns:
    #         list: A list of documents retrieved from the database.
    #     """
    #     if db is None:
    #         db = self.vectordb
    #     if not db_name:
    #         db_name = self.vectordb_name
    #
    #     k = min(db.count(), self.retrieval_top_k)
    #     docs = []
    #     if k:
    #         logger.info(f"\033[33m Retrieving {k} entries for db: {db_name} \n \033[0m")
    #         docs = db.similarity_search(query, k=k)
    #
    #     return docs

    """
    Learning Actions (from working mem)
    """
    # TODO: doublecheck below can be removed cos base mem has it
    # def update_ebd(self, entry, metadata=None, db=None):
    #     """
    #     Stores an embedding in the vector database.
    #
    #     Args:
    #         entry: The embedding to store.
    #         metadata (dict): Optional metadata associated with the embedding.
    #         db: The database where the embedding should be stored. If None, the default database is used.
    #     """
    #     if db is None:
    #         db = self.vectordb
    #
    #     db.add_texts(texts=[entry], metadatas=[metadata])
    #     # TODO: below is chroma specific, remove soon
    #     db.persist()

    def update_rules(self, rules):
        """
        Stores rules in JSON format and their embeddings in the vector database.

        Args:
            rules (list): A list of rules to be stored.
        """
        for rule in rules:
            if (not rule['flexible_conditions'] and not rule['rigid_conditions']) or not rule['actions']:
                continue
            self.add_rule(rule)
            conditions_str, actions_str = self.construct_text_rule(rule)
            self.update_ebd(conditions_str, metadata={"actions_str": actions_str})
