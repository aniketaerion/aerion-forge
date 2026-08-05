"""Typed errors for M3.6 Engineering Mission Orchestration."""


class MissionOrchestrationError(RuntimeError):
    """Base error for mission orchestration."""


class MissionValidationError(MissionOrchestrationError):
    """Raised when a mission request or state is invalid."""


class MissionPolicyViolationError(MissionOrchestrationError):
    """Raised when orchestration violates policy."""


class MissionStateTransitionError(MissionOrchestrationError):
    """Raised when a mission state transition is invalid."""


class MissionStageNotFoundError(MissionOrchestrationError):
    """Raised when a workflow stage cannot be resolved."""


class MissionStageConflictError(MissionOrchestrationError):
    """Raised when duplicate stage registration conflicts."""


class MissionDependencyError(MissionOrchestrationError):
    """Raised when stage dependencies are invalid or incomplete."""


class MissionCheckpointError(MissionOrchestrationError):
    """Raised when checkpoint persistence fails."""


class MissionRecoveryError(MissionOrchestrationError):
    """Raised when a paused or failed mission cannot recover."""


class MissionCancellationError(MissionOrchestrationError):
    """Raised when cancellation cannot be completed safely."""


class MissionExecutionError(MissionOrchestrationError):
    """Raised when stage or mission execution fails."""


class MissionReportError(MissionOrchestrationError):
    """Raised when orchestration evidence cannot be rendered or persisted."""