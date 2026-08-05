"""Typed errors for M3.8 Unified Agent Runtime."""

from __future__ import annotations


class AgentRuntimeError(Exception):
    """Base error for the unified agent runtime."""


class AgentRuntimeConfigurationError(AgentRuntimeError):
    """Raised when runtime configuration is invalid."""


class AgentRuntimePolicyError(AgentRuntimeError):
    """Raised when an agent request violates policy."""


class AgentRuntimeValidationError(AgentRuntimeError):
    """Raised when runtime state or evidence is invalid."""


class AgentRuntimeCapabilityError(AgentRuntimeError):
    """Raised when a required Forge capability is unavailable."""


class AgentRuntimeStateError(AgentRuntimeError):
    """Raised when an invalid lifecycle transition is requested."""


class AgentRuntimeApprovalError(AgentRuntimeError):
    """Raised when required human approval is missing or invalid."""


class AgentRuntimePersistenceError(AgentRuntimeError):
    """Raised when agent state cannot be persisted."""


class AgentRuntimeRecoveryError(AgentRuntimeError):
    """Raised when a session cannot be recovered safely."""


class AgentRuntimeExecutionError(AgentRuntimeError):
    """Raised when a runtime stage cannot execute safely."""


class AgentRuntimeReportError(AgentRuntimeError):
    """Raised when runtime evidence cannot be reported."""