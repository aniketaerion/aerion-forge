"""Errors for the M5.8 Forge Mission Runtime."""

from __future__ import annotations


class MissionRuntimeError(Exception):
    """Base error for mission runtime failures."""


class MissionContractError(MissionRuntimeError):
    """Raised when a mission contract is invalid."""


class MissionStateError(MissionRuntimeError):
    """Raised when a mission state transition is invalid."""


class MissionPolicyError(MissionRuntimeError):
    """Raised when mission policy prevents an operation."""


class MissionScopeError(MissionRuntimeError):
    """Raised when mission scope and repository scope do not match."""


class MissionCapabilityError(MissionRuntimeError):
    """Raised when required capabilities are unavailable."""


class MissionApprovalError(MissionRuntimeError):
    """Raised when required approval is missing or invalid."""