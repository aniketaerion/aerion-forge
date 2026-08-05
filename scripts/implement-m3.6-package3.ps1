[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\mission_orchestration\recovery.py" @'
"""Recovery, resume and cancellation for M3.6 Mission Orchestration."""

from __future__ import annotations

from pathlib import Path

from forge.mission_orchestration.errors import (
    MissionCancellationError,
    MissionRecoveryError,
)
from forge.mission_orchestration.models import (
    MissionCheckpoint,
    MissionExecution,
    MissionStatus,
    StageRun,
    StageStatus,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy
from forge.mission_orchestration.service import repository_fingerprint


class MissionRecoveryService:
    """Validate and reconstruct resumable mission state."""

    def __init__(
        self,
        policy: MissionOrchestrationPolicy | None = None,
    ) -> None:
        self.policy = policy or MissionOrchestrationPolicy()

    def validate_resume(
        self,
        execution: MissionExecution,
        checkpoint: MissionCheckpoint,
    ) -> None:
        """Reject resume when checkpoint or repository state is stale."""
        if not self.policy.allow_resume:
            raise MissionRecoveryError("mission resume is disabled by policy")

        if execution.request.mission_id != checkpoint.mission_id:
            raise MissionRecoveryError("checkpoint mission ID does not match")

        if execution.workflow.workflow_id != checkpoint.workflow_id:
            raise MissionRecoveryError("checkpoint workflow ID does not match")

        current_fingerprint = repository_fingerprint(
            Path(execution.request.repository_root),
            execution.request.requested_paths,
        )

        if (
            self.policy.stop_on_repository_state_change
            and current_fingerprint != checkpoint.repository_fingerprint
        ):
            raise MissionRecoveryError(
                "repository fingerprint changed after checkpoint"
            )

    def resume(
        self,
        execution: MissionExecution,
        checkpoint: MissionCheckpoint,
    ) -> MissionExecution:
        """Reconstruct a resumable execution from one checkpoint."""
        self.validate_resume(execution, checkpoint)

        if checkpoint.status in {
            MissionStatus.COMPLETED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        }:
            raise MissionRecoveryError(
                f"terminal mission cannot resume: {checkpoint.status.value}"
            )

        return execution.model_copy(
            update={
                "status": MissionStatus.RESUMING,
                "stage_runs": checkpoint.stage_runs,
                "current_stage_id": checkpoint.current_stage_id,
                "checkpoint_id": checkpoint.checkpoint_id,
                "failure_reason": None,
            }
        )

    def cancel(
        self,
        execution: MissionExecution,
        *,
        reason: str,
    ) -> MissionExecution:
        """Cancel a non-terminal mission and retain stage evidence."""
        if not self.policy.allow_cancellation:
            raise MissionCancellationError(
                "mission cancellation is disabled by policy"
            )

        if execution.status in {
            MissionStatus.COMPLETED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        }:
            raise MissionCancellationError(
                f"terminal mission cannot be cancelled: {execution.status.value}"
            )

        if not reason.strip():
            raise MissionCancellationError("cancellation reason is required")

        cancelled_runs = tuple(
            self._cancel_running_stage(run)
            for run in execution.stage_runs
        )

        return execution.model_copy(
            update={
                "status": MissionStatus.CANCELLED,
                "stage_runs": cancelled_runs,
                "current_stage_id": None,
                "failure_reason": reason.strip(),
            }
        )

    @staticmethod
    def _cancel_running_stage(run: StageRun) -> StageRun:
        if run.status not in {
            StageStatus.RUNNING,
            StageStatus.READY,
            StageStatus.AWAITING_APPROVAL,
        }:
            return run

        return run.model_copy(
            update={
                "status": StageStatus.CANCELLED,
                "errors": (*run.errors, "mission cancelled"),
            }
        )
'@

Write-Utf8NoBom "forge\mission_orchestration\reporting.py" @'
"""Mission reporting for M3.6 Mission Orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from forge.mission_orchestration.errors import MissionReportError
from forge.mission_orchestration.identifiers import (
    orchestration_report_identifier,
)
from forge.mission_orchestration.models import (
    MissionExecution,
    MissionReport,
    StageStatus,
)


def build_mission_report(
    execution: MissionExecution,
    *,
    started_at: datetime,
    completed_at: datetime | None = None,
    messages: tuple[str, ...] = (),
) -> MissionReport:
    """Build one deterministic final mission report."""
    artifacts = tuple(
        artifact
        for run in execution.stage_runs
        if run.result is not None
        for artifact in run.result.output_artifacts
    )

    report_id = orchestration_report_identifier(
        {
            "mission_id": execution.request.mission_id,
            "workflow_id": execution.workflow.workflow_id,
            "status": execution.status.value,
            "stage_run_ids": [
                run.stage_run_id for run in execution.stage_runs
            ],
            "output_artifacts": artifacts,
        }
    )

    return MissionReport(
        report_id=report_id,
        mission_id=execution.request.mission_id,
        workflow_id=execution.workflow.workflow_id,
        status=execution.status,
        stage_runs=execution.stage_runs,
        started_at=started_at,
        completed_at=completed_at,
        messages=messages,
        output_artifacts=artifacts,
    )


def render_markdown(report: MissionReport) -> str:
    """Render a compact human-readable mission report."""
    successful = sum(
        1 for run in report.stage_runs if run.status is StageStatus.SUCCEEDED
    )
    failed = sum(
        1 for run in report.stage_runs if run.status is StageStatus.FAILED
    )
    cancelled = sum(
        1 for run in report.stage_runs if run.status is StageStatus.CANCELLED
    )

    lines = [
        "# Engineering Mission Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Mission ID: `{report.mission_id}`",
        f"- Workflow ID: `{report.workflow_id}`",
        f"- Status: `{report.status.value}`",
        f"- Started: `{report.started_at.isoformat()}`",
        f"- Completed: `{report.completed_at.isoformat() if report.completed_at else 'not completed'}`",
        f"- Successful stages: `{successful}`",
        f"- Failed stages: `{failed}`",
        f"- Cancelled stages: `{cancelled}`",
        "",
        "## Stage Timeline",
        "",
    ]

    for run in report.stage_runs:
        lines.extend(
            [
                f"### {run.stage_id}",
                "",
                f"- Attempt: `{run.attempt_number}`",
                f"- Status: `{run.status.value}`",
                f"- Started: `{run.started_at.isoformat() if run.started_at else 'not started'}`",
                f"- Completed: `{run.completed_at.isoformat() if run.completed_at else 'not completed'}`",
                "",
            ]
        )

    if report.output_artifacts:
        lines.extend(["## Output Artifacts", ""])
        lines.extend(f"- `{artifact}`" for artifact in report.output_artifacts)
        lines.append("")

    if report.messages:
        lines.extend(["## Messages", ""])
        lines.extend(f"- {message}" for message in report.messages)
        lines.append("")

    return "\n".join(lines)


def write_report_bundle(
    report: MissionReport,
    destination: Path,
) -> dict[str, Path]:
    """Persist JSON and Markdown mission evidence."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        json_path = destination / "MISSION_ORCHESTRATION_REPORT.json"
        markdown_path = destination / "MISSION_ORCHESTRATION_REPORT.md"

        json_path.write_text(
            json.dumps(
                report.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(
            render_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise MissionReportError(
            f"unable to write mission report bundle: {exc}"
        ) from exc

    return {
        json_path.name: json_path,
        markdown_path.name: markdown_path,
    }


def completed_now() -> datetime:
    """Return an explicit UTC completion timestamp."""
    return datetime.now(UTC)
'@

Write-Utf8NoBom "tests\test_mission_orchestration_recovery.py" @'
from pathlib import Path

import pytest

from forge.mission_orchestration.errors import (
    MissionCancellationError,
    MissionRecoveryError,
)
from forge.mission_orchestration.models import MissionStatus
from forge.mission_orchestration.recovery import MissionRecoveryService
from forge.mission_orchestration.service import MissionOrchestrationService
from forge.mission_orchestration.store import MissionCheckpointStore


def execution_for(tmp_path: Path):
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()
    request = service.create_request(
        repository_root=tmp_path,
        objective="Recover mission",
        requested_paths=("sample.py",),
    )
    return service, service.create_execution(request)


def test_resume_restores_checkpoint_state(tmp_path: Path) -> None:
    service, execution = execution_for(tmp_path)
    execution = service.run_next(execution)
    checkpoint = service.checkpoint(
        execution,
        MissionCheckpointStore(tmp_path / "checkpoints"),
    )

    resumed = MissionRecoveryService().resume(execution, checkpoint)

    assert resumed.status is MissionStatus.RESUMING
    assert resumed.stage_runs == checkpoint.stage_runs
    assert resumed.checkpoint_id == checkpoint.checkpoint_id


def test_resume_rejects_repository_drift(tmp_path: Path) -> None:
    service, execution = execution_for(tmp_path)
    checkpoint = service.checkpoint(
        execution,
        MissionCheckpointStore(tmp_path / "checkpoints"),
    )
    (tmp_path / "sample.py").write_bytes(b"print('changed')\n")

    with pytest.raises(MissionRecoveryError):
        MissionRecoveryService().resume(execution, checkpoint)


def test_cancel_requires_reason(tmp_path: Path) -> None:
    _, execution = execution_for(tmp_path)

    with pytest.raises(MissionCancellationError):
        MissionRecoveryService().cancel(execution, reason="")


def test_cancel_marks_execution_cancelled(tmp_path: Path) -> None:
    _, execution = execution_for(tmp_path)

    cancelled = MissionRecoveryService().cancel(
        execution,
        reason="operator requested cancellation",
    )

    assert cancelled.status is MissionStatus.CANCELLED
    assert cancelled.failure_reason == "operator requested cancellation"
'@

Write-Utf8NoBom "tests\test_mission_orchestration_reporting.py" @'
import json
from datetime import UTC, datetime
from pathlib import Path

from forge.mission_orchestration.reporting import (
    build_mission_report,
    render_markdown,
    write_report_bundle,
)
from forge.mission_orchestration.service import MissionOrchestrationService


def execution_for(tmp_path: Path):
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()
    request = service.create_request(
        repository_root=tmp_path,
        objective="Report mission",
        requested_paths=("sample.py",),
    )
    execution = service.create_execution(request)
    return service.run_next(execution)


def test_build_report_is_deterministic(tmp_path: Path) -> None:
    execution = execution_for(tmp_path)
    started = datetime(2026, 1, 1, tzinfo=UTC)

    first = build_mission_report(execution, started_at=started)
    second = build_mission_report(execution, started_at=started)

    assert first.report_id == second.report_id


def test_markdown_contains_stage_timeline(tmp_path: Path) -> None:
    report = build_mission_report(
        execution_for(tmp_path),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    rendered = render_markdown(report)

    assert "Engineering Mission Report" in rendered
    assert "mission_validation" in rendered


def test_report_bundle_writes_json_and_markdown(tmp_path: Path) -> None:
    report = build_mission_report(
        execution_for(tmp_path),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    written = write_report_bundle(report, tmp_path / "reports")

    assert set(written) == {
        "MISSION_ORCHESTRATION_REPORT.json",
        "MISSION_ORCHESTRATION_REPORT.md",
    }
    payload = json.loads(
        written["MISSION_ORCHESTRATION_REPORT.json"].read_text(
            encoding="utf-8"
        )
    )
    assert payload["mission_id"] == report.mission_id
'@

Write-Host ""
Write-Host "M3.6 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_mission_orchestration_recovery.py `
    .\tests\test_mission_orchestration_reporting.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.6 PACKAGE 3 COMPLETE" -ForegroundColor Green
git status --short
