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

Write-Utf8NoBom "forge\agent_runtime\cli.py" @'
"""CLI for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    ApprovalKind,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.reporting import write_report_bundle
from forge.agent_runtime.service import AgentRuntimeService
from forge.agent_runtime.store import AgentRuntimeStore

agent_app = typer.Typer(
    help="Run bounded unified engineering-agent sessions.",
    no_args_is_help=True,
)

console = Console()


def _planning_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: dict[str, object],
) -> AgentStageResult:
    del repository_root, session, context
    return succeeded_result(stage, "mission plan created")


def _service() -> AgentRuntimeService:
    registry = AgentCapabilityRegistry(
        (PlanningAdapter(_planning_executor),)
    )
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )
    return AgentRuntimeService(registry, policy)


def _store(root: Path) -> AgentRuntimeStore:
    return AgentRuntimeStore(
        root / "memory" / "agent_runtime"
    )


@agent_app.command("create")
def create_session(
    objective: Annotated[
        str,
        typer.Option("--objective", help="Engineering objective."),
    ],
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            help="Target Git repository root.",
        ),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print session JSON."),
    ] = False,
) -> None:
    """Create and persist a planning-only agent session."""
    service = _service()
    root = repository_root.resolve()
    request = service.create_request(
        AgentObjective(
            objective=objective,
            repository_root=str(root),
            requested_capabilities=(
                AgentCapability.MISSION_PLANNING,
            ),
        )
    )
    session = service.create_session(request)
    _store(root).save_session(session)

    if json_output:
        console.print_json(session.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {session.session_id}")
    console.print(f"[bold]Status:[/bold] {session.status.value}")


@agent_app.command("approve")
def approve_session(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    approved_by: Annotated[
        str,
        typer.Option("--approved-by"),
    ] = "operator",
    reason: Annotated[
        str,
        typer.Option("--reason"),
    ] = "approved",
) -> None:
    """Add plan approval to a persisted session."""
    root = repository_root.resolve()
    store = _store(root)
    service = _service()
    session = store.load_session(session_id)
    approval = AgentApproval(
        approval_id=f"{session_id}-plan-approval",
        kind=ApprovalKind.PLAN,
        approved=True,
        approved_by=approved_by,
        reason=reason,
    )
    updated = service.add_approval(session, approval)
    store.save_session(updated)
    console.print("[green]Approval recorded.[/green]")


@agent_app.command("run-next")
def run_next(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
) -> None:
    """Execute exactly one stage and persist the result."""
    root = repository_root.resolve()
    store = _store(root)
    service = _service()
    session = store.load_session(session_id)
    updated = service.run_next(session)
    store.save_session(updated)
    console.print(f"[bold]Status:[/bold] {updated.status.value}")


@agent_app.command("run")
def run_to_boundary(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
) -> None:
    """Run until approval, completion, cancellation, or failure."""
    root = repository_root.resolve()
    store = _store(root)
    service = _service()
    session = store.load_session(session_id)
    updated = service.run_to_boundary(session)
    store.save_session(updated)
    console.print(f"[bold]Status:[/bold] {updated.status.value}")


@agent_app.command("show")
def show_session(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Show persisted agent-session state."""
    session = _store(repository_root.resolve()).load_session(
        session_id
    )

    if json_output:
        console.print_json(session.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {session.session_id}")
    console.print(f"[bold]Status:[/bold] {session.status.value}")
    console.print(
        f"[bold]Objective:[/bold] "
        f"{session.request.objective.objective}"
    )


@agent_app.command("list")
def list_sessions(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
) -> None:
    """List persisted agent sessions."""
    table = Table(title="Unified Agent Sessions")
    table.add_column("Session ID")

    for session_id in _store(
        repository_root.resolve()
    ).list_session_ids():
        table.add_row(session_id)

    console.print(table)


@agent_app.command("report")
def report_session(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    destination: Annotated[
        Path,
        typer.Option("--destination"),
    ] = Path("reports/latest/agent_runtime"),
) -> None:
    """Write JSON and Markdown session reports."""
    root = repository_root.resolve()
    session = _store(root).load_session(session_id)
    written = write_report_bundle(
        session,
        root / destination,
    )
    console.print_json(
        json.dumps(
            {
                name: str(path)
                for name, path in written.items()
            }
        )
    )
'@

Write-Utf8NoBom "tests\test_agent_runtime_cli.py" @'
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from forge.agent_runtime.cli import agent_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_agent_cli_help() -> None:
    result = runner.invoke(agent_app, ["--help"])

    assert result.exit_code == 0
    assert "unified engineering-agent" in result.stdout


def test_agent_cli_create_and_list(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    initialize_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    created = runner.invoke(
        agent_app,
        [
            "create",
            "--objective",
            "Plan feature",
            "--repository-root",
            str(tmp_path),
        ],
    )

    listed = runner.invoke(
        agent_app,
        [
            "list",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert created.exit_code == 0
    assert listed.exit_code == 0
    assert "agent-session-" in listed.stdout
'@

Write-Utf8NoBom "tests\test_agent_runtime_end_to_end.py" @'
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import (
    AgentCapabilityAdapter,
    succeeded_result,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    ApprovalKind,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.service import AgentRuntimeService


class PlanningAdapter(AgentCapabilityAdapter):
    capability = AgentCapability.MISSION_PLANNING

    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(stage, "planned")


def test_agent_runtime_end_to_end(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    service = AgentRuntimeService(
        AgentCapabilityRegistry((PlanningAdapter(),)),
        AgentRuntimePolicy(
            allowed_capabilities=(
                AgentCapability.MISSION_PLANNING,
            )
        ),
    )
    request = service.create_request(
        AgentObjective(
            objective="Plan feature",
            repository_root=str(tmp_path),
            requested_capabilities=(
                AgentCapability.MISSION_PLANNING,
            ),
        )
    )
    session = service.create_session(request)
    approved = service.add_approval(
        session,
        AgentApproval(
            approval_id="approval-1",
            kind=ApprovalKind.PLAN,
            approved=True,
            approved_by="operator",
            reason="approved",
        ),
    )

    completed = service.run_to_boundary(approved)

    assert completed.status is AgentSessionStatus.COMPLETED
    assert len(completed.stage_results) == 1
'@

Write-Utf8NoBom "scripts\validate-m3.8-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProduction = @(
    ".\forge\agent_runtime\__init__.py",
    ".\forge\agent_runtime\errors.py",
    ".\forge\agent_runtime\identifiers.py",
    ".\forge\agent_runtime\models.py",
    ".\forge\agent_runtime\policies.py",
    ".\forge\agent_runtime\registry.py",
    ".\forge\agent_runtime\state.py",
    ".\forge\agent_runtime\executor.py",
    ".\forge\agent_runtime\service.py",
    ".\forge\agent_runtime\store.py",
    ".\forge\agent_runtime\recovery.py",
    ".\forge\agent_runtime\reporting.py",
    ".\forge\agent_runtime\telemetry.py",
    ".\forge\agent_runtime\cli.py"
)

$RequiredTests = @(
    ".\tests\test_agent_runtime_identifiers.py",
    ".\tests\test_agent_runtime_models.py",
    ".\tests\test_agent_runtime_policies.py",
    ".\tests\test_agent_runtime_registry.py",
    ".\tests\test_agent_runtime_state.py",
    ".\tests\test_agent_runtime_executor.py",
    ".\tests\test_agent_runtime_service.py",
    ".\tests\test_agent_runtime_store.py",
    ".\tests\test_agent_runtime_recovery.py",
    ".\tests\test_agent_runtime_reporting.py",
    ".\tests\test_agent_runtime_telemetry.py",
    ".\tests\test_agent_runtime_cli.py",
    ".\tests\test_agent_runtime_end_to_end.py"
)

$RequiredDocs = @(
    ".\docs\agent_runtime\ARCHITECTURE.md",
    ".\docs\agent_runtime\SPECIFICATION.md",
    ".\docs\agent_runtime\DATA_MODEL.md",
    ".\docs\agent_runtime\STATE_MACHINE.md",
    ".\docs\agent_runtime\SECURITY_MODEL.md",
    ".\docs\agent_runtime\CAPABILITY_INTEGRATION.md",
    ".\docs\agent_runtime\ACCEPTANCE_CRITERIA.md"
)

foreach ($Path in $RequiredProduction + $RequiredTests + $RequiredDocs) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M3.8 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M3.8 architecture file: $Path"
    }
}

$Cli = Get-Content ".\forge\cli.py" -Raw

if ($Cli -notmatch 'agent_app') {
    throw "M3.8 agent CLI is not registered in forge\cli.py"
}

Write-Host "M3.8 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m3.8-completion.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "Ruff validation failed."
}

python -m mypy .
if ($LASTEXITCODE -ne 0) {
    throw "MyPy validation failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Pytest validation failed."
}

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m3.8-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M3.8 architecture validation failed."
}

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['agent', '--help']); raise SystemExit(result.exit_code)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "M3.8 CLI verification failed."
}

