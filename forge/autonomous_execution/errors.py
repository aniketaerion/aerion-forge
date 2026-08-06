"""Typed errors for the autonomous execution engine."""

from __future__ import annotations


class AutonomousExecutionError(RuntimeError):
    """Base error for autonomous execution failures."""


class ExecutionContractError(AutonomousExecutionError):
    """Raised when an execution contract is invalid."""


class ExecutionIdentifierError(AutonomousExecutionError):
    """Raised when an execution identifier cannot be created."""


class ExecutionPolicyError(AutonomousExecutionError):
    """Raised when an execution policy is invalid."""


class ToolContractError(AutonomousExecutionError):
    """Raised when a tool contract is invalid."""


class ToolResolutionError(AutonomousExecutionError):
    """Raised when a tool cannot be resolved safely."""