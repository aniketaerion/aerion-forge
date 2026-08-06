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

$ExpectedBranch = "feature/m5.7-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.7 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution_v2\reporting.py" @'
"""Reporting for M5.7 autonomous execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from forge.autonomous_execution_v2.history import ExecutionHistory
from forge.autonomous_execution_v2.models import ExecutionRun


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Serializable report for one execution run."""

    run: ExecutionRun
    history: ExecutionHistory


def execution_report_payload(
    report: ExecutionReport,
) -> dict[str, Any]:
    """Return deterministic JSON-ready execution report."""
    succeeded_steps = sum(
        1
        for step in report.run.steps
        if step.state.value == "succeeded"
    )
    failed_steps = sum(
        1
        for step in report.run.steps
        if step.state.value == "failed"
    )

    return {
        "run": report.run.model_dump(mode="json"),
        "attempts": [
            attempt.model_dump(mode="json")
            for attempt in report.history.attempts
        ],
        "evidence": [
            item.model_dump(mode="json")
            for item in report.history.evidence
        ],
        "recovery_decisions": [
            item.model_dump(mode="json")
            for item in report.history.recovery_decisions
        ],
        "summary": {
            "step_count": len(report.run.steps),
            "succeeded_steps": succeeded_steps,
            "failed_steps": failed_steps,
            "attempt_count": len(report.history.attempts),
            "evidence_count": len(report.history.evidence),
            "recovery_count": len(
                report.history.recovery_decisions
            ),
        },
    }


def execution_report_json(
    report: ExecutionReport,
) -> str:
    """Render execution report as JSON."""
    return json.dumps(
        execution_report_payload(report),
        indent=2,
        sort_keys=True,
    )


def execution_report_markdown(
    report: ExecutionReport,
) -> str:
    """Render execution report as Markdown."""
    payload = execution_report_payload(report)
    summary = payload["summary"]

    lines = [
        "# Autonomous Execution Report",
        "",
        f"- Run ID: `{report.run.run_id}`",
        f"- Plan ID: `{report.run.plan_id}`",
        f"- Plan Version: `{report.run.plan_version}`",
        f"- State: `{report.run.state.value}`",
        f"- Repository: `{report.run.repository_root}`",
        f"- Steps: `{summary['step_count']}`",
        f"- Successful Steps: `{summary['succeeded_steps']}`",
        f"- Failed Steps: `{summary['failed_steps']}`",
        f"- Attempts: `{summary['attempt_count']}`",
        f"- Evidence Items: `{summary['evidence_count']}`",
        f"- Recovery Decisions: `{summary['recovery_count']}`",
        "",
        "## Steps",
        "",
    ]

    for step in report.run.steps:
        lines.extend(
            [
                f"### {step.sequence}. {step.name}",
                "",
                f"- Step ID: `{step.step_id}`",
                f"- State: `{step.state.value}`",
                f"- Risk: `{step.risk}`",
                "",
                step.description,
                "",
            ]
        )

    lines.extend(["## Attempts", ""])

    if not report.history.attempts:
        lines.extend(["No execution attempts recorded.", ""])
    else:
        for attempt in report.history.attempts:
            lines.extend(
                [
                    f"### Attempt {attempt.attempt_number}",
                    "",
                    f"- Attempt ID: `{attempt.attempt_id}`",
                    f"- Step ID: `{attempt.step_id}`",
                    f"- State: `{attempt.state.value}`",
                    (
                        f"- Failure: `{attempt.failure_reason}`"
                        if attempt.failure_reason
                        else "- Failure: `none`"
                    ),
                    "",
                ]
            )

    lines.extend(["## Evidence", ""])

    if not report.history.evidence:
        lines.extend(["No execution evidence recorded.", ""])
    else:
        for item in report.history.evidence:
            lines.extend(
                [
                    f"### {item.kind.value}",
                    "",
                    f"- Evidence ID: `{item.evidence_id}`",
                    f"- Step ID: `{item.step_id}`",
                    "",
                    item.summary,
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\cli.py" @'
"""CLI commands for M5.7 autonomous execution."""

from __future__ import annotations

import json

import typer

from forge.autonomous_execution_v2.history import ExecutionHistory
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)
from forge.autonomous_execution_v2.reporting import (
    ExecutionReport,
    execution_report_json,
    execution_report_markdown,
)
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    ExecutionStepState,
)

app = typer.Typer(
    help="Inspect and simulate M5.7 autonomous execution."
)


