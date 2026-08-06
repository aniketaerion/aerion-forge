"""Typed errors for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class KnowledgeLoaderError(DomainIntelligenceError):
    """Base error for knowledge-loader intelligence."""


class KnowledgeLoaderConfigurationError(KnowledgeLoaderError):
    """Raised when knowledge-loader configuration is invalid."""


class KnowledgeLoaderPolicyError(KnowledgeLoaderError):
    """Raised when a loader operation violates policy."""


class KnowledgeSourceError(KnowledgeLoaderError):
    """Raised when a knowledge source cannot be read or parsed."""


class KnowledgeCompatibilityError(KnowledgeLoaderError):
    """Raised when knowledge content is incompatible."""