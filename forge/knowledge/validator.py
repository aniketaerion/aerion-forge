"""Strict structural knowledge graph integrity validation."""

import re
from collections import Counter

from forge.indexing.models import IndexStatus, ProjectIndex
from forge.knowledge.errors import KnowledgeGraphValidationError
from forge.knowledge.models import (
    GraphValidationResult,
    KnowledgeGraph,
    KnowledgeNodeType,
)

ABSOLUTE_PATH = re.compile(r"^(?:[a-zA-Z]:[/\\]|/|\\\\)")


class KnowledgeGraphValidator:
    """Validate identities, references, compatibility, portability, and statistics."""

    def validate(self, graph: KnowledgeGraph, project_index: ProjectIndex) -> GraphValidationResult:
        """Return validation details without mutating graph state."""
        errors: list[str] = []
        node_ids = [node.node_id for node in graph.nodes]
        edge_ids = [edge.edge_id for edge in graph.edges]
        if len(node_ids) != len(set(node_ids)):
            errors.append("duplicate node ID")
        if len(edge_ids) != len(set(edge_ids)):
            errors.append("duplicate edge ID")
        known = set(node_ids)
        for edge in graph.edges:
            if edge.source_node_id not in known:
                errors.append(f"missing edge source: {edge.edge_id}")
            if edge.target_node_id not in known:
                errors.append(f"missing edge target: {edge.edge_id}")
            if edge.source_node_id == edge.target_node_id:
                errors.append(f"forbidden self-edge: {edge.edge_id}")
        generation = graph.generation
        if generation.repository_identity != project_index.generation.repository_identity:
            errors.append("repository identity mismatch")
        if generation.workspace_id != project_index.generation.workspace_id:
            errors.append("workspace identity mismatch")
        if generation.source_index_generation_id != project_index.generation.generation_id:
            errors.append("source index generation mismatch")
        if (
            generation.source_index_state_fingerprint
            != project_index.generation.repository_state_fingerprint
        ):
            errors.append("source index state mismatch")
        if not any(node.node_type is KnowledgeNodeType.REPOSITORY for node in graph.nodes):
            errors.append("repository root node missing")
        indexed_paths = {
            item.normalized_path
            for item in project_index.files
            if item.index_status is IndexStatus.INDEXED and not item.ignored
        }
        represented_paths = {
            node.path
            for node in graph.nodes
            if node.path
            and node.node_type
            in {
                KnowledgeNodeType.FILE,
                KnowledgeNodeType.MANIFEST,
                KnowledgeNodeType.CONFIGURATION,
                KnowledgeNodeType.DOCUMENTATION,
                KnowledgeNodeType.CONTAINER,
                KnowledgeNodeType.KUBERNETES,
                KnowledgeNodeType.CI_PIPELINE,
                KnowledgeNodeType.INFRASTRUCTURE,
                KnowledgeNodeType.MIGRATION_AREA,
                KnowledgeNodeType.SCHEMA_AREA,
            }
        }
        if represented_paths != indexed_paths:
            errors.append("file nodes do not match indexed files")
        for node in graph.nodes:
            if node.repository_identity != generation.repository_identity:
                errors.append(f"node repository mismatch: {node.node_id}")
            if node.workspace_id != generation.workspace_id:
                errors.append(f"node workspace mismatch: {node.node_id}")
            if node.path and ABSOLUTE_PATH.match(node.path):
                errors.append(f"absolute portable path: {node.node_id}")
        stats = generation.statistics
        if stats.node_count != len(graph.nodes) or stats.edge_count != len(graph.edges):
            errors.append("graph statistics mismatch")
        if stats.nodes_by_type != dict(
            sorted(Counter(node.node_type.value for node in graph.nodes).items())
        ):
            errors.append("node type statistics mismatch")
        if stats.edges_by_type != dict(
            sorted(Counter(edge.edge_type.value for edge in graph.edges).items())
        ):
            errors.append("edge type statistics mismatch")
        return GraphValidationResult(valid=not errors, errors=sorted(set(errors)))

    def require_valid(self, graph: KnowledgeGraph, project_index: ProjectIndex) -> None:
        """Raise when graph integrity checks fail."""
        result = self.validate(graph, project_index)
        if not result.valid:
            raise KnowledgeGraphValidationError("; ".join(result.errors))
