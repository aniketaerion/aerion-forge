"""Typed errors for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class BusinessDomainIntelligenceError(DomainIntelligenceError):
    """Base error for business-domain intelligence."""


class BusinessDomainConfigurationError(
    BusinessDomainIntelligenceError
):
    """Raised when business-domain configuration is invalid."""


class BusinessDomainPolicyError(
    BusinessDomainIntelligenceError
):
    """Raised when business-domain analysis violates policy."""


class BusinessDomainParseError(
    BusinessDomainIntelligenceError
):
    """Raised when a business-domain artifact cannot be parsed."""