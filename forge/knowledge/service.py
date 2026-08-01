"""Knowledge graph input loading, generation, validation, reporting, and persistence."""

import hashlib
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from forge.discovery.models import DiscoveryResult
from forge.indexing.models import ProjectIndex
from forge.indexing.service import IndexingService
from forge.indexing.store import ProjectIndexStore
from forge.knowledge.builder import KnowledgeGraphBuilder
from forge.knowledge.diff import diff_graph
from forge.knowledge.errors import (
    KnowledgeGraphBuildError,
    KnowledgeGraphInputMismatchError,
    KnowledgeGraphInputMissingError,
    KnowledgeGraphReportError,
)
from forge.knowledge.models import (
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeGraphConfiguration,
    KnowledgeGraphGeneration,
    KnowledgeGraphResult,
    KnowledgeGraphStatistics,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeOrphans,
)
from forge.knowledge.renderer import KnowledgeGraphRenderer
from forge.knowledge.store import KnowledgeGraphRepository
from forge.knowledge.validator import KnowledgeGraphValidator


class KnowledgeGraphService:
    """Build a validated graph solely from existing Forge state."""

    def __init__(
        self,
        discovery_path: Path,
        index_store: ProjectIndexStore,
        graph_store: KnowledgeGraphRepository,
        reports_path: Path,
        logger: logging.Logger,
        configuration: KnowledgeGraphConfiguration,
        renderer: KnowledgeGraphRenderer | None = None,
        validator: KnowledgeGraphValidator | None = None,
    ) -> None:
        self.discovery_path = discovery_path
        self.index_store = index_store
        self.graph_store = graph_store
        self.reports_path = reports_path.resolve()
        self.logger = logger
        self.configuration = configuration
        self.renderer = renderer or KnowledgeGraphRenderer()
        self.validator = validator or KnowledgeGraphValidator()

    def build(
        self,
        root: Path,
        workspace_id: str | None = None,
        workspace_name: str | None = None,
    ) -> KnowledgeGraphResult:
        """Load consistent inputs, rebuild, diff, validate, report, and persist."""
        discovery, project_index, identity, discovery_fingerprint = self.load_inputs(
            root, workspace_id
        )
        previous = self.graph_store.get(identity)
        try:
            nodes, edges = KnowledgeGraphBuilder(self.configuration).build(
                discovery, project_index, workspace_id, workspace_name
            )
        except ValueError as exc:
            raise KnowledgeGraphBuildError(str(exc)) from exc
        changes = diff_graph(
            previous.nodes if previous else [],
            previous.edges if previous else [],
            nodes,
            edges,
        )
        state = self._state_fingerprint(
            nodes,
            edges,
            discovery_fingerprint,
            project_index.generation.repository_state_fingerprint,
        )
        generation_id = f"graph-{state[:20]}"
        nodes = self._observe_nodes(nodes, previous, generation_id)
        edges = self._observe_edges(edges, previous, generation_id)
        orphans = self._orphans(nodes, edges)
        previous_generation_id = None
        if previous:
            previous_generation_id = (
                previous.generation.previous_generation_id
                if previous.generation.graph_state_fingerprint == state
                else previous.generation.generation_id
            )
        statistics = self._statistics(nodes, edges, changes, orphans)
        generation = KnowledgeGraphGeneration(
            generation_id=generation_id,
            previous_generation_id=previous_generation_id,
            repository_identity=identity,
            workspace_id=workspace_id,
            source_discovery_fingerprint=discovery_fingerprint,
            source_index_generation_id=project_index.generation.generation_id,
            source_index_state_fingerprint=project_index.generation.repository_state_fingerprint,
            graph_state_fingerprint=state,
            statistics=statistics,
        )
        graph = KnowledgeGraph(generation=generation, nodes=nodes, edges=edges)
        self.validator.require_valid(graph, project_index)
        result = KnowledgeGraphResult(graph=graph, changes=changes, orphans=orphans)
        self._write_reports(result)
        self.graph_store.save(identity, graph)
        self.logger.info(
            "Knowledge graph completed",
            extra={
                "context": {
                    "repository": discovery.repository_name,
                    "nodes": len(nodes),
                    "edges": len(edges),
                    "state": state,
                }
            },
        )
        return result

    def load_inputs(
        self, root: Path, workspace_id: str | None
    ) -> tuple[DiscoveryResult, ProjectIndex, str, str]:
        """Load discovery and index entries and verify repository compatibility."""
        resolved = root.resolve(strict=True)
        identity = workspace_id or IndexingService.repository_identity(resolved)
        project_index = self.index_store.get(identity)
        if project_index is None:
            raise KnowledgeGraphInputMissingError(
                "Project index missing; run 'forge index <target>' first"
            )
        if not self.discovery_path.exists():
            raise KnowledgeGraphInputMissingError(
                "Discovery input missing; run 'forge inspect <target>' first"
            )
        try:
            data = json.loads(self.discovery_path.read_text(encoding="utf-8"))
            records = data.get("results", {})
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            raise KnowledgeGraphInputMissingError(
                f"Discovery input cannot be loaded: {exc}"
            ) from exc
        candidate = records.get(workspace_id) if workspace_id else None
        if candidate is None:
            for value in records.values():
                try:
                    parsed = DiscoveryResult.model_validate(value)
                    if parsed.repository_root.resolve() == resolved:
                        candidate = value
                        break
                except (ValidationError, OSError):
                    continue
        if candidate is None:
            raise KnowledgeGraphInputMissingError(
                "Discovery result missing; run 'forge inspect <target>' first"
            )
        try:
            discovery = DiscoveryResult.model_validate(candidate)
        except ValidationError as exc:
            raise KnowledgeGraphInputMismatchError(f"Discovery result is invalid: {exc}") from exc
        if discovery.repository_root.resolve() != resolved:
            raise KnowledgeGraphInputMismatchError("Discovery repository does not match target")
        if project_index.generation.repository_identity != identity:
            raise KnowledgeGraphInputMismatchError(
                "Index repository identity does not match target"
            )
        if project_index.generation.workspace_id != workspace_id:
            raise KnowledgeGraphInputMismatchError("Index workspace identity does not match target")
        portable_discovery = discovery.model_dump(mode="json", exclude={"repository_root"})
        fingerprint = hashlib.sha256(
            json.dumps(portable_discovery, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return discovery, project_index, identity, fingerprint

    @staticmethod
    def _state_fingerprint(
        nodes: list[KnowledgeNode],
        edges: list[KnowledgeEdge],
        discovery_fingerprint: str,
        index_fingerprint: str,
    ) -> str:
        digest = hashlib.sha256(f"1.0|{discovery_fingerprint}|{index_fingerprint}\n".encode())
        for node in nodes:
            value = node.model_dump(
                mode="json", exclude={"first_observed_generation", "last_observed_generation"}
            )
            digest.update(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
        for edge in edges:
            value = edge.model_dump(
                mode="json", exclude={"first_observed_generation", "last_observed_generation"}
            )
            digest.update(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
        return digest.hexdigest()

    @staticmethod
    def _observe_nodes(
        nodes: list[KnowledgeNode], previous: KnowledgeGraph | None, generation: str
    ) -> list[KnowledgeNode]:
        old = {item.node_id: item for item in previous.nodes} if previous else {}
        return [
            item.model_copy(
                update={
                    "first_observed_generation": old[item.node_id].first_observed_generation
                    if item.node_id in old
                    else generation,
                    "last_observed_generation": generation,
                }
            )
            for item in nodes
        ]

    @staticmethod
    def _observe_edges(
        edges: list[KnowledgeEdge], previous: KnowledgeGraph | None, generation: str
    ) -> list[KnowledgeEdge]:
        old = {item.edge_id: item for item in previous.edges} if previous else {}
        return [
            item.model_copy(
                update={
                    "first_observed_generation": old[item.edge_id].first_observed_generation
                    if item.edge_id in old
                    else generation,
                    "last_observed_generation": generation,
                }
            )
            for item in edges
        ]

    @staticmethod
    def _orphans(nodes: list[KnowledgeNode], edges: list[KnowledgeEdge]) -> KnowledgeOrphans:
        degree = Counter(edge.source_node_id for edge in edges) + Counter(
            edge.target_node_id for edge in edges
        )
        component_types = {
            KnowledgeNodeType.APPLICATION,
            KnowledgeNodeType.SERVICE,
            KnowledgeNodeType.LIBRARY,
        }
        component_ids = {node.node_id for node in nodes if node.node_type in component_types}
        assigned_files = {
            edge.source_node_id for edge in edges if edge.edge_type.value == "BELONGS_TO"
        }
        file_types = {
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
        files = [node for node in nodes if node.node_type in file_types]
        owned_manifests = {
            edge.target_node_id
            for edge in edges
            if edge.edge_type.value == "HAS_MANIFEST" and edge.source_node_id in component_ids
        }
        components_with_manifests = {
            edge.source_node_id
            for edge in edges
            if edge.edge_type.value == "HAS_MANIFEST" and edge.source_node_id in component_ids
        }
        return KnowledgeOrphans(
            orphan_node_ids=sorted(node.node_id for node in nodes if degree[node.node_id] == 0),
            unassigned_file_ids=sorted(
                node.node_id for node in files if node.node_id not in assigned_files
            ),
            unknown_role_file_ids=sorted(
                node.node_id for node in files if node.metadata.get("engineering_role") == "unknown"
            ),
            unowned_manifest_ids=sorted(
                node.node_id
                for node in files
                if node.node_type is KnowledgeNodeType.MANIFEST
                and node.node_id not in owned_manifests
            ),
            components_without_manifest_ids=sorted(component_ids - components_with_manifests),
        )

    @staticmethod
    def _statistics(
        nodes: list[KnowledgeNode],
        edges: list[KnowledgeEdge],
        changes: Any,
        orphans: KnowledgeOrphans,
    ) -> KnowledgeGraphStatistics:
        return KnowledgeGraphStatistics(
            node_count=len(nodes),
            edge_count=len(edges),
            nodes_by_type=dict(sorted(Counter(node.node_type.value for node in nodes).items())),
            edges_by_type=dict(sorted(Counter(edge.edge_type.value for edge in edges).items())),
            orphan_node_count=len(orphans.orphan_node_ids),
            unassigned_file_count=len(orphans.unassigned_file_ids),
            added_node_count=len(changes.added_nodes),
            modified_node_count=len(changes.modified_nodes),
            removed_node_count=len(changes.removed_nodes),
            unchanged_node_count=len(changes.unchanged_nodes),
            added_edge_count=len(changes.added_edges),
            modified_edge_count=len(changes.modified_edges),
            removed_edge_count=len(changes.removed_edges),
            unchanged_edge_count=len(changes.unchanged_edges),
        )

    def _write_reports(self, result: KnowledgeGraphResult) -> None:
        self.reports_path.mkdir(parents=True, exist_ok=True)
        staged: list[tuple[Path, Path]] = []
        try:
            for filename, content in self.renderer.render(result).items():
                destination = (self.reports_path / filename).resolve()
                if self.reports_path not in destination.parents:
                    raise KnowledgeGraphReportError(
                        "Graph report path escapes configured directory"
                    )
                temporary = destination.with_suffix(f"{destination.suffix}.tmp")
                temporary.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
                staged.append((temporary, destination))
            for temporary, destination in staged:
                temporary.replace(destination)
        except OSError as exc:
            for temporary, _ in staged:
                temporary.unlink(missing_ok=True)
            raise KnowledgeGraphReportError(f"Unable to write graph reports: {exc}") from exc
