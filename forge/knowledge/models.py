"""Schema-versioned structural engineering knowledge graph models."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

GRAPH_SCHEMA_VERSION = "1.0"
MetadataValue = str | int | bool | list[str] | None


class KnowledgeNodeType(StrEnum):
    WORKSPACE = "workspace"
    REPOSITORY = "repository"
    APPLICATION = "application"
    SERVICE = "service"
    LIBRARY = "library"
    MODULE = "module"
    DIRECTORY = "directory"
    FILE = "file"
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    PACKAGE_MANAGER = "package_manager"
    BUILD_SYSTEM = "build_system"
    TEST_FRAMEWORK = "test_framework"
    DATABASE = "database"
    MANIFEST = "manifest"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    CONTAINER = "container"
    KUBERNETES = "kubernetes"
    CI_PIPELINE = "ci_pipeline"
    INFRASTRUCTURE = "infrastructure"
    MIGRATION_AREA = "migration_area"
    SCHEMA_AREA = "schema_area"
    UNKNOWN = "unknown"


class KnowledgeEdgeType(StrEnum):
    CONTAINS = "CONTAINS"
    BELONGS_TO = "BELONGS_TO"
    HAS_FILE = "HAS_FILE"
    HAS_DIRECTORY = "HAS_DIRECTORY"
    HAS_MODULE = "HAS_MODULE"
    HAS_APPLICATION = "HAS_APPLICATION"
    HAS_SERVICE = "HAS_SERVICE"
    HAS_LIBRARY = "HAS_LIBRARY"
    USES_LANGUAGE = "USES_LANGUAGE"
    USES_FRAMEWORK = "USES_FRAMEWORK"
    USES_PACKAGE_MANAGER = "USES_PACKAGE_MANAGER"
    USES_BUILD_SYSTEM = "USES_BUILD_SYSTEM"
    USES_TEST_FRAMEWORK = "USES_TEST_FRAMEWORK"
    USES_DATABASE = "USES_DATABASE"
    HAS_MANIFEST = "HAS_MANIFEST"
    HAS_CONFIGURATION = "HAS_CONFIGURATION"
    HAS_DOCUMENTATION = "HAS_DOCUMENTATION"
    HAS_CONTAINER_CONFIGURATION = "HAS_CONTAINER_CONFIGURATION"
    HAS_KUBERNETES_CONFIGURATION = "HAS_KUBERNETES_CONFIGURATION"
    HAS_CI_PIPELINE = "HAS_CI_PIPELINE"
    HAS_INFRASTRUCTURE = "HAS_INFRASTRUCTURE"
    HAS_MIGRATION_AREA = "HAS_MIGRATION_AREA"
    HAS_SCHEMA_AREA = "HAS_SCHEMA_AREA"
    DECLARES_DEPENDENCY = "DECLARES_DEPENDENCY"
    RELATED_TO = "RELATED_TO"
    UNKNOWN_RELATION = "UNKNOWN_RELATION"


class EvidenceOrigin(StrEnum):
    WORKSPACE = "workspace"
    DISCOVERY = "discovery"
    INDEX = "index"
    MANIFEST = "manifest"
    PATH_RULE = "path_rule"
    CONFIGURATION = "configuration"
    DERIVED = "derived"


class Confidence(StrEnum):
    EXPLICIT = "explicit"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNKNOWN = "unknown"


class GraphChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"


class KnowledgeNode(BaseModel):
    node_id: str
    node_type: KnowledgeNodeType
    canonical_name: str
    display_name: str
    path: str | None = None
    repository_identity: str
    workspace_id: str | None = None
    source_origin: EvidenceOrigin
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)
    schema_version: str = GRAPH_SCHEMA_VERSION
    first_observed_generation: str = "pending"
    last_observed_generation: str = "pending"


class KnowledgeEdge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: KnowledgeEdgeType
    source_origin: EvidenceOrigin
    confidence: Confidence
    evidence: list[str] = Field(default_factory=list)
    first_observed_generation: str = "pending"
    last_observed_generation: str = "pending"


class KnowledgeGraphStatistics(BaseModel):
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    nodes_by_type: dict[str, int] = Field(default_factory=dict)
    edges_by_type: dict[str, int] = Field(default_factory=dict)
    orphan_node_count: int = Field(ge=0)
    unassigned_file_count: int = Field(ge=0)
    added_node_count: int = Field(ge=0)
    modified_node_count: int = Field(ge=0)
    removed_node_count: int = Field(ge=0)
    unchanged_node_count: int = Field(ge=0)
    added_edge_count: int = Field(ge=0)
    modified_edge_count: int = Field(ge=0)
    removed_edge_count: int = Field(ge=0)
    unchanged_edge_count: int = Field(ge=0)


class KnowledgeGraphGeneration(BaseModel):
    schema_version: str = GRAPH_SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    repository_identity: str
    workspace_id: str | None = None
    source_discovery_fingerprint: str
    source_index_generation_id: str
    source_index_state_fingerprint: str
    graph_state_fingerprint: str
    statistics: KnowledgeGraphStatistics
    validation_status: Literal["valid"] = "valid"


class KnowledgeGraph(BaseModel):
    schema_version: str = GRAPH_SCHEMA_VERSION
    generation: KnowledgeGraphGeneration
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)


class KnowledgeGraphChange(BaseModel):
    change_type: GraphChangeType
    entity_id: str


class KnowledgeGraphChangeSet(BaseModel):
    added_nodes: list[KnowledgeGraphChange] = Field(default_factory=list)
    modified_nodes: list[KnowledgeGraphChange] = Field(default_factory=list)
    removed_nodes: list[KnowledgeGraphChange] = Field(default_factory=list)
    unchanged_nodes: list[KnowledgeGraphChange] = Field(default_factory=list)
    added_edges: list[KnowledgeGraphChange] = Field(default_factory=list)
    modified_edges: list[KnowledgeGraphChange] = Field(default_factory=list)
    removed_edges: list[KnowledgeGraphChange] = Field(default_factory=list)
    unchanged_edges: list[KnowledgeGraphChange] = Field(default_factory=list)


class KnowledgeOrphans(BaseModel):
    orphan_node_ids: list[str] = Field(default_factory=list)
    unassigned_file_ids: list[str] = Field(default_factory=list)
    unknown_role_file_ids: list[str] = Field(default_factory=list)
    unowned_manifest_ids: list[str] = Field(default_factory=list)
    components_without_manifest_ids: list[str] = Field(default_factory=list)


class KnowledgeGraphResult(BaseModel):
    graph: KnowledgeGraph
    changes: KnowledgeGraphChangeSet
    orphans: KnowledgeOrphans


class KnowledgeGraphConfiguration(BaseModel):
    max_nodes: int = Field(ge=1)
    max_edges: int = Field(ge=1)
    max_module_depth: int = Field(ge=1, le=10)
    include_directory_nodes: bool = True


class KnowledgeGraphStore(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    repositories: dict[str, KnowledgeGraph] = Field(default_factory=dict)


class GraphValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
