"""Typed errors for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class PhaseValidationError(DomainIntelligenceError):
    """Base error for phase-validation intelligence."""


class PhaseValidationConfigurationError(PhaseValidationError):
    """Raised when validation configuration is invalid."""


class PhaseValidationPolicyError(PhaseValidationError):
    """Raised when validation policy is violated."""


class PhaseValidationExecutionError(PhaseValidationError):
    """Raised when a validation check cannot execute."""


class PhaseReleaseError(PhaseValidationError):
    """Raised when a phase is not eligible for release."""