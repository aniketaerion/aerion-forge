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