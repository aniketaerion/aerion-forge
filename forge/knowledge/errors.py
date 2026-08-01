"""Engineering knowledge graph failure types."""


class KnowledgeGraphError(Exception):
    """Base graph error."""


class KnowledgeGraphTargetNotFoundError(KnowledgeGraphError):
    """The requested target could not be resolved."""


class KnowledgeGraphInputMissingError(KnowledgeGraphError):
    """Required discovery or index input is absent."""


class KnowledgeGraphInputMismatchError(KnowledgeGraphError):
    """Persisted inputs do not describe the same repository."""


class KnowledgeGraphLimitExceededError(KnowledgeGraphError):
    """A configured graph-size limit was exceeded."""


class KnowledgeGraphBuildError(KnowledgeGraphError):
    """Graph construction failed before validation."""


class KnowledgeGraphValidationError(KnowledgeGraphError):
    """Graph integrity validation failed."""


class KnowledgeGraphPersistenceError(KnowledgeGraphError):
    """Graph persistence failed."""


class KnowledgeGraphReportError(KnowledgeGraphError):
    """Graph report generation failed."""


class KnowledgeGraphCorruptionError(KnowledgeGraphPersistenceError):
    """Persisted graph state is corrupt or incompatible."""
