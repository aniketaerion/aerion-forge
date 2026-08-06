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
    throw "M5.1 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_runtime\transitions.py" @'
"""Authoritative mission-state transition map."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.states import MissionState


_TRANSITIONS: dict[MissionState, frozenset[MissionState]] = {
    MissionState.RECEIVED: frozenset(
        {
            MissionState.QUALIFYING,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.QUALIFYING: frozenset(
        {
            MissionState.QUALIFIED,
            MissionState.CLARIFICATION_REQUIRED,
            MissionState.ESCALATED,
            MissionState.FAILED,
            MissionState.CANCELLED,
        }
    ),
    MissionState.CLARIFICATION_REQUIRED: frozenset(
        {
            MissionState.QUALIFYING,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.QUALIFIED: frozenset(
        {
            MissionState.CONTEXT_BUILDING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.CONTEXT_BUILDING: frozenset(
        {
            MissionState.CONTEXT_READY,
            MissionState.BLOCKED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.CONTEXT_READY: frozenset(
        {
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.PLANNING: frozenset(
        {
            MissionState.PLAN_READY,
            MissionState.BLOCKED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.PLAN_READY: frozenset(
        {
            MissionState.AWAITING_APPROVAL,
            MissionState.APPROVED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.AWAITING_APPROVAL: frozenset(
        {
            MissionState.APPROVED,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.APPROVED: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.PAUSED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.EXECUTING: frozenset(
        {
            MissionState.VALIDATING,
            MissionState.PAUSED,
            MissionState.BLOCKED,
            MissionState.ROLLING_BACK,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.VALIDATING: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.REVIEWING,
            MissionState.PLANNING,
            MissionState.ROLLING_BACK,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.REVIEWING: frozenset(
        {
            MissionState.COMPLETED,
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.PAUSED: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.BLOCKED: frozenset(
        {
            MissionState.CONTEXT_BUILDING,
            MissionState.PLANNING,
            MissionState.EXECUTING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.ROLLING_BACK: frozenset(
        {
            MissionState.ROLLED_BACK,
            MissionState.ESCALATED,
            MissionState.FAILED,
        }
    ),
    MissionState.ROLLED_BACK: frozenset(
        {
            MissionState.EXECUTING,
            MissionState.PLANNING,
            MissionState.ESCALATED,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.ESCALATED: frozenset(
        {
            MissionState.AWAITING_APPROVAL,
            MissionState.PLANNING,
            MissionState.CANCELLED,
            MissionState.FAILED,
        }
    ),
    MissionState.COMPLETED: frozenset(),
    MissionState.FAILED: frozenset(),
    MissionState.CANCELLED: frozenset(),
}

LEGAL_TRANSITIONS: Final[
    Mapping[MissionState, frozenset[MissionState]]
] = MappingProxyType(_TRANSITIONS)


def allowed_targets(
    state: MissionState,
) -> frozenset[MissionState]:
    """Return legal target states for a mission state."""
    return LEGAL_TRANSITIONS[state]


def can_transition(
    current: MissionState,
    target: MissionState,
) -> bool:
    """Return whether a mission transition is legal."""
    return target in allowed_targets(current)


def assert_transition_allowed(
    current: MissionState,
    target: MissionState,
) -> None:
    """Raise when a transition is not permitted."""
    if not can_transition(current, target):
        raise MissionStateError(
            f"Illegal mission transition: {current.value} -> {target.value}"
        )
'@

Write-Utf8NoBom "forge\autonomous_runtime\invariants.py" @'
"""Mission lifecycle invariant checks."""

from __future__ import annotations

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
    TERMINAL_MISSION_STATES,
)


def assert_budget_available(
    mission: AutonomousMission,
) -> None:
    """Ensure all mission-level execution budgets remain available."""
    budgets = mission.request.budgets

    if mission.replan_count > budgets.maximum_replans:
        raise MissionContractError("Mission replan budget is exhausted.")

    if mission.tool_call_count > budgets.maximum_tool_calls:
        raise MissionContractError("Mission tool-call budget is exhausted.")

    if mission.attempt_count > (
        budgets.maximum_steps
        * budgets.maximum_attempts_per_step
    ):
        raise MissionContractError("Mission attempt budget is exhausted.")


def assert_authority_consistent(
    mission: AutonomousMission,
) -> None:
    """Ensure granted authority does not exceed requested authority."""
    if mission.granted_authority > mission.request.requested_authority:
        raise MissionContractError(
            "Granted authority exceeds requested authority."
        )


def assert_terminal_outcome_consistent(
    mission: AutonomousMission,
) -> None:
    """Ensure terminal missions carry an outcome reference."""
    if (
        mission.state in TERMINAL_MISSION_STATES
        and mission.outcome_id is None
    ):
        raise MissionContractError(
            "Terminal mission requires an outcome identifier."
        )


def assert_execution_authority(
    mission: AutonomousMission,
) -> None:
    """Ensure execution state has sufficient authority."""
    if (
        mission.state is MissionState.EXECUTING
        and mission.granted_authority < AuthorityLevel.A2_MODIFY
    ):
        raise MissionContractError(
            "Executing mission requires at least A2 authority."
        )


def assert_mission_invariants(
    mission: AutonomousMission,
) -> None:
    """Validate all current M5.1 mission invariants."""
    assert_budget_available(mission)
    assert_authority_consistent(mission)
    assert_terminal_outcome_consistent(mission)
    assert_execution_authority(mission)
'@

Write-Utf8NoBom "forge\autonomous_runtime\lifecycle.py" @'
"""Deterministic mission lifecycle operations."""

from __future__ import annotations

from datetime import datetime, timezone

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.invariants import (
    assert_mission_invariants,
)
from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.states import (
    MissionState,
    TERMINAL_MISSION_STATES,
)
from forge.autonomous_runtime.transitions import (
    assert_transition_allowed,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def transition_mission(
    mission: AutonomousMission,
    target: MissionState,
    *,
    outcome_id: str | None = None,
    current_step_id: str | None = None,
    increment_attempt: bool = False,
    increment_replan: bool = False,
    increment_tool_call: bool = False,
) -> AutonomousMission:
    """Return a new immutable mission snapshot in the target state."""
    if mission.state in TERMINAL_MISSION_STATES:
        raise MissionStateError(
            f"Terminal mission cannot transition from {mission.state.value}."
        )

    assert_mission_invariants(mission)
    assert_transition_allowed(mission.state, target)

    if target in TERMINAL_MISSION_STATES and not outcome_id:
        raise MissionStateError(
            "Terminal transition requires an outcome identifier."
        )

    updated = mission.model_copy(
        update={
            "version": mission.version + 1,
            "state": target,
            "current_step_id": current_step_id,
            "attempt_count": mission.attempt_count
            + int(increment_attempt),
            "replan_count": mission.replan_count
            + int(increment_replan),
            "tool_call_count": mission.tool_call_count
            + int(increment_tool_call),
            "outcome_id": outcome_id
            if target in TERMINAL_MISSION_STATES
            else mission.outcome_id,
            "updated_at": utc_now(),
        }
    )

    assert_mission_invariants(updated)
    return updated


def pause_mission(
    mission: AutonomousMission,
) -> AutonomousMission:
    return transition_mission(mission, MissionState.PAUSED)


def cancel_mission(
    mission: AutonomousMission,
    *,
    outcome_id: str,
) -> AutonomousMission:
    return transition_mission(
        mission,
        MissionState.CANCELLED,
        outcome_id=outcome_id,
    )


def fail_mission(
    mission: AutonomousMission,
    *,
    outcome_id: str,
) -> AutonomousMission:
    return transition_mission(
        mission,
        MissionState.FAILED,
        outcome_id=outcome_id,
    )
'@

Write-Utf8NoBom "forge\autonomous_runtime\service.py" @'
"""Application service for deterministic mission lifecycle control."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.lifecycle import transition_mission
from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.states import MissionState
from forge.autonomous_runtime.transitions import allowed_targets


