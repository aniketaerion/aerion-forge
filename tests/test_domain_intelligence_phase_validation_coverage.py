from forge.domain_intelligence.phase_validation.coverage import (
    validate_coverage,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)


def test_coverage_validation_passes() -> None:
    result = validate_coverage(
        collected_test_count=100,
        minimum_test_count=50,
        coverage_percent=85.0,
        minimum_coverage_percent=80.0,
    )

    assert result.status is PhaseValidationStatus.PASS


def test_coverage_validation_fails_without_required_coverage() -> None:
    result = validate_coverage(
        collected_test_count=100,
        minimum_test_count=50,
        coverage_percent=None,
        minimum_coverage_percent=80.0,
    )

    assert result.status is PhaseValidationStatus.FAIL