def _sample_run() -> ExecutionRun:
    return ExecutionRun(
        run_id="execution-run-v2-simulation",
        request_id="execution-request-v2-simulation",
        plan_id="planning-plan-simulation",
        plan_version=1,
        repository_root="simulation-repository",
        repository_fingerprint="simulation-fingerprint",
        state=ExecutionRunState.SUCCEEDED,
        steps=(
            ExecutionStep(
                step_id="execution-step-v2-validate",
                planning_step_id="planning-step-validate",
                sequence=1,
                name="Validate",
                description="Run controlled repository validation.",
                state=ExecutionStepState.SUCCEEDED,
                required_tools=("test",),
                expected_outputs=("validation-results",),
                acceptance_criteria=("Validation passes.",),
            ),
        ),
    )


@app.command("simulate")
def simulate(
    output_format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or markdown.",
    ),
) -> None:
    """Render a deterministic execution simulation."""
    run = _sample_run()
    history = ExecutionHistory(
        run=run,
        attempts=(),
        evidence=(),
        recovery_decisions=(),
    )
    report = ExecutionReport(
        run=run,
        history=history,
    )

    if output_format == "markdown":
        typer.echo(execution_report_markdown(report))
        return

    if output_format != "json":
        raise typer.BadParameter(
            "Format must be 'json' or 'markdown'."
        )

    typer.echo(execution_report_json(report))


@app.command("status")
def status() -> None:
    """Show a deterministic execution status sample."""
    run = _sample_run()
    typer.echo(
        json.dumps(
            {
                "run_id": run.run_id,
                "state": run.state.value,
                "step_count": len(run.steps),
                "completed_steps": sum(
                    1
                    for step in run.steps
                    if step.state
                    is ExecutionStepState.SUCCEEDED
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("policy")
def policy() -> None:
    """Show the default M5.7 execution policy."""
    typer.echo(
        json.dumps(
            AutonomousExecutionV2Policy().model_dump(
                mode="json"
            ),
            indent=2,
            sort_keys=True,
        )
    )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_reporting.py" @'
import json

from forge.autonomous_execution_v2.history import ExecutionHistory
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.reporting import (
    ExecutionReport,
    execution_report_json,
    execution_report_markdown,
)
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    ExecutionStepState,
)


def report() -> ExecutionReport:
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        state=ExecutionRunState.SUCCEEDED,
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                state=ExecutionStepState.SUCCEEDED,
            ),
        ),
    )
    history = ExecutionHistory(
        run=run,
        attempts=(),
        evidence=(),
        recovery_decisions=(),
    )
    return ExecutionReport(
        run=run,
        history=history,
    )


def test_json_report_is_serializable() -> None:
    payload = json.loads(
        execution_report_json(report())
    )

    assert payload["run"]["run_id"] == "run-1"
    assert payload["summary"]["step_count"] == 1
    assert payload["summary"]["succeeded_steps"] == 1


def test_markdown_report_contains_execution_details() -> None:
    markdown = execution_report_markdown(report())

    assert "# Autonomous Execution Report" in markdown
    assert "run-1" in markdown
    assert "Validate" in markdown
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_execution_v2.cli import app


runner = CliRunner()


def test_simulate_outputs_json() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"state": "succeeded"' in result.stdout
    assert '"step_count": 1' in result.stdout


def test_status_outputs_run_state() -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert '"completed_steps": 1' in result.stdout
    assert '"state": "succeeded"' in result.stdout


def test_policy_outputs_safe_defaults() -> None:
    result = runner.invoke(app, ["policy"])

    assert result.exit_code == 0
    assert '"allow_destructive_execution": false' in result.stdout
    assert '"maximum_attempts_per_step": 3' in result.stdout
'@

Write-Utf8NoBom "scripts\validate-m5.7-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    ".\docs\autonomous_execution_v2\ARCHITECTURE.md",
    ".\docs\autonomous_execution_v2\SPECIFICATION.md",
    ".\docs\autonomous_execution_v2\DATA_MODEL.md",
    ".\docs\autonomous_execution_v2\STATE_MACHINE.md",
    ".\docs\autonomous_execution_v2\AUTHORITY_MODEL.md",
    ".\docs\autonomous_execution_v2\RECOVERY_MODEL.md",
    ".\docs\autonomous_execution_v2\EVIDENCE_MODEL.md",
    ".\docs\autonomous_execution_v2\ACCEPTANCE_CRITERIA.md",
    ".\forge\autonomous_execution_v2\models.py",
    ".\forge\autonomous_execution_v2\graph.py",
    ".\forge\autonomous_execution_v2\scheduler.py",
    ".\forge\autonomous_execution_v2\coordinator.py",
    ".\forge\autonomous_execution_v2\repository.py",
    ".\forge\autonomous_execution_v2\service.py",
    ".\forge\autonomous_execution_v2\reporting.py",
    ".\forge\autonomous_execution_v2\cli.py"
)

