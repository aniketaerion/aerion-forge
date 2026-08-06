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