Write-Host "M3.8 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCli = Get-Content $ForgeCliPath -Raw

if ($ForgeCli -notmatch 'from forge\.agent_runtime\.cli import agent_app') {
    $ImportAnchor = 'from forge import __version__'

    if (-not $ForgeCli.Contains($ImportAnchor)) {
        throw "Could not find forge.cli import insertion anchor."
    }

    $ForgeCli = $ForgeCli.Replace(
        $ImportAnchor,
        $ImportAnchor + "`nfrom forge.agent_runtime.cli import agent_app"
    )
}

if ($ForgeCli -notmatch 'app\.add_typer\(agent_app,\s*name="agent"\)') {
    $RegistrationAnchor = 'app = typer.Typer('

    if (-not $ForgeCli.Contains($RegistrationAnchor)) {
        throw "Could not find forge.cli app anchor."
    }

    $AppEnd = $ForgeCli.IndexOf(")`n", $ForgeCli.IndexOf($RegistrationAnchor))

    if ($AppEnd -lt 0) {
        throw "Could not locate forge.cli app declaration end."
    }

    $InsertAt = $AppEnd + 2
    $ForgeCli = $ForgeCli.Insert(
        $InsertAt,
        "`napp.add_typer(agent_app, name=`"agent`")`n"
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ForgeCliPath),
    $ForgeCli,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green
Write-Host ""
Write-Host "M3.8 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_agent_runtime_cli.py `
    .\tests\test_agent_runtime_end_to_end.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.8 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m3.8-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M3.8 architecture validation"

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['agent', '--help']); raise SystemExit(result.exit_code)" | Out-Null
Assert-CommandSuccess "M3.8 CLI verification"

Write-Host ""
Write-Host "M3.8 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short
