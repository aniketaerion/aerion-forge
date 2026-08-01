"""Deterministic structural knowledge graph construction."""

from pathlib import PurePosixPath

from forge.discovery.models import DiscoveryResult
from forge.indexing.models import FileCategory, IndexStatus, ProjectIndex
from forge.knowledge.errors import KnowledgeGraphLimitExceededError
from forge.knowledge.identifiers import edge_id, node_id, normalize_path
from forge.knowledge.models import (
    Confidence,
    EvidenceOrigin,
    KnowledgeEdge,
    KnowledgeEdgeType,
    KnowledgeGraphConfiguration,
    KnowledgeNode,
    KnowledgeNodeType,
)
from forge.knowledge.resolver import ComponentBoundary, StructuralResolver


class KnowledgeGraphBuilder:
    """Convert existing discovery and index data into a truthful structural graph."""

    def __init__(self, configuration: KnowledgeGraphConfiguration) -> None:
        self.configuration = configuration
        self.resolver = StructuralResolver(configuration.max_module_depth)
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: dict[str, KnowledgeEdge] = {}

    def build(
        self,
        discovery: DiscoveryResult,
        project_index: ProjectIndex,
        workspace_id: str | None,
        workspace_name: str | None,
    ) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
        """Build deduplicated nodes and edges using no filesystem access."""
        identity = project_index.generation.repository_identity
        repository = self._node(
            KnowledgeNodeType.REPOSITORY,
            identity,
            discovery.repository_name,
            None,
            identity,
            workspace_id,
            EvidenceOrigin.DISCOVERY,
            {"project_type": discovery.project_type},
        )
        if workspace_id:
            workspace = self._node(
                KnowledgeNodeType.WORKSPACE,
                workspace_id,
                workspace_name or workspace_id,
                None,
                identity,
                workspace_id,
                EvidenceOrigin.WORKSPACE,
            )
            self._edge(
                workspace,
                repository,
                KnowledgeEdgeType.CONTAINS,
                EvidenceOrigin.WORKSPACE,
                Confidence.EXPLICIT,
                ["registered workspace"],
            )

        components = self.resolver.components(discovery)
        component_nodes: dict[str, KnowledgeNode] = {}
        for component in components:
            component_node = self._component(identity, workspace_id, component)
            component_nodes[component.path] = component_node
            relation = {
                KnowledgeNodeType.SERVICE: KnowledgeEdgeType.HAS_SERVICE,
                KnowledgeNodeType.LIBRARY: KnowledgeEdgeType.HAS_LIBRARY,
            }.get(component.node_type, KnowledgeEdgeType.HAS_APPLICATION)
            self._edge(
                repository,
                component_node,
                relation,
                EvidenceOrigin.DISCOVERY,
                Confidence.STRONG,
                [component.path],
            )

        directory_nodes: dict[str, KnowledgeNode] = {}
        module_nodes: dict[str, KnowledgeNode] = {}
        path_nodes: dict[str, KnowledgeNode] = {}
        for indexed in project_index.files:
            if indexed.index_status is not IndexStatus.INDEXED or indexed.ignored:
                continue
            placement = self.resolver.place(indexed, components)
            if self.configuration.include_directory_nodes:
                parent = repository
                for directory in placement.directory_paths:
                    directory_node = directory_nodes.get(directory) or self._node(
                        KnowledgeNodeType.DIRECTORY,
                        identity,
                        PurePosixPath(directory).name,
                        directory,
                        identity,
                        workspace_id,
                        EvidenceOrigin.INDEX,
                    )
                    directory_nodes[directory] = directory_node
                    self._edge(
                        parent,
                        directory_node,
                        KnowledgeEdgeType.HAS_DIRECTORY,
                        EvidenceOrigin.DERIVED,
                        Confidence.STRONG,
                        [directory],
                    )
                    parent = directory_node
            file_type = self._file_node_type(indexed.category)
            file_node = self._node(
                file_type,
                identity,
                indexed.file_name,
                indexed.path,
                identity,
                workspace_id,
                EvidenceOrigin.INDEX,
                {
                    "category": indexed.category.value,
                    "engineering_role": indexed.engineering_role.value,
                    "binary": indexed.binary,
                    "sensitive": indexed.sensitive,
                    "fingerprint_strategy": indexed.fingerprint.strategy.value,
                },
            )
            path_nodes[normalize_path(indexed.path)] = file_node
            self._edge(
                repository,
                file_node,
                self._file_relation(file_type),
                EvidenceOrigin.INDEX,
                Confidence.EXPLICIT,
                [indexed.path],
            )
            if placement.directory_paths and self.configuration.include_directory_nodes:
                self._edge(
                    directory_nodes[placement.directory_paths[-1]],
                    file_node,
                    KnowledgeEdgeType.CONTAINS,
                    EvidenceOrigin.DERIVED,
                    Confidence.STRONG,
                    [indexed.path],
                )
            if placement.component_path:
                component_node = component_nodes[placement.component_path]
                self._edge(
                    component_node,
                    file_node,
                    KnowledgeEdgeType.HAS_FILE,
                    EvidenceOrigin.PATH_RULE,
                    Confidence.MODERATE,
                    [placement.component_path],
                )
                self._edge(
                    file_node,
                    component_node,
                    KnowledgeEdgeType.BELONGS_TO,
                    EvidenceOrigin.PATH_RULE,
                    Confidence.MODERATE,
                    [placement.component_path],
                )
            if placement.module_path:
                module_node = module_nodes.get(placement.module_path) or self._node(
                    KnowledgeNodeType.MODULE,
                    identity,
                    PurePosixPath(placement.module_path).name,
                    placement.module_path,
                    identity,
                    workspace_id,
                    EvidenceOrigin.PATH_RULE,
                )
                module_nodes[placement.module_path] = module_node
                owner = component_nodes.get(placement.component_path or "", repository)
                self._edge(
                    owner,
                    module_node,
                    KnowledgeEdgeType.HAS_MODULE,
                    EvidenceOrigin.PATH_RULE,
                    Confidence.MODERATE,
                    [placement.module_path],
                )
                self._edge(
                    module_node,
                    file_node,
                    KnowledgeEdgeType.HAS_FILE,
                    EvidenceOrigin.PATH_RULE,
                    Confidence.MODERATE,
                    [placement.module_path],
                )

        self._technology_nodes(repository, component_nodes, discovery, identity, workspace_id)
        self._dependency_nodes(
            repository, component_nodes, path_nodes, discovery, identity, workspace_id
        )
        self._check_limits()
        return sorted(self.nodes.values(), key=lambda item: item.node_id), sorted(
            self.edges.values(), key=lambda item: item.edge_id
        )

    def _component(
        self, identity: str, workspace_id: str | None, component: ComponentBoundary
    ) -> KnowledgeNode:
        return self._node(
            component.node_type,
            identity,
            component.name,
            component.path,
            identity,
            workspace_id,
            EvidenceOrigin.DISCOVERY,
            {"boundary": component.path},
        )

    def _technology_nodes(
        self,
        repository: KnowledgeNode,
        components: dict[str, KnowledgeNode],
        discovery: DiscoveryResult,
        identity: str,
        workspace_id: str | None,
    ) -> None:
        groups = (
            (discovery.languages, KnowledgeNodeType.LANGUAGE, KnowledgeEdgeType.USES_LANGUAGE),
            (discovery.frameworks, KnowledgeNodeType.FRAMEWORK, KnowledgeEdgeType.USES_FRAMEWORK),
            (
                discovery.package_managers,
                KnowledgeNodeType.PACKAGE_MANAGER,
                KnowledgeEdgeType.USES_PACKAGE_MANAGER,
            ),
            (
                discovery.build_systems,
                KnowledgeNodeType.BUILD_SYSTEM,
                KnowledgeEdgeType.USES_BUILD_SYSTEM,
            ),
            (
                discovery.test_frameworks,
                KnowledgeNodeType.TEST_FRAMEWORK,
                KnowledgeEdgeType.USES_TEST_FRAMEWORK,
            ),
            (discovery.databases, KnowledgeNodeType.DATABASE, KnowledgeEdgeType.USES_DATABASE),
        )
        for values, node_type, relation in groups:
            iterable = values.keys() if isinstance(values, dict) else values
            for value in sorted(iterable):
                technology = self._node(
                    node_type,
                    identity,
                    value,
                    None,
                    identity,
                    workspace_id,
                    EvidenceOrigin.DISCOVERY,
                )
                self._edge(
                    repository,
                    technology,
                    relation,
                    EvidenceOrigin.DISCOVERY,
                    Confidence.STRONG,
                    [value],
                )
                if node_type is KnowledgeNodeType.DATABASE:
                    for component in components.values():
                        if component.node_type is KnowledgeNodeType.SERVICE:
                            self._edge(
                                component,
                                technology,
                                relation,
                                EvidenceOrigin.DISCOVERY,
                                Confidence.MODERATE,
                                [value],
                            )
                if node_type is KnowledgeNodeType.DATABASE:
                    for component in components.values():
                        if component.node_type is KnowledgeNodeType.SERVICE:
                            self._edge(
                                component,
                                technology,
                                relation,
                                EvidenceOrigin.DISCOVERY,
                                Confidence.MODERATE,
                                [value],
                            )
                if node_type is KnowledgeNodeType.FRAMEWORK:
                    for component in components.values():
                        self._edge(
                            component,
                            technology,
                            relation,
                            EvidenceOrigin.DISCOVERY,
                            Confidence.MODERATE,
                            [value],
                        )

    def _dependency_nodes(
        self,
        repository: KnowledgeNode,
        components: dict[str, KnowledgeNode],
        path_nodes: dict[str, KnowledgeNode],
        discovery: DiscoveryResult,
        identity: str,
        workspace_id: str | None,
    ) -> None:
        for dependency in discovery.dependencies:
            manifest = path_nodes.get(normalize_path(dependency.source))
            if manifest is None:
                continue
            dependency_key = f"{dependency.name}@{normalize_path(dependency.source)}"
            dependency_node = self._node(
                KnowledgeNodeType.DEPENDENCY,
                identity,
                dependency_key,
                None,
                identity,
                workspace_id,
                EvidenceOrigin.MANIFEST,
                {
                    "version": dependency.version,
                    "scope": dependency.scope,
                    "source_manifest": normalize_path(dependency.source),
                    "dependency_name": dependency.name,
                },
            )
            self._edge(
                manifest,
                dependency_node,
                KnowledgeEdgeType.DECLARES_DEPENDENCY,
                EvidenceOrigin.MANIFEST,
                Confidence.EXPLICIT,
                [dependency.source],
            )
            owner = (
                self._owner_for_path(normalize_path(dependency.source), components) or repository
            )
            self._edge(
                owner,
                manifest,
                KnowledgeEdgeType.HAS_MANIFEST,
                EvidenceOrigin.MANIFEST,
                Confidence.STRONG,
                [dependency.source],
            )

    @staticmethod
    def _owner_for_path(path: str, components: dict[str, KnowledgeNode]) -> KnowledgeNode | None:
        matches = [
            node
            for boundary, node in components.items()
            if boundary != "." and path.startswith(f"{boundary}/")
        ]
        return max(matches, key=lambda item: len(item.path or "")) if matches else None

    def _node(
        self,
        node_type: KnowledgeNodeType,
        canonical_identity: str,
        display: str,
        path: str | None,
        repository_identity: str,
        workspace_id: str | None,
        origin: EvidenceOrigin,
        metadata: dict[str, str | int | bool | list[str] | None] | None = None,
    ) -> KnowledgeNode:
        normalized = normalize_path(path) if path else None
        identifier = node_id(node_type, canonical_identity, normalized or display)
        node = KnowledgeNode(
            node_id=identifier,
            node_type=node_type,
            canonical_name=normalized or display.casefold(),
            display_name=display,
            path=normalized,
            repository_identity=repository_identity,
            workspace_id=workspace_id,
            source_origin=origin,
            metadata=metadata or {},
        )
        existing = self.nodes.get(identifier)
        if existing and existing.model_dump(
            exclude={"first_observed_generation", "last_observed_generation"}
        ) != node.model_dump(exclude={"first_observed_generation", "last_observed_generation"}):
            raise ValueError(f"Conflicting canonical node: {identifier}")
        self.nodes[identifier] = existing or node
        return self.nodes[identifier]

    def _edge(
        self,
        source: KnowledgeNode,
        target: KnowledgeNode,
        edge_type: KnowledgeEdgeType,
        origin: EvidenceOrigin,
        confidence: Confidence,
        evidence: list[str],
    ) -> None:
        identifier = edge_id(source.node_id, edge_type, target.node_id)
        self.edges.setdefault(
            identifier,
            KnowledgeEdge(
                edge_id=identifier,
                source_node_id=source.node_id,
                target_node_id=target.node_id,
                edge_type=edge_type,
                source_origin=origin,
                confidence=confidence,
                evidence=sorted(set(evidence)),
            ),
        )

    @staticmethod
    def _file_node_type(category: FileCategory) -> KnowledgeNodeType:
        return {
            FileCategory.MANIFEST: KnowledgeNodeType.MANIFEST,
            FileCategory.CONFIGURATION: KnowledgeNodeType.CONFIGURATION,
            FileCategory.DOCUMENTATION: KnowledgeNodeType.DOCUMENTATION,
            FileCategory.CONTAINER: KnowledgeNodeType.CONTAINER,
            FileCategory.KUBERNETES: KnowledgeNodeType.KUBERNETES,
            FileCategory.CI_CD: KnowledgeNodeType.CI_PIPELINE,
            FileCategory.INFRASTRUCTURE: KnowledgeNodeType.INFRASTRUCTURE,
            FileCategory.MIGRATION: KnowledgeNodeType.MIGRATION_AREA,
            FileCategory.SCHEMA: KnowledgeNodeType.SCHEMA_AREA,
        }.get(category, KnowledgeNodeType.FILE)

    @staticmethod
    def _file_relation(node_type: KnowledgeNodeType) -> KnowledgeEdgeType:
        return {
            KnowledgeNodeType.MANIFEST: KnowledgeEdgeType.HAS_MANIFEST,
            KnowledgeNodeType.CONFIGURATION: KnowledgeEdgeType.HAS_CONFIGURATION,
            KnowledgeNodeType.DOCUMENTATION: KnowledgeEdgeType.HAS_DOCUMENTATION,
            KnowledgeNodeType.CONTAINER: KnowledgeEdgeType.HAS_CONTAINER_CONFIGURATION,
            KnowledgeNodeType.KUBERNETES: KnowledgeEdgeType.HAS_KUBERNETES_CONFIGURATION,
            KnowledgeNodeType.CI_PIPELINE: KnowledgeEdgeType.HAS_CI_PIPELINE,
            KnowledgeNodeType.INFRASTRUCTURE: KnowledgeEdgeType.HAS_INFRASTRUCTURE,
            KnowledgeNodeType.MIGRATION_AREA: KnowledgeEdgeType.HAS_MIGRATION_AREA,
            KnowledgeNodeType.SCHEMA_AREA: KnowledgeEdgeType.HAS_SCHEMA_AREA,
        }.get(node_type, KnowledgeEdgeType.HAS_FILE)

    def _check_limits(self) -> None:
        if len(self.nodes) > self.configuration.max_nodes:
            raise KnowledgeGraphLimitExceededError(
                f"Graph exceeds node limit of {self.configuration.max_nodes}"
            )
        if len(self.edges) > self.configuration.max_edges:
            raise KnowledgeGraphLimitExceededError(
                f"Graph exceeds edge limit of {self.configuration.max_edges}"
            )
