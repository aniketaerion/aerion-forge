"""Production-facing mission-runtime facade over unified Agent Runtime."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from forge.agent_runtime.models import AgentApproval, AgentObjective, AgentSession, ApprovalKind
from forge.agent_runtime.production_service import PRODUCTION_CAPABILITIES, production_agent_service
from forge.agent_runtime.store import AgentRuntimeStore


@dataclass(frozen=True, slots=True)
class MissionRuntimeRunResult:
    session: AgentSession

    @property
    def session_id(self) -> str:
        return self.session.session_id

    @property
    def status(self) -> str:
        return self.session.status.value


def _state_store(repository_root: Path) -> AgentRuntimeStore:
    override = os.environ.get("AERION_FORGE_RUNTIME_STATE_ROOT")
    base = (
        Path(override).expanduser().resolve()
        if override
        else Path.home() / ".aerion-forge" / "mission_runtime"
    )
    repository_key = hashlib.sha256(
        str(repository_root.resolve()).encode("utf-8")
    ).hexdigest()[:24]
    return AgentRuntimeStore(base / repository_key)


def _next_approval_kind(session: AgentSession) -> ApprovalKind:
    completed = {result.stage_id for result in session.stage_results}
    for stage in session.stages:
        if stage.stage_id in completed:
            continue
        if not set(stage.depends_on).issubset(completed):
            continue
        if stage.requires_approval is None:
            raise RuntimeError("next mission stage does not require approval")
        return stage.requires_approval
    raise RuntimeError("mission has no pending approval boundary")


def run_objective(*, objective: str, repository_root: Path) -> MissionRuntimeRunResult:
    root = repository_root.expanduser().resolve()
    service = production_agent_service()
    request = service.create_request(
        AgentObjective(
            objective=objective,
            repository_root=str(root),
            requested_capabilities=PRODUCTION_CAPABILITIES,
        ),
        dry_run=False,
        allow_code_changes=True,
    )
    session = service.create_session(request)
    updated = service.run_to_boundary(session)
    _state_store(root).save_session(updated)
    return MissionRuntimeRunResult(session=updated)


def approve_current_boundary(
    *,
    session_id: str,
    repository_root: Path,
    approved_by: str,
    reason: str,
) -> MissionRuntimeRunResult:
    root = repository_root.expanduser().resolve()
    store = _state_store(root)
    service = production_agent_service()
    session = store.load_session(session_id)
    kind = _next_approval_kind(session)
    approval = AgentApproval(
        approval_id=f"{session_id}-{kind.value}-approval-{len(session.approvals) + 1}",
        kind=kind,
        approved=True,
        approved_by=approved_by,
        reason=reason,
    )
    approved = service.add_approval(session, approval)
    updated = service.run_to_boundary(approved)
    store.save_session(updated)
    return MissionRuntimeRunResult(session=updated)


def load_session(*, session_id: str, repository_root: Path) -> AgentSession:
    return _state_store(repository_root.expanduser().resolve()).load_session(session_id)


def list_sessions(*, repository_root: Path) -> tuple[str, ...]:
    return _state_store(repository_root.expanduser().resolve()).list_session_ids()

# Backward-compatible M5.8 Package 5 API.
# Plan approval now delegates to the generic approval-boundary handler.
approve_plan = approve_current_boundary
