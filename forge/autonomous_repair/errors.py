"""Typed errors for M3.5 Autonomous Repair."""


class AutonomousRepairError(RuntimeError):
    """Base error for autonomous repair."""


class RepairInputValidationError(AutonomousRepairError):
    """Raised when repair input is invalid."""


class RepairProviderNotFoundError(AutonomousRepairError):
    """Raised when a requested provider is unavailable."""


class RepairProviderConflictError(AutonomousRepairError):
    """Raised when duplicate provider registrations conflict."""


class RepairProposalError(AutonomousRepairError):
    """Raised when a bounded proposal cannot be generated."""


class RepairPolicyViolationError(AutonomousRepairError):
    """Raised when a repair violates policy."""


class RepairApprovalRequiredError(AutonomousRepairError):
    """Raised when apply mode lacks explicit approval."""


class RepairRepositoryStateError(AutonomousRepairError):
    """Raised when repository state changed unexpectedly."""


class RepairAttemptLimitError(AutonomousRepairError):
    """Raised when maximum repair attempts are exhausted."""


class RepairExecutionError(AutonomousRepairError):
    """Raised when repair execution fails."""


class RepairValidationError(AutonomousRepairError):
    """Raised when post-repair validation fails."""


class RepairRollbackError(AutonomousRepairError):
    """Raised when rollback cannot restore prior state."""


class RepairPersistenceError(AutonomousRepairError):
    """Raised when session evidence cannot be persisted."""