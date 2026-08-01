"""Deterministic portable knowledge graph reports."""

import json

from forge.knowledge.models import KnowledgeGraphChange, KnowledgeGraphResult


def _json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n"


def _items(values: list[str]) -> str:
    return "\n".join(f"- `{value}`" for value in values) if values else "None."


def _changes(values: list[KnowledgeGraphChange]) -> list[str]:
    return [item.entity_id for item in values]


class KnowledgeGraphRenderer:
    """Render graph, changes, nodes, edges, and orphan analysis."""

    def render(self, result: KnowledgeGraphResult) -> dict[str, str]:
        graph = result.graph.model_dump(mode="json")
        changes = result.changes.model_dump(mode="json")
        orphans = result.orphans.model_dump(mode="json")
        return {
            "KNOWLEDGE_GRAPH.json": _json(graph),
            "KNOWLEDGE_GRAPH_SUMMARY.json": _json(graph["generation"]),
            "KNOWLEDGE_GRAPH_CHANGES.json": _json(changes),
            "KNOWLEDGE_NODES.json": _json({"nodes": graph["nodes"]}),
            "KNOWLEDGE_EDGES.json": _json({"edges": graph["edges"]}),
            "KNOWLEDGE_ORPHANS.json": _json(orphans),
            "KNOWLEDGE_GRAPH_SUMMARY.md": self._summary(result),
            "KNOWLEDGE_GRAPH_CHANGES.md": self._change_report(result),
            "KNOWLEDGE_ORPHANS.md": self._orphan_report(result),
        }

    @staticmethod
    def _summary(result: KnowledgeGraphResult) -> str:
        generation = result.graph.generation
        stats = generation.statistics
        return f"""# Knowledge Graph Summary

- Generation: `{generation.generation_id}`
- Previous generation: `{generation.previous_generation_id or "none"}`
- Graph state: `{generation.graph_state_fingerprint}`
- Source index generation: `{generation.source_index_generation_id}`
- Source index state: `{generation.source_index_state_fingerprint}`
- Nodes: {stats.node_count}
- Edges: {stats.edge_count}
- Orphans: {stats.orphan_node_count}
- Unassigned files: {stats.unassigned_file_count}
- Validation: {generation.validation_status}
"""

    @staticmethod
    def _change_report(result: KnowledgeGraphResult) -> str:
        changes = result.changes
        return f"""# Knowledge Graph Changes

## Added Nodes
{_items(_changes(changes.added_nodes))}

## Modified Nodes
{_items(_changes(changes.modified_nodes))}

## Removed Nodes
{_items(_changes(changes.removed_nodes))}

## Added Edges
{_items(_changes(changes.added_edges))}

## Modified Edges
{_items(_changes(changes.modified_edges))}

## Removed Edges
{_items(_changes(changes.removed_edges))}
"""

    @staticmethod
    def _orphan_report(result: KnowledgeGraphResult) -> str:
        orphans = result.orphans
        return f"""# Knowledge Graph Orphans

## Orphan Nodes
{_items(orphans.orphan_node_ids)}

## Unassigned Files
{_items(orphans.unassigned_file_ids)}

## Unknown-Role Files
{_items(orphans.unknown_role_file_ids)}

## Unowned Manifests
{_items(orphans.unowned_manifest_ids)}

## Components Without Manifests
{_items(orphans.components_without_manifest_ids)}
"""
