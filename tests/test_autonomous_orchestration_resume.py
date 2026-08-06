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