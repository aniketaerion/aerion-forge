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

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

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

$ExpectedBranch = "feature/m5.6-autonomous-planning-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.6 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_planning\reporting.py" @'
"""Reporting for autonomous planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningValidationResult,
)


@dataclass(frozen=True, slots=True)
class PlanningReport:
    """Serializable planning report."""

    plan: PlanningPlan
    validation: PlanningValidationResult


def planning_report_payload(
    report: PlanningReport,
) -> dict[str, Any]:
    """Return deterministic JSON-ready planning report."""
    return {
        "plan": report.plan.model_dump(mode="json"),
        "validation": report.validation.model_dump(
            mode="json"
        ),
        "step_count": len(report.plan.steps),
        "dependency_count": len(report.plan.dependencies),
        "blocking_findings": sum(
            1
            for finding in report.validation.findings
            if finding.blocking
        ),
    }


def planning_report_json(
    report: PlanningReport,
) -> str:
    """Render planning report as JSON."""
    return json.dumps(
        planning_report_payload(report),
        indent=2,
        sort_keys=True,
    )


def planning_report_markdown(
    report: PlanningReport,
) -> str:
    """Render planning report as Markdown."""
    lines = [
        "# Autonomous Planning Report",
        "",
        f"- Plan ID: `{report.plan.plan_id}`",
        f"- Request ID: `{report.plan.request_id}`",
        f"- Version: `{report.plan.version}`",
        f"- State: `{report.plan.state.value}`",
        f"- Risk: `{report.plan.risk.value}`",
        f"- Valid: `{str(report.validation.valid).lower()}`",
        f"- Steps: `{len(report.plan.steps)}`",
        f"- Dependencies: `{len(report.plan.dependencies)}`",
        "",
        "## Summary",
        "",
        report.plan.summary,
        "",
        "## Steps",
        "",
    ]

    for step in report.plan.steps:
        lines.extend(
            [
                f"### {step.sequence}. {step.name}",
                "",
                f"- ID: `{step.step_id}`",
                f"- Kind: `{step.kind.value}`",
                f"- Risk: `{step.risk.value}`",
                (
                    "- Approval: "
                    f"`{step.approval_requirement.value}`"
                ),
                "",
                step.description,
                "",
            ]
        )

    lines.extend(["## Validation Findings", ""])

    if not report.validation.findings:
        lines.extend(["No validation findings.", ""])
    else:
        for finding in report.validation.findings:
            lines.extend(
                [
                    f"### {finding.code}",
                    "",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Blocking: `{str(finding.blocking).lower()}`",
                    "",
                    finding.message,
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"
'@

Write-Utf8NoBom "forge\autonomous_planning\cli.py" @'
"""CLI commands for autonomous planning."""

from __future__ import annotations

import json

import typer

from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.reporting import (
    PlanningReport,
    planning_report_json,
    planning_report_markdown,
)
from forge.autonomous_planning.states import PlanningIntent
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)

app = typer.Typer(
    help="Generate and inspect autonomous engineering plans."
)


@app.command("simulate")
def simulate_plan(
    objective: str = typer.Option(
        "Implement a repository-grounded feature",
        "--objective",
        help="Objective for the simulated plan.",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or markdown.",
    ),
) -> None:
    """Generate and validate a deterministic in-memory plan."""
    policy = AutonomousPlanningPolicy()
    request = PlanningRequest(
        request_id="simulation-request",
        objective=objective,
        repository_root="simulation-repository",
        intent=PlanningIntent.IMPLEMENT_FEATURE,
        acceptance_criteria=("All configured checks pass.",),
        created_by="Aerion Forge CLI",
    )
    context = PlanningContext(
        repository_root="simulation-repository",
        repository_fingerprint="simulation-fingerprint",
        known_capabilities=("analysis", "editing", "testing"),
        validation_commands=(
            "python -m ruff check .",
            "python -m mypy .",
            "python -m pytest -p no:cacheprovider",
        ),
    )
    generated = AutonomousPlanGenerator(
        policy=policy
    ).generate(
        request=request,
        context=context,
    )
    validation = AutonomousPlanValidator(
        policy=policy
    ).validate(generated.plan)
    report = PlanningReport(
        plan=generated.plan,
        validation=validation,
    )

    if output_format == "markdown":
        typer.echo(planning_report_markdown(report))
        return

    if output_format != "json":
        raise typer.BadParameter(
            "Format must be 'json' or 'markdown'."
        )

    typer.echo(planning_report_json(report))


@app.command("policy")
def show_policy() -> None:
    """Show the default autonomous-planning policy."""
    typer.echo(
        json.dumps(
            AutonomousPlanningPolicy().model_dump(
                mode="json"
            ),
            indent=2,
            sort_keys=True,
        )
    )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_reporting.py" @'
import json

from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
    PlanningValidationResult,
)
from forge.autonomous_planning.reporting import (
    PlanningReport,
    planning_report_json,
    planning_report_markdown,
)
from forge.autonomous_planning.states import StepKind


def report() -> PlanningReport:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Repository-grounded plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                kind=StepKind.VALIDATION,
            ),
        ),
    )
    validation = PlanningValidationResult(
        plan_id=plan.plan_id,
        valid=True,
    )
    return PlanningReport(
        plan=plan,
        validation=validation,
    )


def test_json_report_is_serializable() -> None:
    payload = json.loads(
        planning_report_json(report())
    )

    assert payload["step_count"] == 1
    assert payload["plan"]["plan_id"] == "plan-1"


def test_markdown_report_contains_plan() -> None:
    markdown = planning_report_markdown(report())

    assert "# Autonomous Planning Report" in markdown
    assert "plan-1" in markdown
    assert "Validate" in markdown
'@

Write-Utf8NoBom "tests\test_autonomous_planning_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_planning.cli import app


runner = CliRunner()


def test_simulation_outputs_json() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"step_count": 4' in result.stdout
    assert '"valid": true' in result.stdout


def test_policy_outputs_default_policy() -> None:
    result = runner.invoke(app, ["policy"])

    assert result.exit_code == 0
    assert '"maximum_steps": 50' in result.stdout
    assert '"allow_destructive_steps": false' in result.stdout
'@

Write-Utf8NoBom "scripts\validate-m5.6-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredModules = @(
    ".\forge\autonomous_planning\__init__.py",
    ".\forge\autonomous_planning\models.py",
    ".\forge\autonomous_planning\policies.py",
    ".\forge\autonomous_planning\graph.py",
    ".\forge\autonomous_planning\graph_builder.py",
    ".\forge\autonomous_planning\analysis.py",
    ".\forge\autonomous_planning\step_synthesis.py",
    ".\forge\autonomous_planning\plan_generation.py",
    ".\forge\autonomous_planning\validation.py",
    ".\forge\autonomous_planning\approval.py",
    ".\forge\autonomous_planning\repository.py",
    ".\forge\autonomous_planning\service.py",
    ".\forge\autonomous_planning\reporting.py",
    ".\forge\autonomous_planning\cli.py"
)

foreach ($Path in $RequiredModules) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.6 module: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty M5.6 module: $Path"
    }
}

Write-Host "M5.6 architecture validation passed." `
    -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m5.6-completion.ps1" @'
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
    -File ".\scripts\validate-m5.6-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-Success "M5.6 architecture validation"

python -m ruff check .
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_planning_identifiers.py `
    .\tests\test_autonomous_planning_states.py `
    .\tests\test_autonomous_planning_policies.py `
    .\tests\test_autonomous_planning_models.py `
    .\tests\test_autonomous_planning_graph.py `
    .\tests\test_autonomous_planning_cycle_detection.py `
    .\tests\test_autonomous_planning_ordering.py `
    .\tests\test_autonomous_planning_eligibility.py `
    .\tests\test_autonomous_planning_graph_builder.py `
    .\tests\test_autonomous_planning_analysis.py `
    .\tests\test_autonomous_planning_step_synthesis.py `
    .\tests\test_autonomous_planning_dependency_synthesis.py `
    .\tests\test_autonomous_planning_plan_generation.py `
    .\tests\test_autonomous_planning_validation.py `
    .\tests\test_autonomous_planning_approval.py `
    .\tests\test_autonomous_planning_revision.py `
    .\tests\test_autonomous_planning_repository.py `
    .\tests\test_autonomous_planning_service.py `
    .\tests\test_autonomous_planning_reporting.py `
    .\tests\test_autonomous_planning_cli.py `
    -p no:cacheprovider
Assert-Success "M5.6 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full repository tests"

Write-Host "M5.6 completion validation passed." `
    -ForegroundColor Green
'@

$RootCliPath = ".\forge\cli.py"

if (-not (Test-Path $RootCliPath)) {
    throw "Missing root CLI file: $RootCliPath"
}

$CliContent = Get-Content $RootCliPath -Raw

$ImportLine = (
    "from forge.autonomous_planning.cli import " +
    "app as autonomous_planning_app"
)
$RegistrationLine = (
    'app.add_typer(' +
    'autonomous_planning_app, ' +
    'name="autonomous-planning"' +
    ')'
)

if (-not $CliContent.Contains($ImportLine)) {
    $AnchorPattern = (
        '(?m)^(from forge\.autonomous_[^\r\n]+\r?\n)'
    )
    $Matches = [regex]::Matches(
        $CliContent,
        $AnchorPattern
    )

    if ($Matches.Count -gt 0) {
        $LastMatch = $Matches[
            $Matches.Count - 1
        ]
        $InsertAt = (
            $LastMatch.Index +
            $LastMatch.Length
        )
        $CliContent = (
            $CliContent.Substring(0, $InsertAt) +
            $ImportLine +
            [Environment]::NewLine +
            $CliContent.Substring($InsertAt)
        )
    }
    else {
        throw "Unable to locate autonomous CLI import block."
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
Write-Host "M5.6 Package 4 files written. Normalizing generated files..." `
    -ForegroundColor Cyan


python -m ruff check `
    .\forge\cli.py `
    .\forge\autonomous_planning\cli.py `
    .\forge\autonomous_planning\reporting.py `
    .\tests\test_autonomous_planning_cli.py `
    .\tests\test_autonomous_planning_reporting.py `
    --fix
Assert-CommandSuccess "Package 4 Ruff normalization"

Write-Host ""
Write-Host "Running M5.6 completion validation..." `
    -ForegroundColor Cyan

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.6-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.6 completion validation"

Write-Host ""
Write-Host "M5.6 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short
