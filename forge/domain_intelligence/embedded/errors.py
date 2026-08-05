"""Typed errors for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class EmbeddedIntelligenceError(DomainIntelligenceError):
    """Base error for embedded-domain intelligence."""


class EmbeddedConfigurationError(EmbeddedIntelligenceError):
    """Raised when embedded analysis configuration is invalid."""


class EmbeddedPolicyError(EmbeddedIntelligenceError):
    """Raised when embedded analysis violates policy."""


class EmbeddedParseError(EmbeddedIntelligenceError):
    """Raised when an embedded artifact cannot be parsed."""