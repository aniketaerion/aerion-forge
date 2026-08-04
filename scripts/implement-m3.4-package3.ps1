[CmdletBinding()]
param([string]$RepositoryRoot = "D:\Software Dev\Aerion Forge")
$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param([string]$Path,[string]$Content)
    $FullPath = Join-Path $RepositoryRoot $Path
    New-Item -ItemType Directory -Path (Split-Path $FullPath -Parent) -Force | Out-Null
    [System.IO.File]::WriteAllText($FullPath,$Content,[System.Text.UTF8Encoding]::new($false))
    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\validation_repair\planner.py" @'
"""Bounded repair-candidate planning."""

from __future__ import annotations

from collections import defaultdict

from forge.validation_repair.identifiers import repair_candidate_identifier
from forge.validation_repair.models import RepairCandidate, ValidationFinding


def plan_repairs(findings: tuple[ValidationFinding, ...]) -> tuple[RepairCandidate, ...]:
    """Group actionable findings by path into bounded repair candidates."""
    grouped: dict[str, list[ValidationFinding]] = defaultdict(list)
    for finding in findings:
        if finding.path:
            grouped[finding.path].append(finding)

    candidates: list[RepairCandidate] = []
    for path in sorted(grouped):
        items = grouped[path]
        finding_ids = tuple(sorted(item.finding_id for item in items))
        tools = sorted({item.tool.value for item in items})
        objective = (
            f"Repair {len(items)} validation finding(s) in {path} "
            f"reported by {', '.join(tools)}"
        )
        candidates.append(
            RepairCandidate(
                candidate_id=repair_candidate_identifier(
                    {"path": path, "finding_ids": finding_ids, "objective": objective}
                ),
                finding_ids=finding_ids,
                objective=objective,
                target_paths=(path,),
                risk_notes=(
                    "Candidate is bounded to one repository-relative path.",
                    "Apply mode requires explicit approval.",
                ),
            )
        )
    return tuple(candidates)
'@

Write-Utf8NoBom "forge\validation_repair\service.py" @'
"""Validation and bounded repair orchestration."""

from __future__ import annotations

from pathlib import Path

from forge.validation_repair.errors import RepairAttemptLimitError, RepairPlanningError
from forge.validation_repair.identifiers import repair_session_identifier
from forge.validation_repair.models import (
    RepairAttempt,
    RepairCandidate,
    RepairReport,
    RepairSession,
    RepairStatus,
    ValidationCommand,
    ValidationRun,
    ValidationStatus,
)
from forge.validation_repair.planner import plan_repairs
from forge.validation_repair.policies import ValidationRepairPolicy
from forge.validation_repair.runner import run_validation


class ValidationRepairService:
    """Run validators and create bounded repair-session evidence."""

    def __init__(self, policy: ValidationRepairPolicy | None = None) -> None:
        self.policy = policy or ValidationRepairPolicy()

    def validate(
        self,
        repository_root: Path,
        commands: tuple[ValidationCommand, ...],
    ) -> tuple[ValidationRun, ...]:
        return tuple(
            run_validation(repository_root, command, self.policy)
            for command in commands
        )

    def plan(
        self,
        validation_runs: tuple[ValidationRun, ...],
    ) -> tuple[RepairCandidate, ...]:
        findings = tuple(
            finding
            for run in validation_runs
            if run.status is not ValidationStatus.PASSED
            for finding in run.findings
        )
        candidates = plan_repairs(findings)
        if findings and not candidates:
            raise RepairPlanningError(
                "validation findings could not be mapped to target paths"
            )
        return candidates

    def create_session(
        self,
        repository_root: Path,
        candidates: tuple[RepairCandidate, ...],
        *,
        approved: bool = False,
    ) -> RepairSession:
        root = self.policy.resolve_repository(repository_root)
        if len(candidates) > self.policy.max_repair_attempts:
            raise RepairAttemptLimitError(
                "candidate count exceeds configured repair-attempt limit"
            )
        attempts = tuple(
            RepairAttempt(
                attempt_number=index,
                candidate=candidate,
                status=RepairStatus.PLANNED,
            )
            for index, candidate in enumerate(candidates, start=1)
        )
        return RepairSession(
            session_id=repair_session_identifier(
                {
                    "repository_root": str(root),
                    "candidate_ids": [c.candidate_id for c in candidates],
                    "approved": approved,
                }
            ),
            repository_root=str(root),
            max_attempts=self.policy.max_repair_attempts,
            attempts=attempts,
            approved=approved,
        )

    def build_report(
        self,
        session: RepairSession,
        validation_runs: tuple[ValidationRun, ...],
    ) -> RepairReport:
        succeeded = bool(validation_runs) and all(
            run.status is ValidationStatus.PASSED for run in validation_runs
        )
        return RepairReport(
            session_id=session.session_id,
            repository_root=session.repository_root,
            succeeded=succeeded,
            attempts=session.attempts,
            final_validation_runs=validation_runs,
            messages=("No repair has been applied in Package 3.",),
        )
'@

Write-Utf8NoBom "tests\test_validation_repair_planner.py" @'
from forge.validation_repair.models import (
    FindingSeverity,
    ValidationFinding,
    ValidationTool,
)
from forge.validation_repair.planner import plan_repairs


def finding(path: str, finding_id: str) -> ValidationFinding:
    return ValidationFinding(
        finding_id=finding_id,
        tool=ValidationTool.RUFF,
        severity=FindingSeverity.ERROR,
        code="F401",
        message="unused import",
        path=path,
        line=1,
        column=1,
    )


def test_planner_groups_findings_by_path() -> None:
    candidates = plan_repairs(
        (finding("a.py", "f1"), finding("a.py", "f2"), finding("b.py", "f3"))
    )
    assert len(candidates) == 2
    assert candidates[0].target_paths == ("a.py",)
    assert candidates[0].finding_ids == ("f1", "f2")


def test_planner_ignores_findings_without_paths() -> None:
    item = ValidationFinding(
        finding_id="f1",
        tool=ValidationTool.PYTEST,
        severity=FindingSeverity.ERROR,
        code="pytest-failure",
        message="failure",
    )
    assert plan_repairs((item,)) == ()
'@

Write-Utf8NoBom "tests\test_validation_repair_service.py" @'
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
'@

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest .\tests\test_validation_repair_planner.py .\tests\test_validation_repair_service.py -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.4 PACKAGE 3 COMPLETE" -ForegroundColor Green
git status --short
