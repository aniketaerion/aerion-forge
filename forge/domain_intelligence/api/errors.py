"""Typed errors for M4.4 API Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class ApiIntelligenceError(DomainIntelligenceError):
    """Base error for API-intelligence operations."""


class ApiConfigurationError(ApiIntelligenceError):
    """Raised when API configuration is invalid."""


class ApiPolicyError(ApiIntelligenceError):
    """Raised when API analysis violates policy."""


class ApiParseError(ApiIntelligenceError):
    """Raised when an API artifact cannot be parsed safely."""