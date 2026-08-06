"""Typed errors for the autonomous decision engine."""

from __future__ import annotations


class AutonomousDecisionError(RuntimeError):
    """Base error for autonomous decision failures."""


class DecisionContractError(AutonomousDecisionError):
    """Raised when a decision contract is invalid."""


class DecisionIdentifierError(AutonomousDecisionError):
    """Raised when a deterministic identifier cannot be created."""


class DecisionPolicyError(AutonomousDecisionError):
    """Raised when decision policy is unsafe or inconsistent."""


class CandidateRejectedError(AutonomousDecisionError):
    """Raised when a candidate violates a hard decision constraint."""


class DecisionReplayError(AutonomousDecisionError):
    """Raised when a conflicting decision replay is detected."""