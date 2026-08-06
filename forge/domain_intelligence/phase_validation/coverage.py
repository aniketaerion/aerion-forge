"""Test-count and coverage validation for M4.8 Package 2."""

from __future__ import annotations

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


def coverage_check() -> PhaseValidationCheck:
    payload = {
        "name": "Coverage validation",
        "kind": PhaseValidationKind.COVERAGE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Coverage validation",
        kind=PhaseValidationKind.COVERAGE,
        description=(
            "Validate collected test count and configured coverage "
            "thresholds."
        ),
    )


def validate_coverage(
    *,
    collected_test_count: int,
    minimum_test_count: int,
    coverage_percent: float | None,
    minimum_coverage_percent: float,
) -> PhaseValidationResult:
    check = coverage_check()

    tests_pass = collected_test_count >= minimum_test_count
    coverage_required = minimum_coverage_percent > 0.0

    if not coverage_required:
        coverage_pass = True
    elif coverage_percent is None:
        coverage_pass = False
    else:
        coverage_pass = (
            coverage_percent >= minimum_coverage_percent
        )
    passed = tests_pass and coverage_pass
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )

    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "collected_test_count": collected_test_count,
        "minimum_test_count": minimum_test_count,
        "coverage_percent": coverage_percent,
        "minimum_coverage_percent": minimum_coverage_percent,
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Coverage and test-count requirements passed."
            if passed
            else "Coverage or test-count requirements failed."
        ),
        evidence={
            "collected_test_count": str(collected_test_count),
            "minimum_test_count": str(minimum_test_count),
            "coverage_percent": (
                "not-provided"
                if coverage_percent is None
                else f"{coverage_percent:.2f}"
            ),
            "minimum_coverage_percent": (
                f"{minimum_coverage_percent:.2f}"
            ),
        },
    )