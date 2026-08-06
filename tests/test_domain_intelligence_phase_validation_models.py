import pytest
from pydantic import ValidationError

from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationReport,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def test_phase_validation_models_are_immutable() -> None:
    check = PhaseValidationCheck(
        check_id="check-1",
        name="Architecture",
        kind=PhaseValidationKind.ARCHITECTURE,
    )

    with pytest.raises(ValidationError):
        check.name = "Changed"


def test_phase_validation_report_requires_unique_checks() -> None:
    check = PhaseValidationCheck(
        check_id="check-1",
        name="Architecture",
        kind=PhaseValidationKind.ARCHITECTURE,
    )

    with pytest.raises(ValidationError):
        PhaseValidationReport(
            report_id="report-1",
            phase="4",
            checks=(check, check),
        )


def test_phase_validation_report_passed_property() -> None:
    check = PhaseValidationCheck(
        check_id="check-1",
        name="Architecture",
        kind=PhaseValidationKind.ARCHITECTURE,
    )
    result = PhaseValidationResult(
        result_id="result-1",
        check_id=check.check_id,
        status=PhaseValidationStatus.PASS,
        message="Architecture validation passed.",
    )

    report = PhaseValidationReport(
        report_id="report-1",
        phase="4",
        checks=(check,),
        results=(result,),
    )

    assert report.passed