foreach ($Path in $RequiredFiles) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.7 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty M5.7 architecture file: $Path"
    }
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if (
    -not $CliContent.Contains(
        'name="autonomous-execution-v2"'
    )
) {
    throw "M5.7 CLI registration is missing."
}

Write-Host "M5.7 architecture validation passed." `
    -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m5.7-completion.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-Success {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.7-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-Success "M5.7 architecture validation"

python -m ruff check forge tests
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_v2_identifiers.py `
    .\tests\test_autonomous_execution_v2_states.py `
    .\tests\test_autonomous_execution_v2_policies.py `
    .\tests\test_autonomous_execution_v2_models.py `
    .\tests\test_autonomous_execution_v2_graph.py `
    .\tests\test_autonomous_execution_v2_cycle_detection.py `
    .\tests\test_autonomous_execution_v2_ordering.py `
    .\tests\test_autonomous_execution_v2_eligibility.py `
    .\tests\test_autonomous_execution_v2_scheduler.py `
    .\tests\test_autonomous_execution_v2_graph_builder.py `
    .\tests\test_autonomous_execution_v2_authority.py `
    .\tests\test_autonomous_execution_v2_attempts.py `
    .\tests\test_autonomous_execution_v2_evidence.py `
    .\tests\test_autonomous_execution_v2_step_execution.py `
    .\tests\test_autonomous_execution_v2_coordinator.py `
    .\tests\test_autonomous_execution_v2_repository.py `
    .\tests\test_autonomous_execution_v2_retry.py `
    .\tests\test_autonomous_execution_v2_recovery.py `
    .\tests\test_autonomous_execution_v2_resume.py `
    .\tests\test_autonomous_execution_v2_history.py `
    .\tests\test_autonomous_execution_v2_reporting.py `
    .\tests\test_autonomous_execution_v2_cli.py `
    -p no:cacheprovider
Assert-Success "M5.7 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full repository tests"

Write-Host "M5.7 completion validation passed." `
    -ForegroundColor Green
'@

$RootCliPath = ".\forge\cli.py"

if (-not (Test-Path $RootCliPath)) {
    throw "Missing root CLI file: $RootCliPath"
}

$CliContent = Get-Content $RootCliPath -Raw
$ImportLine = (
    "from forge.autonomous_execution_v2.cli import " +
    "app as autonomous_execution_v2_app"
)
$RegistrationLine = (
    'app.add_typer(' +
    'autonomous_execution_v2_app, ' +
    'name="autonomous-execution-v2"' +
    ')'
)

if (-not $CliContent.Contains($ImportLine)) {
    $ImportAnchor = (
        "from forge.autonomous_execution.cli import " +
        "app as autonomous_execution_app"
    )

    if ($CliContent.Contains($ImportAnchor)) {
        $CliContent = $CliContent.Replace(
            $ImportAnchor,
            $ImportAnchor +
            [Environment]::NewLine +
            $ImportLine
        )
    }
    else {
        $CliContent = (
            $ImportLine +
            [Environment]::NewLine +
            $CliContent
        )
    }
}

if (-not $CliContent.Contains($RegistrationLine)) {
    $CliContent = (
        $CliContent.TrimEnd() +
        [Environment]::NewLine +
        $RegistrationLine +
        [Environment]::NewLine
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $RootCliPath),
    $CliContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Host ""
Write-Host "M5.7 Package 4 files written. Normalizing generated files..." `
    -ForegroundColor Cyan

python -m ruff check `
    .\forge\cli.py `
    .\forge\autonomous_execution_v2\cli.py `
    .\forge\autonomous_execution_v2\reporting.py `
    .\tests\test_autonomous_execution_v2_cli.py `
    .\tests\test_autonomous_execution_v2_reporting.py `
    --fix
Assert-CommandSuccess "Package 4 Ruff normalization"

$Tokens = $null
$ParseErrors = $null

[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path ".\scripts\validate-m5.7-architecture.ps1"),
    [ref]$Tokens,
    [ref]$ParseErrors
) | Out-Null

if ($ParseErrors.Count -gt 0) {
    throw "M5.7 architecture validator syntax failed."
}

$Tokens = $null
$ParseErrors = $null

[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path ".\scripts\validate-m5.7-completion.ps1"),
    [ref]$Tokens,
    [ref]$ParseErrors
) | Out-Null

if ($ParseErrors.Count -gt 0) {
    throw "M5.7 completion validator syntax failed."
}

Write-Host "M5.7 VALIDATOR SYNTAX PASSED" `
    -ForegroundColor Green

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.7-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.7 completion validation"

Write-Host ""
Write-Host "M5.7 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short