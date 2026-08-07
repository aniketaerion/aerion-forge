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

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\mission_runtime\state_machine.py" @'
"""Mission lifecycle state transitions for M5.8."""

from __future__ import annotations

from forge.mission_runtime.errors import MissionStateError
from forge.mission_runtime.states import MissionState

_ALLOWED: dict[MissionState, frozenset[MissionState]] = {
    MissionState.CREATED: frozenset({
        MissionState.RESOLVING_WORKSPACE,
        MissionState.CANCELLED,
    }),
    MissionState.RESOLVING_WORKSPACE: frozenset({
        MissionState.UNDERSTANDING_REPOSITORY,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.UNDERSTANDING_REPOSITORY: frozenset({
        MissionState.SELECTING_CAPABILITIES,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.SELECTING_CAPABILITIES: frozenset({
        MissionState.RETRIEVING_CONTEXT,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.RETRIEVING_CONTEXT: frozenset({
        MissionState.PLANNING,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.PLANNING: frozenset({
        MissionState.VALIDATING_PLAN,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.VALIDATING_PLAN: frozenset({
        MissionState.AWAITING_PLAN_APPROVAL,
        MissionState.APPROVED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.AWAITING_PLAN_APPROVAL: frozenset({
        MissionState.APPROVED,
        MissionState.PAUSED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    }),
    MissionState.APPROVED: frozenset({
        MissionState.EXECUTING,
        MissionState.CANCELLED,
    }),
    MissionState.EXECUTING: frozenset({
        MissionState.VERIFYING,
        MissionState.RECOVERING,
        MissionState.PAUSED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.RECOVERING: frozenset({
        MissionState.EXECUTING,
        MissionState.PAUSED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.VERIFYING: frozenset({
        MissionState.DOCUMENTING,
        MissionState.RECOVERING,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.DOCUMENTING: frozenset({
        MissionState.GENERATING_REVIEW,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.GENERATING_REVIEW: frozenset({
        MissionState.AWAITING_FINAL_APPROVAL,
        MissionState.FAILED,
        MissionState.CANCELLED,
    }),
    MissionState.AWAITING_FINAL_APPROVAL: frozenset({
        MissionState.COMPLETED,
        MissionState.PAUSED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    }),
    MissionState.PAUSED: frozenset({
        MissionState.AWAITING_PLAN_APPROVAL,
        MissionState.EXECUTING,
        MissionState.AWAITING_FINAL_APPROVAL,
        MissionState.CANCELLED,
        MissionState.FAILED,
    }),
    MissionState.COMPLETED: frozenset(),
    MissionState.FAILED: frozenset(),
    MissionState.CANCELLED: frozenset(),
}


def assert_transition(
    current: MissionState,
    target: MissionState,
) -> None:
    if target not in _ALLOWED[current]:
        raise MissionStateError(
            f"Invalid mission state transition: {current.value} -> {target.value}"
        )
'@

Write-Utf8NoBom "forge\mission_runtime\repository.py" @'
"""In-memory mission runtime repository."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.mission_runtime.models import (
    MissionApproval,
    MissionCheckpoint,
    MissionEvidence,
    MissionResult,
    MissionSession,
)


@dataclass(slots=True)
class InMemoryMissionRepository:
    sessions: dict[str, MissionSession] = field(default_factory=dict)
    approvals: dict[str, MissionApproval] = field(default_factory=dict)
    checkpoints: dict[str, MissionCheckpoint] = field(default_factory=dict)
    evidence: dict[str, MissionEvidence] = field(default_factory=dict)
    results: dict[str, MissionResult] = field(default_factory=dict)

    def put_session(self, session: MissionSession) -> None:
        self.sessions[session.session_id] = session

    def get_session(self, session_id: str) -> MissionSession | None:
        return self.sessions.get(session_id)

    def put_approval(self, approval: MissionApproval) -> None:
        self.approvals[approval.approval_id] = approval

    def put_checkpoint(self, checkpoint: MissionCheckpoint) -> None:
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint

    def put_evidence(self, evidence: MissionEvidence) -> None:
        self.evidence[evidence.evidence_id] = evidence

    def put_result(self, result: MissionResult) -> None:
        self.results[result.result_id] = result
'@

Write-Utf8NoBom "forge\mission_runtime\reporting.py" @'
"""Mission runtime reporting."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.models import MissionSession


@dataclass(frozen=True, slots=True)
class MissionRuntimeReport:
    session_id: str
    state: str
    repository_root: str
    selected_capabilities: tuple[str, ...]
    execution_run_ids: tuple[str, ...]
    verification_references: tuple[str, ...]
    review_package_reference: str | None
    failure_reason: str | None


def build_mission_report(
    session: MissionSession,
) -> MissionRuntimeReport:
    return MissionRuntimeReport(
        session_id=session.session_id,
        state=session.state.value,
        repository_root=session.repository_root,
        selected_capabilities=session.selected_capabilities,
        execution_run_ids=session.execution_run_ids,
        verification_references=session.verification_references,
        review_package_reference=session.review_package_reference,
        failure_reason=session.failure_reason,
    )
'@

Write-Utf8NoBom "forge\mission_runtime\service.py" @'
"""Mission lifecycle application service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.repository import InMemoryMissionRepository
from forge.mission_runtime.state_machine import assert_transition
from forge.mission_runtime.states import MissionState


@dataclass(slots=True)
class MissionRuntimeService:
    repository: InMemoryMissionRepository

    def register(self, session: MissionSession) -> None:
        self.repository.put_session(session)

    def transition(
        self,
        *,
        session_id: str,
        target: MissionState,
    ) -> MissionSession:
        session = self.repository.get_session(session_id)
        if session is None:
            raise KeyError(f"Unknown mission session: {session_id}")

        assert_transition(session.state, target)
        updated = session.model_copy(update={"state": target})
        self.repository.put_session(updated)
        return updated
'@

Write-Utf8NoBom "forge\mission_runtime\cli.py" @'
"""CLI for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="mission-runtime",
    help="Inspect M5.8 Forge Mission Runtime capabilities.",
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
'@

Write-Utf8NoBom "tests\test_mission_runtime_state_machine.py" @'
import pytest

from forge.mission_runtime.errors import MissionStateError
from forge.mission_runtime.state_machine import assert_transition
from forge.mission_runtime.states import MissionState


def test_valid_transition_is_allowed() -> None:
    assert_transition(
        MissionState.CREATED,
        MissionState.RESOLVING_WORKSPACE,
    )


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(MissionStateError):
        assert_transition(
            MissionState.CREATED,
            MissionState.COMPLETED,
        )
'@

Write-Utf8NoBom "tests\test_mission_runtime_repository.py" @'
from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.repository import InMemoryMissionRepository


def test_repository_round_trip() -> None:
    repository = InMemoryMissionRepository()
    session = MissionSession(
        session_id="session-1",
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        repository_fingerprint="fingerprint",
    )

    repository.put_session(session)

    assert repository.get_session("session-1") == session
'@

Write-Utf8NoBom "tests\test_mission_runtime_service.py" @'
from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.repository import InMemoryMissionRepository
from forge.mission_runtime.service import MissionRuntimeService
from forge.mission_runtime.states import MissionState


def test_service_transitions_session() -> None:
    repository = InMemoryMissionRepository()
    service = MissionRuntimeService(repository)
    session = MissionSession(
        session_id="session-1",
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        repository_fingerprint="fingerprint",
    )
    service.register(session)

    updated = service.transition(
        session_id="session-1",
        target=MissionState.RESOLVING_WORKSPACE,
    )

    assert updated.state is MissionState.RESOLVING_WORKSPACE
'@

Write-Utf8NoBom "tests\test_mission_runtime_reporting.py" @'
from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.reporting import build_mission_report


def test_reporting_uses_session_state() -> None:
    session = MissionSession(
        session_id="session-1",
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        repository_fingerprint="fingerprint",
        selected_capabilities=("safe-code-editing",),
    )

    report = build_mission_report(session)

    assert report.session_id == "session-1"
    assert report.state == "created"
    assert report.selected_capabilities == ("safe-code-editing",)
'@

Write-Utf8NoBom "tests\test_mission_runtime_cli.py" @'
from typer.testing import CliRunner

from forge.mission_runtime.cli import app


runner = CliRunner()


def test_mission_runtime_about_command() -> None:
    result = runner.invoke(app, ["about"])

    assert result.exit_code == 0
    assert "M5.8 Forge Mission Runtime" in result.stdout
'@

$CliPath = ".\forge\cli.py"
$CliContent = Get-Content $CliPath -Raw

if ($CliContent -notmatch "forge\.mission_runtime\.cli") {
    $CliContent = $CliContent.Replace(
        "from forge.mission_reporting.cli import report_app",
        "from forge.mission_reporting.cli import report_app`nfrom forge.mission_runtime.cli import app as mission_runtime_app"
    )
}

if ($CliContent -notmatch 'app\.add_typer\(mission_runtime_app, name="mission-runtime"\)') {
    $CliContent = $CliContent.Replace(
        'app.add_typer(mission_orchestration_app, name="orchestrate")',
        'app.add_typer(mission_orchestration_app, name="orchestrate")' + "`n" +
        'app.add_typer(mission_runtime_app, name="mission-runtime")'
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $CliPath),
    $CliContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "PATCHED forge\cli.py" -ForegroundColor Green

Write-Host "M5.8 Package 4 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check forge tests --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check forge tests
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_mission_runtime_state_machine.py `
    .\tests\test_mission_runtime_repository.py `
    .\tests\test_mission_runtime_service.py `
    .\tests\test_mission_runtime_reporting.py `
    .\tests\test_mission_runtime_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.8 Package 4 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

forge mission-runtime about
Assert-CommandSuccess "Mission runtime CLI"

Write-Host ""
Write-Host "M5.8 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short
