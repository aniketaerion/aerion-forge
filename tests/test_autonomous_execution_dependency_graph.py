import pytest

from forge.autonomous_execution.dependency_graph import (
    evaluate_dependencies,
    validate_dependency_graph,
)
from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_runtime.models import MissionStep


def step(
    step_id: str,
    sequence: int,
    depends_on: tuple[str, ...] = (),
) -> MissionStep:
    return MissionStep(
        step_id=step_id,
        plan_id="plan-1",
        sequence=sequence,
        title=step_id,
        description=f"Execute {step_id}.",
        action_kind="read_file",
        depends_on=depends_on,
    )


def test_dependency_evaluation_detects_missing_steps() -> None:
    result = evaluate_dependencies(
        step("step-2", 2, ("step-1",)),
        completed_step_ids=frozenset(),
    )

    assert not result.satisfied
    assert result.missing_dependencies == ("step-1",)


def test_dependency_cycle_is_rejected() -> None:
    with pytest.raises(ExecutionContractError):
        validate_dependency_graph(
            (
                step("step-1", 1, ("step-2",)),
                step("step-2", 2, ("step-1",)),
            )
        )