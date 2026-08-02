"""Engineering Memory domain errors."""


class EngineeringMemoryError(Exception):
    """Base Engineering Memory failure."""


class EngineeringMemoryDisabledError(EngineeringMemoryError):
    """Engineering Memory is disabled by configuration."""


class EngineeringMemoryValidationError(EngineeringMemoryError):
    """Engineering Memory data violates the frozen contract."""


class EngineeringMemoryPersistenceError(EngineeringMemoryError):
    """Engineering Memory persistence failed."""


class EngineeringMemoryStoreCorruptionError(EngineeringMemoryPersistenceError):
    """Persisted Engineering Memory cannot be trusted or decoded."""


class EngineeringMemorySchemaMismatchError(EngineeringMemoryPersistenceError):
    """Persisted Engineering Memory uses an unsupported schema."""


class EngineeringMemoryNotFoundError(EngineeringMemoryError):
    """The requested memory record does not exist."""


class EngineeringMemoryReportError(EngineeringMemoryError):
    """Engineering Memory report generation or writing failed."""
