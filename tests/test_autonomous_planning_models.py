import pytest

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningPlan,
    PlanningRequest,
    PlanningStep,
    PlanningValidationFinding,
    PlanningValidationResult,
)
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    DependencyKind,
    PlanningIntent,
    PlanningRisk,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=f"Step {sequence}",
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_request_rejects_empty_objective() -> None:
    with pytest.raises(PlanningContractError):
        PlanningRequest(
            request_id="request-1",
            objective="",
            repository_root="repository",
            intent=PlanningIntent.INVESTIGATE,
            created_by="Aerion",
        )


def test_plan_accepts_ordered_steps() -> None:
    result = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Repository-grounded plan.",
        steps=(step("step-1", 1), step("step-2", 2)),
        dependencies=(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="step-2",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Step two requires step one.",
            ),
        ),
    )
    assert len(result.steps) == 2


def test_plan_rejects_unknown_dependency() -> None:
    with pytest.raises(PlanningContractError):
        PlanningPlan(
            plan_id="plan-1",
            request_id="request-1",
            summary="Invalid plan.",
            steps=(step("step-1", 1),),
            dependencies=(
                PlanningDependency(
                    dependency_id="dependency-1",
                    source_step_id="missing",
                    target_step_id="step-1",
                    kind=DependencyKind.REQUIRES,
                    rationale="Invalid reference.",
                ),
            ),
        )


def test_destructive_step_requires_approval() -> None:
    with pytest.raises(PlanningContractError):
        PlanningStep(
            step_id="step-1",
            sequence=1,
            name="Delete",
            description="Delete generated repository artifacts.",
            kind=StepKind.CODE_CHANGE,
            destructive=True,
            approval_requirement=ApprovalRequirement.NONE,
        )


def test_valid_result_rejects_blocking_finding() -> None:
    finding = PlanningValidationFinding(
        finding_id="finding-1",
        severity=PlanningRisk.HIGH,
        code="BLOCKED",
        message="Blocking issue.",
        blocking=True,
    )
    with pytest.raises(PlanningContractError):
        PlanningValidationResult(
            plan_id="plan-1",
            valid=True,
            findings=(finding,),
        )