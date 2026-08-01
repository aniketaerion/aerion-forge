"""Explicit incremental-index failure types."""


class IndexingError(Exception):
    """Base class for indexing failures."""


class IndexTargetNotFoundError(IndexingError):
    """Raised when the target repository cannot be resolved."""


class IndexPermissionError(IndexingError):
    """Raised when repository content cannot be accessed."""


class IndexLimitExceededError(IndexingError):
    """Raised when configured indexing safety limits are exceeded."""


class IndexPersistenceError(IndexingError):
    """Raised when durable index state cannot be loaded or saved."""


class IndexReportError(IndexingError):
    """Raised when deterministic index reports cannot be written."""


class IndexCorruptionError(IndexPersistenceError):
    """Raised when persisted index data is corrupt or incompatible."""
