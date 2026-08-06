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

$ExpectedBranch = "feature/m5.3-autonomous-mission-orchestrator"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.3 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_orchestration\transitions.py" @'
"""State transitions for autonomous mission orchestration."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

from forge.autonomous_orchestration.errors import (
    OrchestrationStateError,
)
from forge.autonomous_orchestration.states import (
    OrchestrationState,
    TERMINAL_ORCHESTRATION_STATES,
)


_TRANSITIONS: dict[
    OrchestrationState,
    frozenset[OrchestrationState],
] = {
    OrchestrationState.CREATED: frozenset(
        {
            OrchestrationState.INITIALIZING,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.INITIALIZING: frozenset(
        {
            OrchestrationState.PLAN_LOADING,
            OrchestrationState.FAILED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.PLAN_LOADING: frozenset(
        {
            OrchestrationState.READY,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.READY: frozenset(
        {
            OrchestrationState.STEP_SELECTING,
            OrchestrationState.PAUSED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.STEP_SELECTING: frozenset(
        {
            OrchestrationState.STEP_PREPARING,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.COMPLETED,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.STEP_PREPARING: frozenset(
        {
            OrchestrationState.STEP_EXECUTING,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.STEP_EXECUTING: frozenset(
        {
            OrchestrationState.OUTCOME_PROCESSING,
            OrchestrationState.RETRY_PENDING,
            OrchestrationState.ROLLBACK_PENDING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.OUTCOME_PROCESSING: frozenset(
        {
            OrchestrationState.PROGRESS_UPDATING,
            OrchestrationState.RETRY_PENDING,
            OrchestrationState.ROLLBACK_PENDING,
            OrchestrationState.REPLAN_PENDING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.PROGRESS_UPDATING: frozenset(
        {
            OrchestrationState.CONTINUE_CHECK,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.CONTINUE_CHECK: frozenset(
        {
            OrchestrationState.STEP_SELECTING,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.RETRY_PENDING,
            OrchestrationState.ROLLBACK_PENDING,
            OrchestrationState.REPLAN_PENDING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.COMPLETED,
            OrchestrationState.FAILED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.AWAITING_APPROVAL: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.CANCELLED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.RETRY_PENDING: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.ROLLBACK_PENDING: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.REPLAN_PENDING: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.PAUSED: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.CANCELLED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.RESUME_VALIDATING: frozenset(
        {
            OrchestrationState.READY,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.ESCALATED: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.CANCELLED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.COMPLETED: frozenset(),
    OrchestrationState.FAILED: frozenset(),
    OrchestrationState.CANCELLED: frozenset(),
}

ORCHESTRATION_TRANSITIONS: Final[
    Mapping[
        OrchestrationState,
        frozenset[OrchestrationState],
    ]
] = MappingProxyType(_TRANSITIONS)


def assert_orchestration_transition(
    current: OrchestrationState,
    target: OrchestrationState,
) -> None:
    """Raise when an orchestration transition is illegal."""
    if current in TERMINAL_ORCHESTRATION_STATES:
        raise OrchestrationStateError(
            f"Terminal orchestration cannot transition "
            f"from {current.value}."
        )

    if target not in ORCHESTRATION_TRANSITIONS[current]:
        raise OrchestrationStateError(
            f"Illegal orchestration transition: "
            f"{current.value} -> {target.value}"
        )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\session_registry.py" @'
"""Single-session registry for autonomous mission orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.states import (
    TERMINAL_ORCHESTRATION_STATES,
)


@dataclass(slots=True)
class InMemorySessionRegistry:
    """Enforce one active orchestration session per mission."""

    _sessions: dict[str, MissionSession] = field(default_factory=dict)

    def create(self, session: MissionSession) -> None:
        existing = self._sessions.get(session.mission_id)

        if (
            existing is not None
            and existing.state not in TERMINAL_ORCHESTRATION_STATES
        ):
            raise OrchestrationContractError(
                "Mission already has an active orchestration session."
            )

        self._sessions[session.mission_id] = session

    def get(self, mission_id: str) -> MissionSession:
        try:
            return self._sessions[mission_id]
        except KeyError as exc:
            raise OrchestrationContractError(
                f"No orchestration session exists for mission: "
                f"{mission_id}"
            ) from exc

    def update(
        self,
        session: MissionSession,
        *,
        expected_version: int,
    ) -> None:
        current = self.get(session.mission_id)

        if current.version != expected_version:
            raise OrchestrationContractError(
                "Orchestration session version conflict."
            )

        if session.version != expected_version + 1:
            raise OrchestrationContractError(
                "Updated orchestration session must increment version "
                "by exactly one."
            )

        self._sessions[session.mission_id] = session

    def active_sessions(self) -> tuple[MissionSession, ...]:
        return tuple(
            session
            for session in sorted(
                self._sessions.values(),
                key=lambda item: item.mission_id,
            )
            if session.state not in TERMINAL_ORCHESTRATION_STATES
        )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\session_service.py" @'
