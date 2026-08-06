"""Typed errors for autonomous mission orchestration."""

from __future__ import annotations


class AutonomousOrchestrationError(RuntimeError):
    """Base error for orchestration failures."""


class OrchestrationContractError(AutonomousOrchestrationError):
    """Raised when an orchestration contract is invalid."""


class OrchestrationIdentifierError(AutonomousOrchestrationError):
    """Raised when an orchestration identifier cannot be created."""


class OrchestrationPolicyError(AutonomousOrchestrationError):
    """Raised when orchestration policy is unsafe or inconsistent."""


class OrchestrationStateError(AutonomousOrchestrationError):
    """Raised when an orchestration state transition is invalid."""


class OrchestrationResumeError(AutonomousOrchestrationError):
    """Raised when an orchestration session cannot resume."""