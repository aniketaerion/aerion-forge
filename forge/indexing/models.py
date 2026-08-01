"""Schema-versioned incremental project index models."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

INDEX_SCHEMA_VERSION = "1.0"


class FileCategory(StrEnum):
    SOURCE = "source"
    TEST = "test"
    CONFIGURATION = "configuration"
    MANIFEST = "manifest"
    LOCKFILE = "lockfile"
    MIGRATION = "migration"
    SCHEMA = "schema"
    DOCUMENTATION = "documentation"
    BUILD = "build"
    CI_CD = "ci_cd"
    CONTAINER = "container"
    KUBERNETES = "kubernetes"
    INFRASTRUCTURE = "infrastructure"
    SCRIPT = "script"
    ASSET = "asset"
    LOCALIZATION = "localization"
    GENERATED = "generated"
    UNKNOWN = "unknown"


class EngineeringRole(StrEnum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    API = "api"
    DOMAIN = "domain"
    SERVICE = "service"
    CONTROLLER = "controller"
    MODEL = "model"
    REPOSITORY = "repository"
    UI = "ui"
    STATE_MANAGEMENT = "state_management"
    TEST = "test"
    BUILD = "build"
    DEPLOYMENT = "deployment"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    MOBILE = "mobile"
    EMBEDDED = "embedded"
    ROBOTICS = "robotics"
    FIRMWARE = "firmware"
    CONFIGURATION = "configuration"
    SHARED_LIBRARY = "shared_library"
    UNKNOWN = "unknown"


class FingerprintStrategy(StrEnum):
    FULL = "full_content"
    SAMPLED = "bounded_sample"
    PROTECTED = "protected_content"
    PROTECTED_SAMPLED = "protected_bounded_sample"
    NONE = "none"


class IndexStatus(StrEnum):
    INDEXED = "indexed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    RENAMED = "renamed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FileFingerprint(BaseModel):
    value: str | None = None
    strategy: FingerprintStrategy
    algorithm: str = "sha256"


class IndexedFile(BaseModel):
    path: str
    normalized_path: str
    file_name: str
    extension: str
    category: FileCategory
    engineering_role: EngineeringRole
    repository_area: str | None = None
    size_bytes: int = Field(ge=0)
    fingerprint: FileFingerprint
    metadata_fingerprint: str
    index_status: IndexStatus
    binary: bool
    generated: bool
    ignored: bool
    manifest: bool
    test: bool
    configuration: bool
    documentation: bool
    migration: bool
    infrastructure: bool
    sensitive: bool
    last_observed_generation: str = "pending"
    error: str | None = None


class IndexChange(BaseModel):
    change_type: ChangeType
    path: str
    previous_path: str | None = None
    fingerprint: str | None = None


class IndexChangeSet(BaseModel):
    added: list[IndexChange] = Field(default_factory=list)
    modified: list[IndexChange] = Field(default_factory=list)
    removed: list[IndexChange] = Field(default_factory=list)
    unchanged: list[IndexChange] = Field(default_factory=list)
    renamed: list[IndexChange] = Field(default_factory=list)
    failed: list[IndexChange] = Field(default_factory=list)
    skipped: list[IndexChange] = Field(default_factory=list)


class IndexStatistics(BaseModel):
    total_indexed_files: int = Field(ge=0)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_extension: dict[str, int] = Field(default_factory=dict)
    by_engineering_role: dict[str, int] = Field(default_factory=dict)
    added_count: int = Field(ge=0)
    modified_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    renamed_count: int = Field(ge=0)
    unchanged_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)


class IndexGeneration(BaseModel):
    repository_identity: str
    repository_name: str
    workspace_id: str | None = None
    schema_version: str = INDEX_SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    repository_state_fingerprint: str
    statistics: IndexStatistics


class ProjectIndex(BaseModel):
    schema_version: str = INDEX_SCHEMA_VERSION
    generation: IndexGeneration
    files: list[IndexedFile] = Field(default_factory=list)


class IndexResult(BaseModel):
    project_index: ProjectIndex
    changes: IndexChangeSet


class IndexConfiguration(BaseModel):
    max_hash_bytes: int = Field(ge=1024)
    hash_chunk_bytes: int = Field(ge=1024)
    max_files: int = Field(ge=1)


class IndexStore(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    repositories: dict[str, ProjectIndex] = Field(default_factory=dict)
