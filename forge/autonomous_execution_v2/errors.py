"""Errors for M5.7 autonomous execution."""

from __future__ import annotations


class AutonomousExecutionV2Error(Exception):
    """Base M5.7 execution error."""


class ExecutionContractError(AutonomousExecutionV2Error):
    """Raised when an execution contract is invalid."""


class ExecutionStateError(AutonomousExecutionV2Error):
    """Raised for an invalid execution transition."""


class ExecutionPolicyError(AutonomousExecutionV2Error):
    """Raised when execution violates policy."""


class ExecutionAuthorityError(AutonomousExecutionV2Error):
    """Raised when execution authority is insufficient."""