"""Application service for orchestration-session lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.identifiers import (
    mission_session_identifier,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationRequest,
    utc_now,
)
from forge.autonomous_orchestration.session_registry import (
    InMemorySessionRegistry,
)
from forge.autonomous_orchestration.states import OrchestrationState
from forge.autonomous_orchestration.transitions import (
    assert_orchestration_transition,
)


@dataclass(slots=True)
class MissionSessionService:
    """Create and transition versioned orchestration sessions."""

    registry: InMemorySessionRegistry

    def create(
        self,
        request: OrchestrationRequest,
        *,
        plan_id: str,
        plan_version: int,
    ) -> MissionSession:
        session = MissionSession(
            session_id=mission_session_identifier(
                {
                    "mission_id": request.mission_id,
                    "plan_id": plan_id,
                    "plan_version": plan_version,
                    "request_id": request.request_id,
                }
            ),
            mission_id=request.mission_id,
            plan_id=plan_id,
            plan_version=plan_version,
            repository_root=request.repository_root,
        )
        self.registry.create(session)
        return session

    def transition(
        self,
        session: MissionSession,
        target: OrchestrationState,
        *,
        stop_reason: str | None = None,
    ) -> MissionSession:
        assert_orchestration_transition(session.state, target)

        updated = session.model_copy(
            update={
                "state": target,
                "stop_reason": stop_reason,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.registry.update(
            updated,
            expected_version=session.version,
        )
        return updated

    def set_current_step(
        self,
        session: MissionSession,
        step_id: str,
    ) -> MissionSession:
        updated = session.model_copy(
            update={
                "current_step_id": step_id,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.registry.update(
            updated,
            expected_version=session.version,
        )
        return updated

    def mark_step_completed(
        self,
        session: MissionSession,
        step_id: str,
    ) -> MissionSession:
        completed = tuple(
            sorted(
                set(session.completed_step_ids).union({step_id})
            )
        )

        updated = session.model_copy(
            update={
                "current_step_id": (
                    None
                    if session.current_step_id == step_id
                    else session.current_step_id
                ),
                "completed_step_ids": completed,
                "execution_count": session.execution_count + 1,
                "cycle_count": session.cycle_count + 1,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.registry.update(
            updated,
            expected_version=session.version,
        )
        return updated
'@

Write-Utf8NoBom "forge\autonomous_orchestration\checkpointing.py" @'
"""Orchestration-session checkpoint creation and verification."""

from __future__ import annotations

from forge.autonomous_orchestration.identifiers import (
    session_checkpoint_identifier,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    SessionCheckpoint,
)


def build_session_checkpoint(
    session: MissionSession,
    *,
    mission_snapshot_version: int,
    repository_fingerprint: str,
) -> SessionCheckpoint:
    """Create an unverified restart checkpoint."""
    payload = {
        "session_id": session.session_id,
        "session_version": session.version,
        "mission_snapshot_version": mission_snapshot_version,
        "plan_version": session.plan_version,
        "repository_fingerprint": repository_fingerprint,
    }

    return SessionCheckpoint(
        checkpoint_id=session_checkpoint_identifier(payload),
        session_id=session.session_id,
        mission_id=session.mission_id,
        session_version=session.version,
        mission_snapshot_version=mission_snapshot_version,
        plan_version=session.plan_version,
        repository_fingerprint=repository_fingerprint,
        current_step_id=session.current_step_id,
        completed_step_ids=session.completed_step_ids,
        verified=False,
    )


def verify_session_checkpoint(
    checkpoint: SessionCheckpoint,
) -> SessionCheckpoint:
    """Mark a session checkpoint as verified."""
    return checkpoint.model_copy(
        update={"verified": True}
    )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\resume.py" @'
"""Resume validation for autonomous mission orchestration."""

from __future__ import annotations

from forge.autonomous_orchestration.errors import (
    OrchestrationResumeError,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    SessionCheckpoint,
    session_is_resumable,
)
from forge.autonomous_orchestration.states import (
    TERMINAL_ORCHESTRATION_STATES,
)


def validate_resume(
    session: MissionSession,
    checkpoint: SessionCheckpoint,
    *,
    mission_snapshot_version: int,
    plan_version: int,
    repository_fingerprint: str,
) -> None:
    """Validate that an interrupted session may resume safely."""
    if session.state in TERMINAL_ORCHESTRATION_STATES:
        raise OrchestrationResumeError(
            "Terminal orchestration session cannot resume."
        )

    if not session_is_resumable(session):
        raise OrchestrationResumeError(
            f"Session state is not resumable: {session.state.value}"
        )

    if not checkpoint.verified:
        raise OrchestrationResumeError(
            "Resume checkpoint must be verified."
        )

    if checkpoint.session_id != session.session_id:
        raise OrchestrationResumeError(
            "Resume checkpoint belongs to another session."
        )

    if checkpoint.mission_id != session.mission_id:
        raise OrchestrationResumeError(
            "Resume checkpoint belongs to another mission."
        )

    if checkpoint.session_version != session.version:
        raise OrchestrationResumeError(
            "Resume checkpoint session version is stale."
        )

    if checkpoint.mission_snapshot_version != mission_snapshot_version:
        raise OrchestrationResumeError(
            "Mission snapshot version mismatch."
        )

    if checkpoint.plan_version != plan_version:
        raise OrchestrationResumeError(
            "Approved plan version mismatch."
        )

    if checkpoint.repository_fingerprint != repository_fingerprint:
        raise OrchestrationResumeError(
            "Repository fingerprint mismatch."
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_transitions.py" @'
import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationStateError,
)
from forge.autonomous_orchestration.states import OrchestrationState
from forge.autonomous_orchestration.transitions import (
    assert_orchestration_transition,
)


def test_legal_transition_passes() -> None:
    assert_orchestration_transition(
        OrchestrationState.CREATED,
        OrchestrationState.INITIALIZING,
    )


def test_illegal_transition_is_rejected() -> None:
    with pytest.raises(OrchestrationStateError):
        assert_orchestration_transition(
            OrchestrationState.CREATED,
            OrchestrationState.STEP_EXECUTING,
        )


def test_terminal_session_cannot_resume() -> None:
    with pytest.raises(OrchestrationStateError):
        assert_orchestration_transition(
            OrchestrationState.COMPLETED,
            OrchestrationState.RESUME_VALIDATING,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_session_registry.py" @'
import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.session_registry import (
    InMemorySessionRegistry,
)
from forge.autonomous_orchestration.states import OrchestrationState


def session(
    session_id: str,
    *,
    version: int = 1,
    state: OrchestrationState = OrchestrationState.CREATED,
) -> MissionSession:
    return MissionSession(
        session_id=session_id,
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        version=version,
        state=state,
        stop_reason=(
            "Complete."
            if state is OrchestrationState.COMPLETED
            else None
        ),
    )


def test_only_one_active_session_per_mission() -> None:
    registry = InMemorySessionRegistry()
    registry.create(session("session-1"))

    with pytest.raises(OrchestrationContractError):
        registry.create(session("session-2"))


def test_update_requires_matching_version() -> None:
    registry = InMemorySessionRegistry()
    registry.create(session("session-1"))

    with pytest.raises(OrchestrationContractError):
        registry.update(
            session("session-1", version=3),
            expected_version=1,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_session_service.py" @'
from forge.autonomous_orchestration.models import OrchestrationRequest
from forge.autonomous_orchestration.session_registry import (
    InMemorySessionRegistry,
)
from forge.autonomous_orchestration.session_service import (
    MissionSessionService,
)
from forge.autonomous_orchestration.states import OrchestrationState


def test_service_creates_and_transitions_session() -> None:
    service = MissionSessionService(
        registry=InMemorySessionRegistry()
    )
    session = service.create(
        OrchestrationRequest(
            request_id="request-1",
            mission_id="mission-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        plan_id="plan-1",
        plan_version=1,
    )

    session = service.transition(
        session,
        OrchestrationState.INITIALIZING,
    )

    assert session.state is OrchestrationState.INITIALIZING
    assert session.version == 2


def test_service_marks_step_completed() -> None:
    service = MissionSessionService(
        registry=InMemorySessionRegistry()
    )
    session = service.create(
        OrchestrationRequest(
            request_id="request-1",
            mission_id="mission-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        plan_id="plan-1",
        plan_version=1,
    )
    session = service.set_current_step(session, "step-1")
    session = service.mark_step_completed(session, "step-1")

    assert session.current_step_id is None
    assert session.completed_step_ids == ("step-1",)
    assert session.execution_count == 1
    assert session.cycle_count == 1
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_resume.py" @'
import pytest

from forge.autonomous_orchestration.checkpointing import (
    build_session_checkpoint,
    verify_session_checkpoint,
)
from forge.autonomous_orchestration.errors import (
    OrchestrationResumeError,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.resume import validate_resume
from forge.autonomous_orchestration.states import OrchestrationState


def paused_session() -> MissionSession:
    return MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        state=OrchestrationState.PAUSED,
        version=3,
    )


def test_verified_checkpoint_allows_resume() -> None:
    session = paused_session()
    checkpoint = verify_session_checkpoint(
        build_session_checkpoint(
            session,
            mission_snapshot_version=5,
            repository_fingerprint="fingerprint-1",
        )
    )

    validate_resume(
        session,
        checkpoint,
        mission_snapshot_version=5,
        plan_version=1,
        repository_fingerprint="fingerprint-1",
    )


def test_unverified_checkpoint_is_rejected() -> None:
    session = paused_session()
    checkpoint = build_session_checkpoint(
        session,
        mission_snapshot_version=5,
        repository_fingerprint="fingerprint-1",
    )

    with pytest.raises(OrchestrationResumeError):
        validate_resume(
            session,
            checkpoint,
            mission_snapshot_version=5,
            plan_version=1,
            repository_fingerprint="fingerprint-1",
        )
'@

Write-Host ""
Write-Host "M5.3 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_orchestration_transitions.py `
    .\tests\test_autonomous_orchestration_session_registry.py `
    .\tests\test_autonomous_orchestration_session_service.py `
    .\tests\test_autonomous_orchestration_resume.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.3 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.3 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
