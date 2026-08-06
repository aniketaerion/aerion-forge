from forge.autonomous_orchestration.budget_monitor import (
    evaluate_budgets,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)


def test_budget_monitor_detects_cycle_exhaustion() -> None:
    policy = AutonomousOrchestrationPolicy()
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        cycle_count=policy.budgets.maximum_cycles,
    )

    result = evaluate_budgets(session, policy)

    assert not result.allowed
    assert "maximum_cycles" in result.exhausted