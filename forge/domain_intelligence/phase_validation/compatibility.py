"""Compatibility validation for M4.8 Package 2."""

from __future__ import annotations

from collections.abc import Iterable

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def compatibility_check() -> PhaseValidationCheck:
    payload = {
        "name": "Compatibility validation",
        "kind": PhaseValidationKind.COMPATIBILITY.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Compatibility validation",
        kind=PhaseValidationKind.COMPATIBILITY,
        description=(
            "Validate that required compatibility markers are "
            "present in the repository baseline."
        ),
    )


def validate_compatibility(
    *,
    required_markers: Iterable[str],
    available_markers: Iterable[str],
) -> PhaseValidationResult:
    check = compatibility_check()
    required = tuple(sorted(set(required_markers)))
    available = set(available_markers)
    missing = tuple(
        marker
        for marker in required
        if marker not in available
    )
    passed = not missing
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )

    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "required_markers": required,
        "missing_markers": missing,
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Compatibility requirements passed."
            if passed
            else "Compatibility requirements are incomplete."
        ),
        evidence={
            "required_markers": ",".join(required),
            "missing_markers": ",".join(missing),
        },
    )