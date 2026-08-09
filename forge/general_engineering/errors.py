"""Errors for the M5.9 General Engineering Agent."""

from __future__ import annotations


class GeneralEngineeringError(Exception):
    """Base error for general engineering failures."""


class EngineeringContractError(GeneralEngineeringError):
    """Raised when a general engineering contract is invalid."""


class EngineeringPolicyError(GeneralEngineeringError):
    """Raised when policy blocks an engineering action."""


class EngineeringScopeError(GeneralEngineeringError):
    """Raised when requested or proposed scope is invalid."""


class EngineeringEvidenceError(GeneralEngineeringError):
    """Raised when required repository evidence is missing or invalid."""


class EngineeringProviderError(GeneralEngineeringError):
    """Raised when a provider returns invalid or unusable proposal data."""


class EngineeringRepairError(GeneralEngineeringError):
    """Raised when bounded repair cannot proceed safely."""