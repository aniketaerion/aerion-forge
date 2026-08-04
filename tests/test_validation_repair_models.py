import pytest
from pydantic import ValidationError

from forge.validation_repair.models import (
    FindingSeverity,
    RepairAttempt,
    RepairCandidate,
    RepairSession,
    RepairStatus,
    ValidationCommand,
    ValidationFinding,
    ValidationTool,
)


def test_validation_command_is_immutable() -> None:
    command = ValidationCommand(
        command_id="cmd-1",
        tool=ValidationTool.RUFF,
    )

    with pytest.raises(ValidationError):
        command.timeout_seconds = 10


def test_finding_rejects_invalid_line_number() -> None:
    with pytest.raises(ValidationError):
        ValidationFinding(
            finding_id="finding-1",
            tool=ValidationTool.MYPY,
            severity=FindingSeverity.ERROR,
            code="assignment",
            message="invalid assignment",
            line=0,
        )


def test_repair_candidate_requires_findings_and_targets() -> None:
    with pytest.raises(ValidationError):
        RepairCandidate(
            candidate_id="repair-1",
            finding_ids=(),
            objective="repair failure",
            target_paths=(),
        )


def test_repair_session_rejects_excess_attempts() -> None:
    first_candidate = RepairCandidate(
        candidate_id="r1",
        finding_ids=("f1",),
        objective="fix",
        target_paths=("a.py",),
    )
    second_candidate = RepairCandidate(
        candidate_id="r2",
        finding_ids=("f2",),
        objective="fix",
        target_paths=("b.py",),
    )

    first_attempt = RepairAttempt(
        attempt_number=1,
        candidate=first_candidate,
        status=RepairStatus.PLANNED,
    )
    second_attempt = RepairAttempt(
        attempt_number=2,
        candidate=second_candidate,
        status=RepairStatus.PLANNED,
    )

    with pytest.raises(ValidationError):
        RepairSession(
            session_id="session-1",
            repository_root=".",
            max_attempts=1,
            attempts=(first_attempt, second_attempt),
        )