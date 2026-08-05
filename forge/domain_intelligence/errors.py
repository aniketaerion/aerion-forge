"""Typed errors for Phase 4 domain intelligence."""

from __future__ import annotations


class DomainIntelligenceError(Exception):
    """Base error for domain-intelligence operations."""


class DomainIntelligenceConfigurationError(DomainIntelligenceError):
    """Raised when domain-intelligence configuration is invalid."""


class DomainIntelligencePolicyError(DomainIntelligenceError):
    """Raised when analysis violates policy."""


class DomainIntelligenceValidationError(DomainIntelligenceError):
    """Raised when analysis evidence is invalid."""


class DomainPluginNotFoundError(DomainIntelligenceError):
    """Raised when a requested domain plugin is unavailable."""


class DomainPluginCompatibilityError(DomainIntelligenceError):
    """Raised when a plugin is incompatible with Forge."""


class FrontendAnalysisError(DomainIntelligenceError):
    """Raised when frontend analysis cannot complete safely."""