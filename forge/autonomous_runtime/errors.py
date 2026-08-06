"""Typed errors for the Aerion Forge autonomous runtime."""

from __future__ import annotations


class AutonomousRuntimeError(RuntimeError):
    """Base error for autonomous-runtime failures."""


class MissionContractError(AutonomousRuntimeError):
    """Raised when a mission contract is invalid."""


class MissionIdentifierError(AutonomousRuntimeError):
    """Raised when a deterministic identifier cannot be created."""


class MissionPolicyError(AutonomousRuntimeError):
    """Raised when an execution or authority policy is invalid."""


class MissionStateError(AutonomousRuntimeError):
    """Raised when a mission state value or invariant is invalid."""