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

$ExpectedBranch = "feature/m5.2-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.2 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution\reporting.py" @'
"""Reporting helpers for autonomous execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_execution.models import StepExecutionRecord


def execution_summary(
    record: StepExecutionRecord,
) -> dict[str, Any]:
    """Return a deterministic JSON-serializable execution summary."""
    return {
        "execution_id": record.execution_id,
        "mission_id": record.mission_id,
        "step_id": record.step_id,
        "attempt_number": record.attempt_number,
        "lease_id": record.lease_id,
        "checkpoint_id": record.checkpoint_id,
        "state": record.state.value,
        "failure_class": (
            record.failure_class.value
            if record.failure_class is not None
            else None
        ),
        "invocation_count": len(record.invocation_results),
        "evidence_count": len(record.evidence_ids),
        "started_at": record.started_at.isoformat(),
        "completed_at": (
            record.completed_at.isoformat()
            if record.completed_at is not None
            else None
        ),
    }


def render_execution_markdown(
    record: StepExecutionRecord,
) -> str:
    """Render a concise execution report."""
    summary = execution_summary(record)

    return "\n".join(
        [
            "# Aerion Forge Autonomous Execution",
            "",
            f"- Execution ID: `{summary['execution_id']}`",
            f"- Mission ID: `{summary['mission_id']}`",
            f"- Step ID: `{summary['step_id']}`",
            f"- Attempt: `{summary['attempt_number']}`",
            f"- State: `{summary['state']}`",
            f"- Lease: `{summary['lease_id']}`",
            f"- Checkpoint: `{summary['checkpoint_id']}`",
            f"- Failure class: `{summary['failure_class']}`",
            f"- Invocations: `{summary['invocation_count']}`",
            f"- Evidence records: `{summary['evidence_count']}`",
            f"- Started: `{summary['started_at']}`",
            f"- Completed: `{summary['completed_at']}`",
            "",
        ]
    )


def write_execution_report(
    record: StepExecutionRecord,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown execution reports."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "EXECUTION_SUMMARY.json"
    markdown_path = destination / "EXECUTION_SUMMARY.md"

    json_path.write_text(
        json.dumps(
            execution_summary(record),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_execution_markdown(record),
        encoding="utf-8",
    )

    return json_path, markdown_path
'@

Write-Utf8NoBom "forge\autonomous_execution\cli.py" @'
"""Read-only CLI for the M5.2 autonomous execution engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_execution.models import (
    ExecutionRequest,
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.reporting import (
    execution_summary,
    write_execution_report,
)
from forge.autonomous_execution.states import StepExecutionState

app = typer.Typer(
    name="execute",
    help="Inspect and simulate the Aerion Forge execution engine.",
    no_args_is_help=True,
)

console = Console()


@app.command("create-dry-run")
def create_dry_run(
    mission_id: Annotated[
        str,
        typer.Option("--mission-id"),
    ],
    plan_id: Annotated[
        str,
        typer.Option("--plan-id"),
    ],
    step_id: Annotated[
        str,
        typer.Option("--step-id"),
    ],
    repository_root: Annotated[
        str,
        typer.Option("--repository-root"),
    ] = ".",
) -> None:
    """Create a read-only execution request."""
    request = ExecutionRequest(
        request_id=(
            f"execution-request-{mission_id}-{plan_id}-{step_id}"
        ),
        mission_id=mission_id,
        plan_id=plan_id,
        step_id=step_id,
        repository_root=repository_root,
        requested_by="cli",
        dry_run=True,
    )

    table = Table(title="Autonomous Execution Dry Run")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Request", request.request_id)
    table.add_row("Mission", request.mission_id)
    table.add_row("Plan", request.plan_id)
    table.add_row("Step", request.step_id)
    table.add_row("Repository", request.repository_root)
    table.add_row("Dry run", str(request.dry_run))
    console.print(table)


@app.command("report-sample")
def report_sample(
    output: Annotated[
        Path | None,
        typer.Option("--output"),
    ] = None,
) -> None:
    """Render a deterministic sample execution report."""
    record = StepExecutionRecord(
        execution_id="execution-sample",
        mission_id="mission-sample",
        step_id="step-sample",
        state=StepExecutionState.SUCCEEDED,
        evidence_ids=("evidence-sample",),
        completed_at=utc_now(),
    )
    summary = execution_summary(record)

    if output is None:
        console.print_json(json.dumps(summary))
        return

    paths = write_execution_report(record, output)
    console.print(f"Reports: {paths[0]} | {paths[1]}")
'@

Write-Utf8NoBom "tests\test_autonomous_execution_reporting.py" @'
from pathlib import Path

from forge.autonomous_execution.models import (
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.reporting import (
    execution_summary,
    render_execution_markdown,
    write_execution_report,
)
from forge.autonomous_execution.states import StepExecutionState


def record() -> StepExecutionRecord:
    return StepExecutionRecord(
        execution_id="execution-1",
        mission_id="mission-1",
        step_id="step-1",
        state=StepExecutionState.SUCCEEDED,
        evidence_ids=("evidence-1",),
        completed_at=utc_now(),
    )


def test_execution_summary_is_structured() -> None:
    summary = execution_summary(record())

    assert summary["execution_id"] == "execution-1"
    assert summary["state"] == "succeeded"
    assert summary["evidence_count"] == 1


def test_execution_markdown_contains_state() -> None:
    report = render_execution_markdown(record())

    assert "Autonomous Execution" in report
    assert "`succeeded`" in report


def test_write_execution_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_execution_report(
        record(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()
'@

Write-Utf8NoBom "tests\test_autonomous_execution_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_execution.cli import app

runner = CliRunner()


def test_create_dry_run_command() -> None:
    result = runner.invoke(
        app,
        [
            "create-dry-run",
            "--mission-id",
            "mission-1",
            "--plan-id",
            "plan-1",
            "--step-id",
            "step-1",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Execution Dry Run" in normalized
    assert "True" in normalized


def test_report_sample_command() -> None:
    result = runner.invoke(
        app,
        ["report-sample"],
    )

    assert result.exit_code == 0
    assert '"state": "succeeded"' in result.stdout
'@

Write-Utf8NoBom "scripts\validate-m5.2-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_execution\ARCHITECTURE.md",
    ".\docs\autonomous_execution\SPECIFICATION.md",
    ".\docs\autonomous_execution\DATA_MODEL.md",
    ".\docs\autonomous_execution\STATE_MACHINE.md",
    ".\docs\autonomous_execution\TOOL_GATEWAY.md",
    ".\docs\autonomous_execution\FAILURE_MODEL.md",
    ".\docs\autonomous_execution\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_execution\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_execution\models.py",
    ".\forge\autonomous_execution\policies.py",
    ".\forge\autonomous_execution\dependency_graph.py",
    ".\forge\autonomous_execution\planner.py",
    ".\forge\autonomous_execution\tool_registry.py",
    ".\forge\autonomous_execution\tool_gateway.py",
    ".\forge\autonomous_execution\execution_transitions.py",
    ".\forge\autonomous_execution\runtime.py",
    ".\forge\autonomous_execution\reporting.py",
    ".\forge\autonomous_execution\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.2 artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.2 artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_execution" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.2 architecture documents contain placeholders."
}

Write-Host "M5.2 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m5.2-completion.ps1" @'
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
    -File ".\scripts\validate-m5.2-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.2 architecture validation failed."
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
    .\tests\test_autonomous_execution_identifiers.py `
    .\tests\test_autonomous_execution_models.py `
    .\tests\test_autonomous_execution_policies.py `
    .\tests\test_autonomous_execution_tool_contracts.py `
    .\tests\test_autonomous_execution_dependency_graph.py `
    .\tests\test_autonomous_execution_eligibility.py `
    .\tests\test_autonomous_execution_scheduler.py `
    .\tests\test_autonomous_execution_planner.py `
    .\tests\test_autonomous_execution_tool_registry.py `
    .\tests\test_autonomous_execution_argument_validation.py `
    .\tests\test_autonomous_execution_effect_verification.py `
    .\tests\test_autonomous_execution_tool_gateway.py `
    .\tests\test_autonomous_execution_transitions.py `
    .\tests\test_autonomous_execution_lease_manager.py `
    .\tests\test_autonomous_execution_evidence.py `
    .\tests\test_autonomous_execution_runtime.py `
    .\tests\test_autonomous_execution_reporting.py `
    .\tests\test_autonomous_execution_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.2 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full test suite failed."
}

Write-Host "M5.2 completion validation passed." -ForegroundColor Green
'@

# Integrate the execution CLI into forge\cli.py without disturbing the docstring.
$RootCliPath = Join-Path $RepositoryRoot "forge\cli.py"
$ImportLine = 'from forge.autonomous_execution.cli import app as autonomous_execution_app'
$RegistrationLine = 'app.add_typer(autonomous_execution_app, name="execute")'

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
Write-Host "M5.2 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_reporting.py `
    .\tests\test_autonomous_execution_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.2 Package 4 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.2-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.2 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.2-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.2 completion validation"

Write-Host ""
Write-Host "M5.2 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short