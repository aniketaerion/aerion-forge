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

$ExpectedBranch = "feature/m5.1-autonomous-runtime-architecture"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.1 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_runtime\reporting.py" @'
"""Reporting helpers for autonomous-runtime missions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.transitions import allowed_targets


def mission_summary(
    mission: AutonomousMission,
) -> dict[str, Any]:
    """Return a deterministic, JSON-serializable mission summary."""
    return {
        "mission_id": mission.mission_id,
        "version": mission.version,
        "state": mission.state.value,
        "risk_class": mission.risk_class.name,
        "granted_authority": mission.granted_authority.name,
        "current_step_id": mission.current_step_id,
        "attempt_count": mission.attempt_count,
        "replan_count": mission.replan_count,
        "tool_call_count": mission.tool_call_count,
        "event_sequence": mission.event_sequence,
        "available_transitions": tuple(
            state.value
            for state in sorted(
                allowed_targets(mission.state),
                key=lambda item: item.value,
            )
        ),
        "outcome_id": mission.outcome_id,
        "updated_at": mission.updated_at.isoformat(),
    }


def render_mission_markdown(
    mission: AutonomousMission,
) -> str:
    """Render a concise mission report."""
    summary = mission_summary(mission)
    transitions = summary["available_transitions"]
    transition_text = (
        ", ".join(transitions)
        if transitions
        else "None"
    )

    return "\n".join(
        [
            "# Aerion Forge Autonomous Mission",
            "",
            f"- Mission ID: `{summary['mission_id']}`",
            f"- Version: `{summary['version']}`",
            f"- State: `{summary['state']}`",
            f"- Risk: `{summary['risk_class']}`",
            f"- Authority: `{summary['granted_authority']}`",
            f"- Current step: `{summary['current_step_id']}`",
            f"- Attempts: `{summary['attempt_count']}`",
            f"- Replans: `{summary['replan_count']}`",
            f"- Tool calls: `{summary['tool_call_count']}`",
            f"- Event sequence: `{summary['event_sequence']}`",
            f"- Available transitions: `{transition_text}`",
            f"- Outcome: `{summary['outcome_id']}`",
            f"- Updated: `{summary['updated_at']}`",
            "",
        ]
    )


def write_mission_report(
    mission: AutonomousMission,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown mission reports."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "MISSION_SUMMARY.json"
    markdown_path = destination / "MISSION_SUMMARY.md"

    json_path.write_text(
        json.dumps(
            mission_summary(mission),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_mission_markdown(mission),
        encoding="utf-8",
    )

    return json_path, markdown_path
'@

Write-Utf8NoBom "forge\autonomous_runtime\cli.py" @'
"""Read-only CLI for the M5.1 autonomous runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_runtime.identifiers import (
    mission_identifier,
    mission_request_identifier,
)
from forge.autonomous_runtime.lifecycle import transition_mission
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.reporting import (
    mission_summary,
    write_mission_report,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)

app = typer.Typer(
    name="autonomous",
    help="Inspect and simulate the Aerion Forge autonomous runtime.",
    no_args_is_help=True,
)

console = Console()


def _dry_run_mission(
    objective: str,
    repository_root: str,
) -> AutonomousMission:
    request_payload = {
        "objective": objective,
        "repository_root": repository_root,
        "requested_by": "cli",
    }
    request = MissionRequest(
        request_id=mission_request_identifier(request_payload),
        objective=objective,
        repository_root=repository_root,
        requested_authority=AuthorityLevel.A1_PLAN,
        requested_by="cli",
    )
    return AutonomousMission(
        mission_id=mission_identifier(
            {
                "request_id": request.request_id,
                "objective": objective,
            }
        ),
        request=request,
    )


