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

$ExpectedBranch = "feature/m5.8-package5-production-runtime-cli"
$Branch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($Branch -ne $ExpectedBranch) {
    throw "Package 5 must run on '$ExpectedBranch'. Current branch: '$Branch'."
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.8 Package 5."
}

Write-Utf8NoBom "forge\mission_runtime\runner.py" @'
"""Public mission-runtime facade over the persisted unified agent runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forge.agent_runtime.cli import _service, _store
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentSession,
    ApprovalKind,
)


@dataclass(frozen=True, slots=True)
class MissionRuntimeRunResult:
    session: AgentSession

    @property
    def session_id(self) -> str:
        return self.session.session_id

    @property
    def status(self) -> str:
        return self.session.status.value


def run_objective(
    *,
    objective: str,
    repository_root: Path,
) -> MissionRuntimeRunResult:
    """Create, persist, and run a mission to its next control boundary."""
    root = repository_root.expanduser().resolve()
    service = _service()

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
    updated = service.run_to_boundary(session)
    _store(root).save_session(updated)
    return MissionRuntimeRunResult(session=updated)


def approve_plan(
    *,
    session_id: str,
    repository_root: Path,
    approved_by: str,
    reason: str,
) -> MissionRuntimeRunResult:
    """Record plan approval and resume the persisted mission."""
    root = repository_root.expanduser().resolve()
    store = _store(root)
    service = _service()
    session = store.load_session(session_id)

    approval = AgentApproval(
        approval_id=f"{session_id}-mission-runtime-plan-approval",
        kind=ApprovalKind.PLAN,
        approved=True,
        approved_by=approved_by,
        reason=reason,
    )

    approved = service.add_approval(session, approval)
    updated = service.run_to_boundary(approved)
    store.save_session(updated)
    return MissionRuntimeRunResult(session=updated)


def load_session(
    *,
    session_id: str,
    repository_root: Path,
) -> AgentSession:
    return _store(repository_root.expanduser().resolve()).load_session(
        session_id
    )


def list_sessions(
    *,
    repository_root: Path,
) -> tuple[str, ...]:
    return _store(
        repository_root.expanduser().resolve()
    ).list_session_ids()
'@

Write-Utf8NoBom "forge\mission_runtime\cli.py" @'
"""CLI for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from forge.mission_runtime.runner import (
    approve_plan,
    list_sessions,
    load_session,
    run_objective,
)

app = typer.Typer(
    name="mission-runtime",
    help="Run and inspect M5.8 Forge Mission Runtime sessions.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Forge Mission Runtime command group."""


@app.command("about")
def about() -> None:
    """Describe the mission runtime integration boundary."""
    typer.echo(
        "M5.8 Forge Mission Runtime: context -> memory -> planning -> "
        "approval -> execution -> verification -> review."
    )


@app.command("run")
def run(
    objective: Annotated[
        str,
        typer.Argument(help="Engineering objective."),
    ],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root", help="Target Git repository root."),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print session JSON."),
    ] = False,
) -> None:
    """Create a mission and run it to the next control boundary."""
    result = run_objective(
        objective=objective,
        repository_root=repository_root,
    )

    if json_output:
        typer.echo(result.session.model_dump_json())
        return

    typer.echo(f"Session ID: {result.session_id}")
    typer.echo(f"Status: {result.status}")


@app.command("approve")
def approve(
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
    """Approve the plan boundary and resume the mission."""
    result = approve_plan(
        session_id=session_id,
        repository_root=repository_root,
        approved_by=approved_by,
        reason=reason,
    )
    typer.echo(f"Session ID: {result.session_id}")
    typer.echo(f"Status: {result.status}")


@app.command("show")
def show(
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
    """Show one persisted mission-runtime session."""
    session = load_session(
        session_id=session_id,
        repository_root=repository_root,
    )

    if json_output:
        typer.echo(session.model_dump_json())
        return

    typer.echo(f"Session ID: {session.session_id}")
    typer.echo(f"Status: {session.status.value}")
    typer.echo(f"Objective: {session.request.objective.objective}")


@app.command("list")
def list_command(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """List persisted mission-runtime sessions."""
    session_ids = list_sessions(
        repository_root=repository_root,
    )

    if json_output:
        typer.echo(json.dumps(list(session_ids)))
        return

    for session_id in session_ids:
        typer.echo(session_id)
'@

Write-Utf8NoBom "tests\test_mission_runtime_runner.py" @'
from pathlib import Path

from forge.agent_runtime.models import AgentSessionStatus
from forge.mission_runtime.runner import (
    approve_plan,
    load_session,
    run_objective,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_runner_stops_at_plan_approval(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = run_objective(
        objective="Plan calculator change",
        repository_root=tmp_path,
    )

    assert result.session.status is AgentSessionStatus.AWAITING_APPROVAL

    persisted = load_session(
        session_id=result.session_id,
        repository_root=tmp_path,
    )
    assert persisted.session_id == result.session_id


def test_runner_resumes_after_plan_approval(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    created = run_objective(
        objective="Plan calculator change",
        repository_root=tmp_path,
    )

    resumed = approve_plan(
        session_id=created.session_id,
        repository_root=tmp_path,
        approved_by="operator",
        reason="approved for test",
    )

    assert resumed.session.status is AgentSessionStatus.COMPLETED
    assert len(resumed.session.stage_results) == 1
'@

Write-Utf8NoBom "tests\test_mission_runtime_cli.py" @'
import json
from pathlib import Path

from typer.testing import CliRunner

from forge.mission_runtime.cli import app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_mission_runtime_about_command() -> None:
    result = runner.invoke(app, ["about"])
    assert result.exit_code == 0
    assert "M5.8 Forge Mission Runtime" in result.stdout


def test_mission_runtime_help_exposes_public_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "approve" in result.stdout
    assert "show" in result.stdout
    assert "list" in result.stdout


def test_mission_runtime_run_creates_persisted_session(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        app,
        [
            "run",
            "Plan calculator change",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Session ID:" in result.stdout
    assert "Status: awaiting_approval" in result.stdout


def test_mission_runtime_run_and_approve(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    created = runner.invoke(
        app,
        [
            "run",
            "Plan calculator change",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert created.exit_code == 0
    payload = json.loads(created.stdout)

    approved = runner.invoke(
        app,
        [
            "approve",
            payload["session_id"],
            "--repository-root",
            str(tmp_path),
            "--reason",
            "approved for test",
        ],
    )

    assert approved.exit_code == 0
    assert "Status: completed" in approved.stdout
'@

Write-Host ""
Write-Host "M5.8 Package 5 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check `
    .\forge\mission_runtime `
    .\tests\test_mission_runtime_runner.py `
    .\tests\test_mission_runtime_cli.py `
    --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_mission_runtime_runner.py `
    .\tests\test_mission_runtime_cli.py `
    .\tests\test_agent_runtime_end_to_end.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.8 Package 5 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository test suite"

python -c "from typer.testing import CliRunner; from forge.cli import app; r=CliRunner().invoke(app,['mission-runtime','--help']); print(r.stdout); raise SystemExit(r.exit_code)"
Assert-CommandSuccess "Mission Runtime CLI help"

Write-Host ""
Write-Host "M5.8 PACKAGE 5 CLI BRIDGE COMPLETE" -ForegroundColor Green
Write-Host "NOTE: Current unified-agent registry remains planning-only." -ForegroundColor Yellow
Write-Host "Real code editing is not yet proven by this package." -ForegroundColor Yellow

git status --short