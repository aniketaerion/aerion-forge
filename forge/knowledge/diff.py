"""Deterministic node and edge graph comparison."""

from typing import Any

from forge.knowledge.models import (
    GraphChangeType,
    KnowledgeEdge,
    KnowledgeGraphChange,
    KnowledgeGraphChangeSet,
    KnowledgeNode,
)


def _signature(value: KnowledgeNode | KnowledgeEdge) -> dict[str, Any]:
    return value.model_dump(exclude={"first_observed_generation", "last_observed_generation"})


def diff_graph(
    previous_nodes: list[KnowledgeNode],
    previous_edges: list[KnowledgeEdge],
    current_nodes: list[KnowledgeNode],
    current_edges: list[KnowledgeEdge],
) -> KnowledgeGraphChangeSet:
    """Compare complete graph states by canonical identity and stable representation."""
    changes = KnowledgeGraphChangeSet()
    _diff_entities(
        {item.node_id: item for item in previous_nodes},
        {item.node_id: item for item in current_nodes},
        changes.added_nodes,
        changes.modified_nodes,
        changes.removed_nodes,
        changes.unchanged_nodes,
    )
    _diff_entities(
        {item.edge_id: item for item in previous_edges},
        {item.edge_id: item for item in current_edges},
        changes.added_edges,
        changes.modified_edges,
        changes.removed_edges,
        changes.unchanged_edges,
    )
    return changes


def _diff_entities(
    previous: dict[str, KnowledgeNode | KnowledgeEdge],
    current: dict[str, KnowledgeNode | KnowledgeEdge],
    added: list[KnowledgeGraphChange],
    modified: list[KnowledgeGraphChange],
    removed: list[KnowledgeGraphChange],
    unchanged: list[KnowledgeGraphChange],
) -> None:
    for identifier in sorted(set(current) - set(previous)):
        added.append(KnowledgeGraphChange(change_type=GraphChangeType.ADDED, entity_id=identifier))
    for identifier in sorted(set(previous) - set(current)):
        removed.append(
            KnowledgeGraphChange(change_type=GraphChangeType.REMOVED, entity_id=identifier)
        )
    for identifier in sorted(set(previous) & set(current)):
        target = (
            modified
            if _signature(previous[identifier]) != _signature(current[identifier])
            else unchanged
        )
        change_type = GraphChangeType.MODIFIED if target is modified else GraphChangeType.UNCHANGED
        target.append(KnowledgeGraphChange(change_type=change_type, entity_id=identifier))
