from pathlib import Path

import pytest

from forge.validation_repair.errors import RepairAttemptLimitError
from forge.validation_repair.models import (
    FindingSeverity,
    RepairCandidate,
    ValidationCommand,
    ValidationFinding,
    ValidationRun,
    ValidationStatus,
    ValidationTool,
)
from forge.validation_repair.policies import ValidationRepairPolicy
from forge.validation_repair.service import ValidationRepairService


def failed_run() -> ValidationRun:
    command = ValidationCommand(command_id="ruff", tool=ValidationTool.RUFF)
    finding = ValidationFinding(
        finding_id="f1",
        tool=ValidationTool.RUFF,
        severity=FindingSeverity.ERROR,
        code="F401",
        message="unused import",
        path="a.py",
        line=1,
        column=1,
    )
    return ValidationRun(
        run_id="run-1",
        command=command,
        status=ValidationStatus.FAILED,
        exit_code=1,
        duration_seconds=0.1,
        findings=(finding,),
    )


def test_service_plans_candidate_from_failed_run() -> None:
    candidates = ValidationRepairService().plan((failed_run(),))
    assert len(candidates) == 1
    assert candidates[0].target_paths == ("a.py",)


def test_service_creates_bounded_session(tmp_path: Path) -> None:
    candidate = RepairCandidate(
        candidate_id="r1",
        finding_ids=("f1",),
        objective="fix",
        target_paths=("a.py",),
    )
    session = ValidationRepairService().create_session(tmp_path, (candidate,))
    assert len(session.attempts) == 1
    assert session.attempts[0].attempt_number == 1


def test_service_rejects_too_many_candidates(tmp_path: Path) -> None:
    service = ValidationRepairService(
        ValidationRepairPolicy(max_repair_attempts=1)
    )
    candidates = (
        RepairCandidate(
            candidate_id="r1",
            finding_ids=("f1",),
            objective="fix",
            target_paths=("a.py",),
        ),
        RepairCandidate(
            candidate_id="r2",
            finding_ids=("f2",),
            objective="fix",
            target_paths=("b.py",),
        ),
    )
    with pytest.raises(RepairAttemptLimitError):
        service.create_session(tmp_path, candidates)