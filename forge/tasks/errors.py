"""Controlled exceptions for the Task Management Engine."""


class TaskManagementError(Exception):
    """Base exception for all task-management failures."""


class TaskManagementDisabledError(TaskManagementError):
    """Raised when task management is disabled."""


class TaskDefinitionError(TaskManagementError):
    """Raised when a task definition is invalid."""


class TaskIdentifierError(TaskManagementError):
    """Raised when task identity generation fails."""


class TaskNotFoundError(TaskManagementError):
    """Raised when a requested task does not exist."""


class TaskDependencyError(TaskManagementError):
    """Raised when task dependencies are invalid."""


class TaskDependencyCycleError(TaskDependencyError):
    """Raised when a dependency cycle is detected."""


class TaskParentError(TaskManagementError):
    """Raised when a parent-child task relationship is invalid."""


class TaskLifecycleError(TaskManagementError):
    """Raised when a lifecycle transition is invalid."""


class TaskValidationError(TaskManagementError):
    """Raised when task validation fails."""


class TaskPersistenceError(TaskManagementError):
    """Raised when task persistence fails."""


class TaskStoreCorruptionError(TaskPersistenceError):
    """Raised when persisted task state is corrupt."""


class TaskSchemaMismatchError(TaskPersistenceError):
    """Raised when persisted task state uses an unsupported schema."""


class TaskReportError(TaskManagementError):
    """Raised when task report generation fails."""


class TaskConfigurationError(TaskManagementError):
    """Raised when task-management configuration is invalid."""
