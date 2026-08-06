from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.recovery import decide_recovery
from forge.autonomous_orchestration.states import OrchestrationState


def test_recovery_prefers_retry() -> None:
    decision = decide_recovery(
        MissionSession(
            session_id="session-1",
            mission_id="mission-1",
            plan_id="plan-1",
            plan_version=1,
            repository_root="repository",
        ),
        AutonomousOrchestrationPolicy(),
    )

    assert decision.action == "retry"
    assert decision.target_state is OrchestrationState.RETRY_PENDING