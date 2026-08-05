"""Typed errors for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class BackendIntelligenceError(DomainIntelligenceError):
    """Base error for backend-intelligence operations."""


class BackendConfigurationError(BackendIntelligenceError):
    """Raised when backend configuration is invalid."""


class BackendPolicyError(BackendIntelligenceError):
    """Raised when backend analysis violates policy."""


class BackendManifestError(BackendIntelligenceError):
    """Raised when backend project metadata is malformed."""