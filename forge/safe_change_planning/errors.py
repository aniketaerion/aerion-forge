"""Safe Change Planning domain errors."""


class SafeChangePlanningError(Exception):
    """Base error for Safe Change Planning failures."""


class ChangePlanningConfigurationError(SafeChangePlanningError):
    """Raised when planner configuration is invalid."""


class ChangePlanningValidationError(SafeChangePlanningError):
    """Raised when planning inputs or lineage are invalid."""


class ChangePlanningRiskError(SafeChangePlanningError):
    """Raised when mandatory risk controls are missing."""


class ChangePlanNotFoundError(SafeChangePlanningError):
    """Raised when a persisted change plan cannot be found."""


class ChangePlanningPersistenceError(SafeChangePlanningError):
    """Raised when planning state cannot be persisted safely."""


class ChangePlanningReportError(SafeChangePlanningError):
    """Raised when planning reports cannot be rendered or written."""