@app.command("create-dry-run")
def create_dry_run(
    objective: Annotated[
        str,
        typer.Option(
            "--objective",
            help="Bounded engineering objective.",
        ),
    ],
    repository_root: Annotated[
        str,
        typer.Option(
            "--repository-root",
            help="Repository root used for the mission contract.",
        ),
    ] = ".",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            help="Optional report directory.",
        ),
    ] = None,
) -> None:
    """Create an in-memory read-only mission contract."""
    mission = _dry_run_mission(
        objective,
        repository_root,
    )
    summary = mission_summary(mission)

    table = Table(title="Autonomous Mission Dry Run")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Mission", str(summary["mission_id"]))
    table.add_row("State", str(summary["state"]))
    table.add_row("Authority", str(summary["granted_authority"]))
    table.add_row(
        "Transitions",
        ", ".join(summary["available_transitions"]),
    )
    console.print(table)

    if output is not None:
        paths = write_mission_report(mission, output)
        console.print(f"Reports: {paths[0]} | {paths[1]}")


@app.command("simulate-transition")
def simulate_transition(
    target: Annotated[
        MissionState,
        typer.Option(
            "--target",
            case_sensitive=False,
        ),
    ],
    objective: Annotated[
        str,
        typer.Option("--objective"),
    ] = "Simulate autonomous mission lifecycle.",
    repository_root: Annotated[
        str,
        typer.Option("--repository-root"),
    ] = ".",
) -> None:
    """Simulate one legal transition without repository mutation."""
    mission = _dry_run_mission(
        objective,
        repository_root,
    )
    updated = transition_mission(mission, target)

    console.print_json(
        json.dumps(mission_summary(updated))
    )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_reporting.py" @'
from pathlib import Path

from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.reporting import (
    mission_summary,
    render_mission_markdown,
    write_mission_report,
)
from forge.autonomous_runtime.states import AuthorityLevel


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Report mission state.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A1_PLAN,
            requested_by="Aerion",
        ),
    )


def test_mission_summary_is_structured() -> None:
    summary = mission_summary(mission())

    assert summary["mission_id"] == "mission-1"
    assert summary["state"] == "received"
    assert "qualifying" in summary["available_transitions"]


def test_markdown_report_contains_state() -> None:
    report = render_mission_markdown(mission())

    assert "Autonomous Mission" in report
    assert "`received`" in report


