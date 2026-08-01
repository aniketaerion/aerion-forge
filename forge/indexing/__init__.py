"""Incremental project index public API."""

from forge.indexing.errors import (
    IndexCorruptionError,
    IndexingError,
    IndexLimitExceededError,
    IndexPermissionError,
    IndexPersistenceError,
    IndexReportError,
    IndexTargetNotFoundError,
)
from forge.indexing.models import (
    ChangeType,
    EngineeringRole,
    FileCategory,
    FileFingerprint,
    FingerprintStrategy,
    IndexChange,
    IndexChangeSet,
    IndexConfiguration,
    IndexedFile,
    IndexGeneration,
    IndexResult,
    IndexStatistics,
    IndexStatus,
    IndexStore,
    ProjectIndex,
)
from forge.indexing.service import IndexingService
from forge.indexing.store import ProjectIndexStore

__all__ = [
    "ChangeType",
    "EngineeringRole",
    "FileCategory",
    "FileFingerprint",
    "FingerprintStrategy",
    "IndexChange",
    "IndexChangeSet",
    "IndexConfiguration",
    "IndexCorruptionError",
    "IndexGeneration",
    "IndexLimitExceededError",
    "IndexPermissionError",
    "IndexPersistenceError",
    "IndexReportError",
    "IndexResult",
    "IndexStatistics",
    "IndexStatus",
    "IndexStore",
    "IndexTargetNotFoundError",
    "IndexedFile",
    "IndexingError",
    "IndexingService",
    "ProjectIndex",
    "ProjectIndexStore",
]
