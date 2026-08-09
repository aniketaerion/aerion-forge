from pathlib import Path

import pytest

from forge.general_engineering.execution_policy import authorize_execution
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    FileChangePlan,
    GeneratedChangeSet,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)


def _plan_and_change_set(request_id: str) -> tuple[ChangePlan, GeneratedChangeSet]:
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update behavior",
    )
    plan = ChangePlan(
        plan_id="plan-1",
        request_id=request_id,
        objective="Update behavior",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="updated",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="validation-1",
            capabilities=("repository_tests",),
        ),
        expected_effect="updated",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path="src/service.py",
        source_fingerprint="fingerprint-1",
        proposed_content="VALUE = 2\n",
        rationale="implement",
        originating_requirement_id="requirement-1",
        evidence_ids=("evidence-1",),
    )
    return plan, GeneratedChangeSet(
        change_set_id="change-set-1",
        plan_id=plan.plan_id,
        operations=(operation,),
        evidence_ids=("evidence-1",),
    )


def test_apply_requires_code_change_authority(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update behavior",
        repository_root=tmp_path,
        allow_code_changes=False,
    )
    plan, change_set = _plan_and_change_set(request.request_id)

    with pytest.raises(PermissionError, match="does not authorize"):
        authorize_execution(
            request=request,
            plan=plan,
            change_set=change_set,
            approved=True,
            dry_run=False,
        )


def test_dry_run_allowed_without_code_change_authority(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update behavior",
        repository_root=tmp_path,
        allow_code_changes=False,
    )
    plan, change_set = _plan_and_change_set(request.request_id)

    decision = authorize_execution(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=False,
        dry_run=True,
    )

    assert decision.dry_run is True