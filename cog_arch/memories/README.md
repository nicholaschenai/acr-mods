# KG principles

## Attribute versioning vs new nodes

### When to Use Versioning of Attributes

1. **Minor Updates**:
    - Use versioning for minor updates or refinements to existing attributes that do not fundamentally change the identity or role of the node.
    - Example: Updating the `code_str` of a `CodebaseLocationNode` as more detailed information becomes available.

2. **Continuous Tracking**:
    - Use versioning to continuously track changes over time without altering the node's identity.
    - Example: Tracking the `relevance` or `explored` status of a `CodebaseLocationNode`
    
3. **Attribute-Specific History**:
    - Use versioning when you need to maintain a history of changes for specific attributes.
    - Example: Keeping a history of `code_str` changes to understand how the code evolved.

### When to Create New Nodes

1. **Significant Changes**:
    - Create new nodes for significant changes that alter the identity, role, or context of the node.
    - Example: Disproving a hypothesis and creating a new one with a different focus.

2. **Contextual Shifts**:
    - Create new nodes when the context or scope of the node changes significantly.
    - Example: Moving from a high-level suspicion to a detailed investigation in a different part of the codebase.

3. **Maintaining Coherence**:
    - Create new nodes to maintain coherence and clarity in the knowledge graph, especially when the changes are substantial.
    - Example: Creating a new `PatchNode` for each new patch applied, rather than updating an existing one.
