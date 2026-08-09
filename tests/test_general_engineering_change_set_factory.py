from forge.general_engineering.change_set_factory import (
    build_generated_change_set,
)
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    FileChangePlan,
    ValidationPlan,
)
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)


def _plan() -> ChangePlan:
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update behavior",
    )
    return ChangePlan(
        plan_id="plan-1",
        request_id="request-1",
        objective="Update behavior",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="update behavior",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="validation-1",
            capabilities=("repository_tests",),
        ),
        expected_effect="update behavior",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )


def test_change_set_factory_is_deterministic() -> None:
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path="src/service.py",
        source_fingerprint="fingerprint-1",
        proposed_content="VALUE = 2\n",
        rationale="Implement requirement",
        originating_requirement_id="requirement-1",
        evidence_ids=("evidence-1",),
    )

    first = build_generated_change_set(plan=_plan(), operations=(operation,))
    second = build_generated_change_set(plan=_plan(), operations=(operation,))

    assert first.change_set_id == second.change_set_id
    assert first.operations == second.operations