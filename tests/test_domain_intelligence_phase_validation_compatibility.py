from forge.domain_intelligence.phase_validation.compatibility import (
    validate_compatibility,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)


def test_compatibility_validation_passes() -> None:
    result = validate_compatibility(
        required_markers=("python", "powershell"),
        available_markers=("python", "powershell", "git"),
    )

    assert result.status is PhaseValidationStatus.PASS


def test_compatibility_validation_reports_missing_marker() -> None:
    result = validate_compatibility(
        required_markers=("python", "docker"),
        available_markers=("python",),
    )

    assert result.status is PhaseValidationStatus.FAIL
    assert result.evidence["missing_markers"] == "docker"