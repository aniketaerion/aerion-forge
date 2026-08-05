"""Typed errors for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class DatabaseIntelligenceError(DomainIntelligenceError):
    """Base error for database-intelligence operations."""


class DatabaseConfigurationError(DatabaseIntelligenceError):
    """Raised when database configuration is invalid."""


class DatabasePolicyError(DatabaseIntelligenceError):
    """Raised when database analysis violates policy."""


class DatabaseParseError(DatabaseIntelligenceError):
    """Raised when a database artifact cannot be parsed safely."""