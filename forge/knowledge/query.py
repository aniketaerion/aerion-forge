"""Typed, deterministic, read-only graph query foundation."""

from forge.knowledge.models import (
    KnowledgeEdge,
    KnowledgeEdgeType,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeOrphans,
)


class KnowledgeGraphQuery:
    """Provide bounded structural lookups without a query language."""

    def __init__(self, graph: KnowledgeGraph, orphans: KnowledgeOrphans | None = None) -> None:
        self.graph = graph
        self.orphans = orphans or KnowledgeOrphans()
        self._nodes = {node.node_id: node for node in graph.nodes}

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: KnowledgeNodeType) -> list[KnowledgeNode]:
        return [node for node in self.graph.nodes if node.node_type is node_type]

    def get_edges_from(self, node_id: str) -> list[KnowledgeEdge]:
        return [edge for edge in self.graph.edges if edge.source_node_id == node_id]

    def get_edges_to(self, node_id: str) -> list[KnowledgeEdge]:
        return [edge for edge in self.graph.edges if edge.target_node_id == node_id]

    def get_neighbors(self, node_id: str) -> list[KnowledgeNode]:
        identifiers = {edge.target_node_id for edge in self.get_edges_from(node_id)} | {
            edge.source_node_id for edge in self.get_edges_to(node_id)
        }
        return [
            self._nodes[identifier]
            for identifier in sorted(identifiers)
            if identifier in self._nodes
        ]

    def get_files_for_component(self, component_id: str) -> list[KnowledgeNode]:
        identifiers = {
            edge.target_node_id
            for edge in self.get_edges_from(component_id)
            if edge.edge_type is KnowledgeEdgeType.HAS_FILE
        }
        return [self._nodes[value] for value in sorted(identifiers) if value in self._nodes]

    def get_component_for_file(self, file_id: str) -> KnowledgeNode | None:
        edges = [
            edge
            for edge in self.get_edges_from(file_id)
            if edge.edge_type is KnowledgeEdgeType.BELONGS_TO
        ]
        return self._nodes.get(edges[0].target_node_id) if edges else None

    def get_technologies_for_component(self, component_id: str) -> list[KnowledgeNode]:
        technology_relations = {
            KnowledgeEdgeType.USES_LANGUAGE,
            KnowledgeEdgeType.USES_FRAMEWORK,
            KnowledgeEdgeType.USES_PACKAGE_MANAGER,
            KnowledgeEdgeType.USES_BUILD_SYSTEM,
            KnowledgeEdgeType.USES_TEST_FRAMEWORK,
            KnowledgeEdgeType.USES_DATABASE,
        }
        identifiers = {
            edge.target_node_id
            for edge in self.get_edges_from(component_id)
            if edge.edge_type in technology_relations
        }
        return [self._nodes[value] for value in sorted(identifiers) if value in self._nodes]

    def get_manifests_for_component(self, component_id: str) -> list[KnowledgeNode]:
        identifiers = {
            edge.target_node_id
            for edge in self.get_edges_from(component_id)
            if edge.edge_type is KnowledgeEdgeType.HAS_MANIFEST
        }
        return [self._nodes[value] for value in sorted(identifiers) if value in self._nodes]

    def get_dependencies_for_manifest(self, manifest_id: str) -> list[KnowledgeNode]:
        identifiers = {
            edge.target_node_id
            for edge in self.get_edges_from(manifest_id)
            if edge.edge_type is KnowledgeEdgeType.DECLARES_DEPENDENCY
        }
        return [self._nodes[value] for value in sorted(identifiers) if value in self._nodes]

    def get_orphans(self) -> KnowledgeOrphans:
        return self.orphans.model_copy(deep=True)
