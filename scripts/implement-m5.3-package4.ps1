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

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.3-autonomous-mission-orchestrator"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.3 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_orchestration\reporting.py" @'
"""Reporting helpers for autonomous mission orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_orchestration.models import MissionSession


def orchestration_summary(
    session: MissionSession,
) -> dict[str, Any]:
    """Return a deterministic JSON-serializable session summary."""
    return {
        "session_id": session.session_id,
        "mission_id": session.mission_id,
        "plan_id": session.plan_id,
        "plan_version": session.plan_version,
        "repository_root": session.repository_root,
        "state": session.state.value,
        "current_step_id": session.current_step_id,
        "completed_step_ids": list(session.completed_step_ids),
        "failed_step_ids": list(session.failed_step_ids),
        "cycle_count": session.cycle_count,
        "execution_count": session.execution_count,
        "retry_count": session.retry_count,
        "rollback_count": session.rollback_count,
        "replan_count": session.replan_count,
        "checkpoint_id": session.checkpoint_id,
        "stop_reason": session.stop_reason,
        "version": session.version,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def render_orchestration_markdown(
    session: MissionSession,
) -> str:
    """Render a concise orchestration report."""
    summary = orchestration_summary(session)

    return "\n".join(
        [
            "# Aerion Forge Autonomous Mission Orchestration",
            "",
            f"- Session ID: `{summary['session_id']}`",
            f"- Mission ID: `{summary['mission_id']}`",
            f"- Plan ID: `{summary['plan_id']}`",
            f"- Plan version: `{summary['plan_version']}`",
            f"- Repository: `{summary['repository_root']}`",
            f"- State: `{summary['state']}`",
            f"- Current step: `{summary['current_step_id']}`",
            f"- Completed steps: `{len(summary['completed_step_ids'])}`",
            f"- Failed steps: `{len(summary['failed_step_ids'])}`",
            f"- Cycles: `{summary['cycle_count']}`",
            f"- Executions: `{summary['execution_count']}`",
            f"- Retries: `{summary['retry_count']}`",
            f"- Rollbacks: `{summary['rollback_count']}`",
            f"- Replans: `{summary['replan_count']}`",
            f"- Checkpoint: `{summary['checkpoint_id']}`",
            f"- Stop reason: `{summary['stop_reason']}`",
            f"- Version: `{summary['version']}`",
            "",
        ]
    )


def write_orchestration_report(
    session: MissionSession,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown orchestration reports."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "ORCHESTRATION_SUMMARY.json"
    markdown_path = destination / "ORCHESTRATION_SUMMARY.md"

    json_path.write_text(
        json.dumps(
            orchestration_summary(session),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_orchestration_markdown(session),
        encoding="utf-8",
    )

    return json_path, markdown_path
'@

Write-Utf8NoBom "forge\autonomous_orchestration\cli.py" @'
"""Read-only CLI for the M5.3 autonomous mission orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.reporting import (
    orchestration_summary,
    write_orchestration_report,
)
from forge.autonomous_orchestration.states import OrchestrationState

app = typer.Typer(
    name="orchestrate",
    help="Inspect the Aerion Forge autonomous mission orchestrator.",
    no_args_is_help=True,
)

console = Console()


def sample_session() -> MissionSession:
    """Build a deterministic sample session for CLI inspection."""
    return MissionSession(
        session_id="session-sample",
        mission_id="mission-sample",
        plan_id="plan-sample",
        plan_version=1,
        repository_root=".",
        state=OrchestrationState.PAUSED,
        current_step_id="step-sample",
    )


@app.command("status-sample")
def status_sample() -> None:
    """Render deterministic sample orchestration status."""
    summary = orchestration_summary(sample_session())

    table = Table(title="Autonomous Mission Orchestration")
    table.add_column("Field")
    table.add_column("Value")

    for key in (
        "session_id",
        "mission_id",
        "plan_id",
        "plan_version",
        "state",
        "current_step_id",
        "cycle_count",
        "execution_count",
        "version",
    ):
        table.add_row(key, str(summary[key]))

    console.print(table)


@app.command("report-sample")
def report_sample(
    output: Annotated[
        Path | None,
        typer.Option("--output"),
    ] = None,
) -> None:
    """Render or write a deterministic sample report."""
    session = sample_session()

    if output is None:
        console.print_json(
            json.dumps(orchestration_summary(session))
        )
        return

    paths = write_orchestration_report(session, output)
    console.print(f"Reports: {paths[0]} | {paths[1]}")
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_reporting.py" @'
from pathlib import Path

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.reporting import (
    orchestration_summary,
    render_orchestration_markdown,
    write_orchestration_report,
)
from forge.autonomous_orchestration.states import OrchestrationState


def session() -> MissionSession:
    return MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        state=OrchestrationState.PAUSED,
        current_step_id="step-1",
    )


def test_orchestration_summary_is_structured() -> None:
    summary = orchestration_summary(session())

    assert summary["session_id"] == "session-1"
    assert summary["state"] == "paused"
    assert summary["current_step_id"] == "step-1"


def test_orchestration_markdown_contains_state() -> None:
    report = render_orchestration_markdown(session())

    assert "Autonomous Mission Orchestration" in report
    assert "`paused`" in report


