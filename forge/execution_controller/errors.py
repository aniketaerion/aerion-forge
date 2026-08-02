"""Execution Controller domain errors."""


class ExecutionControllerError(Exception):
    """Base error for Execution Controller failures."""


class ExecutionConfigurationError(ExecutionControllerError):
    """Raised when Execution Controller configuration is invalid."""


class ExecutionValidationError(ExecutionControllerError):
    """Raised when execution inputs or lineage are invalid."""


class ExecutionRequestNotFoundError(ExecutionControllerError):
    """Raised when an execution request cannot be found."""


class ExecutionSessionNotFoundError(ExecutionControllerError):
    """Raised when an execution session cannot be found."""


class ExecutionApprovalRequiredError(ExecutionControllerError):
    """Raised when explicit approval is required."""


class ExecutionApprovalRejectedError(ExecutionControllerError):
    """Raised when an execution request has been rejected."""


class ExecutionApprovalMismatchError(ExecutionControllerError):
    """Raised when approval does not match the execution request."""


class ExecutionStateTransitionError(ExecutionControllerError):
    """Raised when an execution state transition is illegal."""


class ExecutionToolNotRegisteredError(ExecutionControllerError):
    """Raised when an operation references an unregistered tool."""


class ExecutionOperationNotApprovedError(ExecutionControllerError):
    """Raised when an operation is outside approved scope."""


class ExecutionDispatchError(ExecutionControllerError):
    """Raised when dispatching a registered operation fails."""


class ExecutionPersistenceError(ExecutionControllerError):
    """Raised when execution state cannot be persisted safely."""


class ExecutionReportError(ExecutionControllerError):
    """Raised when execution reports cannot be rendered or written."""


class ExecutionCancellationError(ExecutionControllerError):
    """Raised when cancellation cannot be completed safely."""