def test_write_mission_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_mission_report(
        mission(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_runtime.cli import app

runner = CliRunner()


def test_create_dry_run_command() -> None:
    result = runner.invoke(
        app,
        [
            "create-dry-run",
            "--objective",
            "Inspect mission contracts.",
            "--repository-root",
            ".",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Mission Dry Run" in normalized
    assert "received" in normalized


def test_simulate_transition_command() -> None:
    result = runner.invoke(
        app,
        [
            "simulate-transition",
            "--target",
            "qualifying",
        ],
    )

    assert result.exit_code == 0
    assert '"state": "qualifying"' in result.stdout
'@

Write-Utf8NoBom "scripts\validate-m5.1-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_runtime\ARCHITECTURE.md",
    ".\docs\autonomous_runtime\SPECIFICATION.md",
    ".\docs\autonomous_runtime\DATA_MODEL.md",
    ".\docs\autonomous_runtime\STATE_MACHINE.md",
    ".\docs\autonomous_runtime\AUTHORITY_MODEL.md",
    ".\docs\autonomous_runtime\EVENT_MODEL.md",
    ".\docs\autonomous_runtime\RECOVERY_MODEL.md",
    ".\docs\autonomous_runtime\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_runtime\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_runtime\states.py",
    ".\forge\autonomous_runtime\models.py",
    ".\forge\autonomous_runtime\transitions.py",
    ".\forge\autonomous_runtime\authority.py",
    ".\forge\autonomous_runtime\approvals.py",
    ".\forge\autonomous_runtime\checkpoints.py",
    ".\forge\autonomous_runtime\recovery.py",
    ".\forge\autonomous_runtime\events.py",
    ".\forge\autonomous_runtime\reporting.py",
    ".\forge\autonomous_runtime\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.1 architecture artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.1 architecture artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_runtime" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.1 architecture documents contain placeholders."
}

Write-Host "M5.1 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m5.1-completion.ps1" @'
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
    -File ".\scripts\validate-m5.1-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.1 architecture validation failed."
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
    .\tests\test_autonomous_runtime_identifiers.py `
    .\tests\test_autonomous_runtime_states.py `
    .\tests\test_autonomous_runtime_models.py `
    .\tests\test_autonomous_runtime_policies.py `
    .\tests\test_autonomous_runtime_transitions.py `
    .\tests\test_autonomous_runtime_invariants.py `
    .\tests\test_autonomous_runtime_lifecycle.py `
    .\tests\test_autonomous_runtime_service.py `
    .\tests\test_autonomous_runtime_authority.py `
    .\tests\test_autonomous_runtime_approvals.py `
    .\tests\test_autonomous_runtime_risk.py `
    .\tests\test_autonomous_runtime_permission.py `
    .\tests\test_autonomous_runtime_checkpoints.py `
    .\tests\test_autonomous_runtime_recovery_engine.py `
    .\tests\test_autonomous_runtime_events.py `
    .\tests\test_autonomous_runtime_recovery_service.py `
    .\tests\test_autonomous_runtime_reporting.py `
    .\tests\test_autonomous_runtime_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.1 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full test suite failed."
}

Write-Host "M5.1 completion validation passed." -ForegroundColor Green
'@

# Repair and integrate forge\cli.py without breaking the module docstring or import block.
$CliPath = Join-Path $RepositoryRoot "forge\cli.py"
$CliContent = Get-Content $CliPath -Raw

$ImportLine = 'from forge.autonomous_runtime.cli import app as autonomous_runtime_app'
$RegistrationLine = 'app.add_typer(autonomous_runtime_app, name="autonomous")'

# Remove any broken prior insertion/registration.
$CliContent = [regex]::Replace(
    $CliContent,
    '(?m)^from forge\.autonomous_runtime\.cli import app as autonomous_runtime_app\r?\n?',
    ''
)
$CliContent = [regex]::Replace(
    $CliContent,
    '(?m)^app\.add_typer\(autonomous_runtime_app, name="autonomous"\)\r?\n?',
    ''
)

# Insert the import immediately before the app declaration, preserving the docstring and import block.
$AppPattern = '(?m)^app\s*=\s*typer\.Typer\('
if ($CliContent -notmatch $AppPattern) {
    throw "Unable to locate the root Typer application declaration in forge\cli.py."
}

$CliContent = [regex]::Replace(
    $CliContent,
    $AppPattern,
    $ImportLine + "`r`n`r`napp = typer.Typer(",
    1
)

# Insert registration immediately before the first command decorator.
$CommandPattern = '(?m)^@app\.(command|callback)\b'
if ($CliContent -match $CommandPattern) {
    $CommandRegex = [regex]::new($CommandPattern)

    $CliContent = $CommandRegex.Replace(
        $CliContent,
        $RegistrationLine + "`r`n`r`n@app.`$1",
        1
    )
}
else {
    $CliContent = $CliContent.TrimEnd() + "`r`n`r`n" + $RegistrationLine + "`r`n"
}

[System.IO.File]::WriteAllText(
    $CliPath,
    $CliContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

# Verify the integration appears exactly once.
$UpdatedCli = Get-Content $CliPath -Raw
$ImportCount = ([regex]::Matches(
    $UpdatedCli,
    [regex]::Escape($ImportLine)
)).Count
$RegistrationCount = ([regex]::Matches(
    $UpdatedCli,
    [regex]::Escape($RegistrationLine)
)).Count

if ($ImportCount -ne 1) {
    throw "Autonomous runtime CLI import count is $ImportCount; expected 1."
}
if ($RegistrationCount -ne 1) {
    throw "Autonomous runtime CLI registration count is $RegistrationCount; expected 1."
}

Write-Host ""
Write-Host "M5.1 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_runtime_reporting.py `
    .\tests\test_autonomous_runtime_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.1 Package 4 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.1-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.1 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.1-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.1 completion validation"

Write-Host ""
Write-Host "M5.1 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short
