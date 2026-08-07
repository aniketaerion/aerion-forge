import pytest

from forge.mission_runtime.verification import (
    MissionVerificationResult,
)


def test_passed_verification_requires_evidence() -> None:
    with pytest.raises(ValueError):
        MissionVerificationResult(
            passed=True,
            references=(),
            summary="Validation passed.",
        )


def test_verification_accepts_evidence() -> None:
    result = MissionVerificationResult(
        passed=True,
        references=("pytest:1741-passed",),
        summary="All required validation passed.",
    )

    assert result.passed