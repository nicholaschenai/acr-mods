import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from typing import Optional, Union, Literal, Any, Dict
from datetime import datetime

from cognitive_base.memories.base_mem import BaseMem
from cognitive_base.utils.database.graph_db.nx_db import NxDb


class DeclarativeMem(BaseMem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_db('knowledge_graph', NxDb())
        self.timestamp = 0
        self.episodic_window = 5
        self.current_episode_buffer = []
        self.episodic_buffer = []
        self.latest_episodic_node = None
        # TODO: future: allow user to set this. update timestamp whenever episodic added
        self.auto_update_timestamp = True

    """
    helpers
    """
    def update_time(self, timestamp: Optional[Union[int, datetime]] = None):
        # TODO: future: see if wna do this buffer. rn can retrieve frm graph
        self.episodic_buffer.append(self.current_episode_buffer)
        if len(self.episodic_buffer) > self.episodic_window:
            self.episodic_buffer.pop(0)
        self.current_episode_buffer = []
        if timestamp is not None:
            self.timestamp = timestamp
        else:
            self.timestamp += 1
            
    def visualize_knowledge_graph(self, max_node_len=30, figsize=(15, 10), task_name=''):
        G = self.dbs['knowledge_graph'].graph
        # TODO: future: Subset the graph if a criterion is provided
        # if subset_criterion:
        #     G = nx.subgraph_view(G, filter_node=subset_criterion)

        # Aim: Ensure episodic nodes are plotted in a line
        episodic_nodes = [node for node, data in G.nodes(data=True) if data.get('mem_type') == 'episodic']

        # Use spring layout for initial positioning
        pos = nx.spring_layout(G, k=0.5)

        # Determine the leftmost and rightmost x-coordinates
        x_coords = [pos[node][0] for node in pos]
        leftmost_x = min(x_coords)
        rightmost_x = max(x_coords)

        # Calculate the spacing between episodic nodes
        num_episodic_nodes = len(episodic_nodes)
        if num_episodic_nodes > 1:
            spacing = (rightmost_x - leftmost_x) / (num_episodic_nodes - 1)
        else:
            spacing = rightmost_x - leftmost_x

        # Manually set positions for episodic nodes
        for i, node in enumerate(episodic_nodes):
            pos[node] = (leftmost_x + i * spacing, 0)

        # Create a colormap
        cmap = plt.get_cmap('tab20')

        # Map node_id to colors
        unique_node_types = list(set(nx.get_node_attributes(G, 'node_type').values()))
        node_norm = mcolors.Normalize(vmin=0, vmax=len(unique_node_types))
        node_type_to_color = {node_id: cmap(node_norm(i)) for i, node_id in enumerate(unique_node_types)}
        node_colors = [node_type_to_color[G.nodes[node].get('node_type', 'default')] for node in G.nodes]

        # Map relation to colors
        unique_relations = list(set(nx.get_edge_attributes(G, 'relation').values()))
        edge_norm = mcolors.Normalize(vmin=0, vmax=len(unique_relations))
        relation_to_color = {relation: cmap(edge_norm(i)) for i, relation in enumerate(unique_relations)}
        edge_colors = [relation_to_color[G.edges[edge].get('relation', 'default')] for edge in G.edges]

        labels = {node: (str(node)[:max_node_len] + '...') if len(str(node)) > max_node_len else str(node) for node in G.nodes}

        plt.figure(figsize=figsize)
        nx.draw(G, pos, labels=labels, with_labels=True, node_size=700, node_color=node_colors, font_size=10,
                font_color="black", font_weight="bold", edge_color=edge_colors)

        edge_labels = nx.get_edge_attributes(G, 'relation')
        for edge, label in edge_labels.items():
            nx.draw_networkx_edge_labels(G, pos, edge_labels={edge: label},
                                         font_color=relation_to_color[G.edges[edge].get('relation', 'default')])

        # Save the graph to a file
        file_suffix = f"_{task_name}" if task_name else ""
        plt.savefig(f"{self.ckpt_dir}/knowledge_graph{file_suffix}.png")

    """
    basic CRUD
    """
    
    def add_node_with_checks(self, node_id: str, verbose=False, **attributes: Any) -> None:
        """
        Add / update a node to the knowledge graph with checks as attributes will override
        currently we only check that code_str should only be updated to be longer

        Args:
            node_id (str): The ID of the node to add.
            verbose (bool): Whether to print verbose output.
            attributes (dict): A dictionary of attributes for the node.
        """
        kg = self.dbs['knowledge_graph']

        # we only update time if episodic node is new
        new_episodic = attributes.get('mem_type', None) == 'episodic' and node_id not in kg.graph.nodes
        if new_episodic:
            attributes['timestamp'] = self.timestamp

        if 'code_str' in attributes:
            if node_id in kg.graph.nodes:
                existing_node_attr = kg.get_node(node_id)
                if 'code_str' in existing_node_attr:
                    if len(attributes['code_str']) <= len(existing_node_attr['code_str']):
                        attributes['code_str'] = existing_node_attr['code_str']

        has_diff = kg.add_node(node_id, verbose=verbose, **attributes)

        if has_diff:
            entry = f"node_id: {node_id}\nattributes:\n{json.dumps(attributes, indent=4)}"
            metadata = {'node_id': node_id}
            self.update_ebd(entry, metadata=metadata, doc_id=node_id)

        # perform most operations after node is added
        if new_episodic:
            self.episodic_buffer.append(node_id)
            self._auto_link_episodic_node(node_id, verbose=verbose)
            if self.auto_update_timestamp:
                self.update_time()

    def get(self, memory):
        pass

    def add_edge_with_checks(self, subject: str, obj: str, relation: str, verbose=False, update=True,
                             old_desc_limit=None, **attributes) -> None:
        """
        Add an edge to the knowledge graph with checks.
        currently we check if theres an  existing description and if so, we add it to old_descriptions

        Args:
            subject (str): The ID of the first node.
            relation (str): The type of relation between the entities.
            obj (str): The ID of the second node.
            verbose (bool): Whether to print verbose output.
            update (bool): Whether to update the existing edge attributes if the edge already exists.
            attributes (dict): A dictionary of attributes for the edge.
        """
        knowledge_graph = self.dbs['knowledge_graph']

        # TODO: future: this can be reused for any attribute that we wna keep history of
        if 'description' in attributes and knowledge_graph.graph.has_edge(subject, obj):
            existing_attributes = knowledge_graph.graph.get_edge_data(subject, obj)
            existing_desc = existing_attributes.get('description', None)
            if existing_desc is not None:
                existing_old_descriptions = existing_attributes.get('old_descriptions', None)
                old_descriptions = (existing_old_descriptions if existing_old_descriptions else []) + [existing_desc]
                if old_desc_limit is not None and len(old_descriptions) > old_desc_limit:
                    old_descriptions = old_descriptions[-old_desc_limit:]
                attributes['old_descriptions'] = old_descriptions

        has_diff, new_attr = knowledge_graph.add_edge(subject, obj, relation, verbose=verbose, update=update, **attributes)

        if has_diff:
            entry = f"subject: {subject}\nrelation: {relation}\nobject: {obj}\nattributes:\n{json.dumps(new_attr, indent=4)}"
            metadata = {'subject': subject, 'object': obj}
            doc_id = f"({subject}, {obj})"
            self.update_ebd(entry, metadata=metadata, doc_id=doc_id)

    def delete(self, memory):
        pass

    def add_graph_elements(self, nodes=None, edges=None, verbose=False):
        """
        Add nodes and edges to the knowledge graph. Handles both dataclass and dict inputs.

        Args:
            nodes (list): A list of nodes to add. Each node can be a dataclass or a dict.
            edges (list): A list of edges to add. Each edge can be a dataclass or a dict.
            verbose (bool): Whether to print verbose output.
        """
        if nodes:
            for node in nodes:
                if hasattr(node, 'dict_clean'):
                    node_data = node.dict_clean()
                else:
                    node_data = node
                self.add_node_with_checks(verbose=verbose, **node_data)

        if edges:
            for edge in edges:
                if hasattr(edge, 'dict_clean'):
                    edge_data = edge.dict_clean()
                else:
                    edge_data = edge
                self.add_edge_with_checks(verbose=verbose, **edge_data)


    
    # Private method to auto-link episodic nodes
    def _auto_link_episodic_node(self, node_id, verbose=False):
        if self.latest_episodic_node is not None:
            self.add_edge_with_checks(self.latest_episodic_node, node_id, 'temporal', verbose=verbose)
        self.latest_episodic_node = node_id

    # TODO: Retrieve the sequence of episodic nodes. maybe allow window
    def get_episodic_sequence(self):
        pass
        # sequence = []
        # current_node = self.latest_episodic_node
        # while current_node is not None:
        #     sequence.append(current_node)
        #     predecessors = list(self.graph.predecessors(current_node))
        #     current_node = predecessors[0] if predecessors else None
        # return sequence[::-1]  # Reverse to get the sequence from the beginning


    # TODO: , also ensure neighbors are not temporal
    def summarize_patch_results(self, patch_node_id: str) -> Dict[str, Any]:
        pass
        # knowledge_graph = self.dbs['knowledge_graph']
        # patch_node = knowledge_graph.get_node(patch_node_id)
        # test_suite_nodes = knowledge_graph.get_neighbors(patch_node_id)
        
        # summary = {
        #     'total_tests': 0,
        #     'passed_tests': 0,
        #     'failed_tests': 0,
        #     'failed_tests_summary': []
        # }

        # for test_suite_node_id in test_suite_nodes:
        #     test_result_nodes = knowledge_graph.get_neighbors(test_suite_node_id)
        #     for test_result_node_id in test_result_nodes:
        #         test_result_node = knowledge_graph.get_node(test_result_node_id)
        #         summary['total_tests'] += 1
        #         if test_result_node['test_passed']:
        #             summary['passed_tests'] += 1
        #         else:
        #             summary['failed_tests'] += 1
        #             summary['failed_tests_summary'].append(test_result_node['traceback'])

        # summary['tests_passed'] = summary['failed_tests'] == 0
        # return summary
    
    """
    retrieval
    """
    # by simple rule based attribute
    def get_suspicious_nodes(self):
        """
        Get nodes that are suspicious 

        Returns:
            list: A list of suspicious nodes.
        """
        return self.dbs['knowledge_graph'].get_nodes_by_attribute('relevance', 'suspicious')
    
    # by rigid match eg keyword search
    def search_keyword(self, keyword: str):
        """
        Search for a keyword in the attributes of nodes and edges in the knowledge graph.

        Args:
            keyword (str): The keyword to search for.

        Returns:
            dict: A dictionary with two keys 'nodes' and 'edges', each containing a list of matching nodes and edges.
        """
        return self.dbs['knowledge_graph'].search_keyword(keyword)

    def add_neighbor_nodes_and_edges(self, nodes_set, edges_set, node_id):
        kg = self.dbs['knowledge_graph']
        edges = kg.get_neighbor_edges(node_id)
        for subject, obj in edges:
            nodes_set.add(subject)
            nodes_set.add(obj)
            edges_set.add((subject, obj))

    def hybrid_graph_retrieval(self, query: str):
        # from query, vector retrieve nodes and edges
        retrieved_nodes_and_edges = self.retrieve_by_ebd(query, k=1)
        
        nodes = set()
        edges = set()
        kg = self.dbs['knowledge_graph']
        for ele in retrieved_nodes_and_edges:
            metadata = ele.metadata
            if 'node_id' in metadata:
                # if node retrieved, get edges and neighbors.
                node_id = metadata['node_id']
                self.add_neighbor_nodes_and_edges(nodes, edges, node_id)
            elif 'subject' in metadata:
                # if edge retrieved, branch out one step n add nodes n edges
                self.add_neighbor_nodes_and_edges(nodes, edges, metadata['subject'])
                self.add_neighbor_nodes_and_edges(nodes, edges, metadata['object'])
            else:
                raise ValueError(f"Unknown element type: {ele}")

        # Convert sets to lists and sort them for consistent ordering
        nodes_list = sorted(list(nodes))
        edges_list = sorted(list(edges))

        # for the elements below, number them, construct dict of number -> element id
        element_id_mapping = {}
        display_str = ""
        element_counter = 1

        # display nodes (name, type) and summary if available
        for node_id in nodes_list:
            data = kg.graph.nodes[node_id]
            node_type = data.get('node_type')
            # for now skip summary as patch summary can be quite long and confusing
            # summary = data.get('summary', '')
            # display_str += f"{element_counter}. Node: {node_id}, Type: {node_type}" + (f", Summary: {summary}\n" if summary else "\n")
            display_str += f"{element_counter}. Node: {node_id}, Type: {node_type}" + "\n"
            element_id_mapping[element_counter] = {'element_id': node_id, 'data': data}
            element_counter += 1

        # display edges (node name, relation, node name) and desc if available
        for subject, obj in edges_list:
            edge_data = kg.graph.get_edge_data(subject, obj)
            description = edge_data.get('description', '')
            relation = edge_data.get('relation')
            display_str += f"{element_counter}. Edge: {subject} -[{relation}]-> {obj}"
            display_str += f", Description: {description}\n" if description else "\n"
            element_id_mapping[element_counter] = {
                'element_id': (subject, obj),
                'data': edge_data,
                'subject_data': kg.graph.nodes[subject],
                'object_data': kg.graph.nodes[obj]
            }
            element_counter += 1

        return display_str, element_id_mapping
