"""
dataclasses for knowledge graph data
"""
from dataclasses import dataclass, asdict, field
from typing import Optional, Union, Literal
from datetime import datetime


@dataclass
class BaseNode:
    node_id: str
    node_type: Optional[str] = None
    description: Optional[str] = None
    mem_type: Optional[Literal['procedural', 'semantic', 'episodic']] = None
    summary: Optional[str] = None
    importance: Optional[int] = None
    importance_reason: Optional[str] = None

    def dict_clean(self):
        # so we dont have None values in the dict to override existing values during node update
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class EpisodicNode(BaseNode):
    timestamp: Optional[Union[int, datetime]] = None

    def __post_init__(self):
        # super().__post_init__()
        self.mem_type = 'episodic'


@dataclass
class SemanticNode(BaseNode):
    def __post_init__(self):
        # super().__post_init__()
        self.mem_type = 'semantic'


@dataclass
class CodebaseLocationNode(SemanticNode):
    file_name: Optional[str] = None
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    code_str: Optional[str] = None
    exists: Optional[Literal['True', 'False', 'Unknown']] = None
    relevance: Optional[str] = None
    additional_info: Optional[str] = None
    explored: Optional[bool] = None


@dataclass
class CodeSnippetNode(SemanticNode):
    # for search API arguments
    code_str: Optional[str] = None
    exists: Optional[Literal['True', 'False', 'Unknown']] = None

    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'code_snippet'


# TODO: when properly migraded to test suite node, remove failed tests summary n tests passed
@dataclass
class PatchNode(EpisodicNode):
    diff: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'patch'


@dataclass
class TestCaseNode(SemanticNode):
    test_name: Optional[str] = None
    test_path: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'test_case'


@dataclass
class TestResultNode(SemanticNode):
    test_passed: Optional[bool] = None
    traceback: Optional[str] = None
    test_path: Optional[str] = None
    test_name: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'test_result'


# test suite node (episodic) when a test suite is run, results of individual tests are stored as test results node
@dataclass
class TestSuiteNode(EpisodicNode):
    suite_name: Optional[str] = None
    failed_tests_summary: Optional[str] = None
    tests_passed: Optional[bool] = None

    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'test_suite'


# example showing what if need to store more stuff adhoc
# from dataclasses import field
#
# @dataclass
# class CodebaseLocationNode:
#     additional_info: Optional[dict] = field(default_factory=dict)


@dataclass
class FunctionalityNode(SemanticNode):
    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'functionality'


@dataclass
class IssueNode(SemanticNode):
    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'issue'


@dataclass
class IntendedBehaviorNode(SemanticNode):
    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'intended_behavior'


@dataclass
class ReasoningNode(SemanticNode):
    def __post_init__(self):
        super().__post_init__()
        self.node_type: str = 'reasoning'


# TODO: tool call layer node (episodic)
# TODO: tool call result node (semantic) with call_ok


@dataclass
class BaseEdge:
    subject: str
    relation: str
    obj: str
    description: Optional[str] = None
    old_descriptions: Optional[list] = None

    def dict_clean(self):
        # so we dont have None values in the dict to override existing values during node update
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ContainsEdge(BaseEdge):
    relation: Literal['contains', 'does_not_contain']