@dataclass(frozen=True, slots=True)
class MissionTransitionRequest:
    """Request to move one mission snapshot to a new state."""

    target: MissionState
    outcome_id: str | None = None
    current_step_id: str | None = None
    increment_attempt: bool = False
    increment_replan: bool = False
    increment_tool_call: bool = False


class AutonomousLifecycleService:
    """Read-only decision and immutable transition service."""

    def available_transitions(
        self,
        mission: AutonomousMission,
    ) -> frozenset[MissionState]:
        return allowed_targets(mission.state)

    def transition(
        self,
        mission: AutonomousMission,
        request: MissionTransitionRequest,
    ) -> AutonomousMission:
        return transition_mission(
            mission,
            request.target,
            outcome_id=request.outcome_id,
            current_step_id=request.current_step_id,
            increment_attempt=request.increment_attempt,
            increment_replan=request.increment_replan,
            increment_tool_call=request.increment_tool_call,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_transitions.py" @'
import pytest

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.states import MissionState
from forge.autonomous_runtime.transitions import (
    allowed_targets,
    assert_transition_allowed,
    can_transition,
)


def test_primary_transition_is_allowed() -> None:
    assert can_transition(
        MissionState.RECEIVED,
        MissionState.QUALIFYING,
    )


def test_terminal_states_have_no_targets() -> None:
    assert allowed_targets(MissionState.COMPLETED) == frozenset()
    assert allowed_targets(MissionState.FAILED) == frozenset()
    assert allowed_targets(MissionState.CANCELLED) == frozenset()


def test_illegal_transition_is_rejected() -> None:
    with pytest.raises(MissionStateError):
        assert_transition_allowed(
            MissionState.RECEIVED,
            MissionState.EXECUTING,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_invariants.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.invariants import (
    assert_budget_available,
    assert_execution_authority,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def request() -> MissionRequest:
    return MissionRequest(
        request_id="request-1",
        objective="Control mission lifecycle.",
        repository_root="repository",
        requested_authority=AuthorityLevel.A2_MODIFY,
        requested_by="Aerion",
    )


def test_execution_requires_modify_authority() -> None:
    mission = AutonomousMission(
        mission_id="mission-1",
        request=request(),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A0_READ,
    )

    with pytest.raises(MissionContractError):
        assert_execution_authority(mission)


def test_budget_exhaustion_is_rejected() -> None:
    mission = AutonomousMission(
        mission_id="mission-2",
        request=request(),
        replan_count=3,
    )

    with pytest.raises(MissionContractError):
        assert_budget_available(mission)


def test_model_still_rejects_authority_above_request() -> None:
    with pytest.raises(ValidationError):
        AutonomousMission(
            mission_id="mission-3",
            request=request(),
            granted_authority=AuthorityLevel.A4_COMMIT,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_lifecycle.py" @'
import pytest

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.lifecycle import transition_mission
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission(
    state: MissionState = MissionState.RECEIVED,
) -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Control mission lifecycle.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=state,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_transition_returns_new_versioned_snapshot() -> None:
    original = mission()
    updated = transition_mission(
        original,
        MissionState.QUALIFYING,
    )

    assert original.state is MissionState.RECEIVED
    assert updated.state is MissionState.QUALIFYING
    assert updated.version == original.version + 1


def test_terminal_transition_requires_outcome() -> None:
    with pytest.raises(MissionStateError):
        transition_mission(
            mission(MissionState.REVIEWING),
            MissionState.COMPLETED,
        )


def test_terminal_mission_cannot_resume() -> None:
    terminal = mission(
        MissionState.REVIEWING
    ).model_copy(
        update={
            "state": MissionState.COMPLETED,
            "outcome_id": "outcome-1",
        }
    )

    with pytest.raises(MissionStateError):
        transition_mission(
            terminal,
            MissionState.PLANNING,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_runtime_service.py" @'
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.service import (
    AutonomousLifecycleService,
    MissionTransitionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Control mission lifecycle.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_service_exposes_available_transitions() -> None:
    service = AutonomousLifecycleService()

    assert MissionState.QUALIFYING in service.available_transitions(
        mission()
    )


def test_service_applies_transition_request() -> None:
    service = AutonomousLifecycleService()

    updated = service.transition(
        mission(),
        MissionTransitionRequest(
            target=MissionState.QUALIFYING,
        ),
    )

    assert updated.state is MissionState.QUALIFYING
    assert updated.version == 2
'@

Write-Host ""
Write-Host "M5.1 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_runtime_transitions.py `
    .\tests\test_autonomous_runtime_invariants.py `
    .\tests\test_autonomous_runtime_lifecycle.py `
    .\tests\test_autonomous_runtime_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.1 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.1 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short