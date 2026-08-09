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