def test_write_orchestration_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_orchestration_report(
        session(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_orchestration.cli import app

runner = CliRunner()


def test_status_sample_command() -> None:
    result = runner.invoke(app, ["status-sample"])

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Mission Orchestration" in normalized
    assert "paused" in normalized


def test_report_sample_command() -> None:
    result = runner.invoke(app, ["report-sample"])

    assert result.exit_code == 0
    assert '"state": "paused"' in result.stdout
'@

Write-Utf8NoBom "scripts\validate-m5.3-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_orchestration\ARCHITECTURE.md",
    ".\docs\autonomous_orchestration\SPECIFICATION.md",
    ".\docs\autonomous_orchestration\DATA_MODEL.md",
    ".\docs\autonomous_orchestration\STATE_MACHINE.md",
    ".\docs\autonomous_orchestration\STOP_MODEL.md",
    ".\docs\autonomous_orchestration\RESUME_MODEL.md",
    ".\docs\autonomous_orchestration\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_orchestration\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_orchestration\models.py",
    ".\forge\autonomous_orchestration\policies.py",
    ".\forge\autonomous_orchestration\transitions.py",
    ".\forge\autonomous_orchestration\session_service.py",
    ".\forge\autonomous_orchestration\plan_loader.py",
    ".\forge\autonomous_orchestration\coordinator.py",
    ".\forge\autonomous_orchestration\iteration_service.py",
    ".\forge\autonomous_orchestration\orchestrator.py",
    ".\forge\autonomous_orchestration\reporting.py",
    ".\forge\autonomous_orchestration\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.3 artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.3 artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_orchestration" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.3 architecture documents contain placeholders."
}

Write-Host "M5.3 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m5.3-completion.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.3-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.3 architecture validation failed."
}

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "Ruff failed."
}

python -m mypy .
if ($LASTEXITCODE -ne 0) {
    throw "MyPy failed."
}

python -m pytest `
    .\tests\test_autonomous_orchestration_identifiers.py `
    .\tests\test_autonomous_orchestration_states.py `
    .\tests\test_autonomous_orchestration_policies.py `
    .\tests\test_autonomous_orchestration_models.py `
    .\tests\test_autonomous_orchestration_transitions.py `
    .\tests\test_autonomous_orchestration_session_registry.py `
    .\tests\test_autonomous_orchestration_session_service.py `
    .\tests\test_autonomous_orchestration_resume.py `
    .\tests\test_autonomous_orchestration_plan_loader.py `
    .\tests\test_autonomous_orchestration_progress.py `
    .\tests\test_autonomous_orchestration_budget_monitor.py `
    .\tests\test_autonomous_orchestration_coordinator.py `
    .\tests\test_autonomous_orchestration_journal.py `
    .\tests\test_autonomous_orchestration_outcome_processor.py `
    .\tests\test_autonomous_orchestration_recovery.py `
    .\tests\test_autonomous_orchestration_iteration_service.py `
    .\tests\test_autonomous_orchestration_reporting.py `
    .\tests\test_autonomous_orchestration_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.3 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full repository test suite failed."
}

Write-Host "M5.3 completion validation passed." -ForegroundColor Green
'@

$RootCliPath = Join-Path $RepositoryRoot "forge\cli.py"
$ImportLine = 'from forge.autonomous_orchestration.cli import app as autonomous_orchestration_app'
$RegistrationLine = 'app.add_typer(autonomous_orchestration_app, name="orchestrate")'

$CliLines = @(
    Get-Content $RootCliPath |
        Where-Object {
            $_.Trim() -ne $ImportLine -and
            $_.Trim() -ne $RegistrationLine
        }
)

$AppIndex = -1

for ($Index = 0; $Index -lt $CliLines.Count; $Index++) {
    if ($CliLines[$Index] -match '^app\s*=\s*typer\.Typer\(') {
        $AppIndex = $Index
        break
    }
}

if ($AppIndex -lt 0) {
    throw "Root Typer application declaration not found in forge\cli.py."
}

$BeforeApp = @()
if ($AppIndex -gt 0) {
    $BeforeApp = @($CliLines[0..($AppIndex - 1)])
}

$FromApp = @($CliLines[$AppIndex..($CliLines.Count - 1)])

$CliLines = @(
    $BeforeApp
    $ImportLine
    ''
    $FromApp
)

$CommandIndex = -1

for ($Index = 0; $Index -lt $CliLines.Count; $Index++) {
    if ($CliLines[$Index] -match '^@app\.(command|callback)\b') {
        $CommandIndex = $Index
        break
    }
}

if ($CommandIndex -lt 0) {
    throw "No root CLI command decorator found in forge\cli.py."
}

$BeforeCommand = @()
if ($CommandIndex -gt 0) {
    $BeforeCommand = @($CliLines[0..($CommandIndex - 1)])
}

$FromCommand = @($CliLines[$CommandIndex..($CliLines.Count - 1)])

$CliLines = @(
    $BeforeCommand
    $RegistrationLine
    ''
    $FromCommand
)

[System.IO.File]::WriteAllLines(
    $RootCliPath,
    $CliLines,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Host ""
Write-Host "M5.3 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_orchestration_reporting.py `
    .\tests\test_autonomous_orchestration_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.3 Package 4 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.3-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.3 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.3-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.3 completion validation"

Write-Host ""
Write-Host "M5.3 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short