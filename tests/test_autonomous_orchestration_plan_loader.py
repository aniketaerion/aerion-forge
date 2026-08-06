import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.plan_loader import (
    InMemoryApprovedPlanStore,
)
from forge.autonomous_runtime.models import MissionPlan


def plan(version: int = 1) -> MissionPlan:
    return MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        version=version,
        objective_summary="Execute mission.",
        completion_criteria=("Mission complete.",),
        steps=(),
    )


def test_plan_store_loads_expected_version() -> None:
    store = InMemoryApprovedPlanStore()
    store.register(plan())

    loaded = store.load(
        "mission-1",
        expected_plan_id="plan-1",
        expected_version=1,
    )

    assert loaded.version == 1


def test_plan_version_mismatch_is_rejected() -> None:
    store = InMemoryApprovedPlanStore()
    store.register(plan())

    with pytest.raises(OrchestrationContractError):
        store.load(
            "mission-1",
            expected_plan_id="plan-1",
            expected_version=2,
        )