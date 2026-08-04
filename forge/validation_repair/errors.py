"""Typed errors for validation and repair orchestration."""


class ValidationRepairError(RuntimeError):
    """Base error for validation and repair."""


class InvalidValidationCommandError(ValidationRepairError):
    """Raised when a validation command is not permitted."""


class ValidationExecutionError(ValidationRepairError):
    """Raised when validation execution fails unexpectedly."""


class ValidationTimeoutError(ValidationRepairError):
    """Raised when a validation command exceeds its timeout."""


class ValidationOutputParseError(ValidationRepairError):
    """Raised when validation output cannot be interpreted."""


class RepairPlanningError(ValidationRepairError):
    """Raised when a bounded repair candidate cannot be planned."""


class RepairApprovalRequiredError(ValidationRepairError):
    """Raised when repair application lacks explicit approval."""


class RepairAttemptLimitError(ValidationRepairError):
    """Raised when the configured attempt limit is exhausted."""


class RepairStateChangedError(ValidationRepairError):
    """Raised when repository state changes unexpectedly."""


class RepairExecutionError(ValidationRepairError):
    """Raised when a repair cannot be executed safely."""


class RepairRollbackError(ValidationRepairError):
    """Raised when rollback cannot restore the prior state."""