from pathlib import Path

import pytest

from forge.general_engineering.errors import EngineeringRepairError
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    FileChangePlan,
    RepairProposal,
    ValidationOutcome,
    ValidationPlan,
)
from forge.general_engineering.repair_policy import validate_repair_proposal
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import EditOperationType, EngineeringRisk, ValidationStatus


def test_repair_cannot_expand_plan_scope(tmp_path: Path) -> None:
    request = build_engineering_request(objective="change", repository_root=tmp_path)
    requirement = ChangeRequirement(requirement_id="r1", description="change")
    plan = ChangePlan(
        plan_id="p1",
        request_id=request.request_id,
        objective="change",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/a.py",
                rationale="g",
                evidence_ids=("e",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="c",
            ),
        ),
        validation_plan=ValidationPlan(validation_plan_id="v1", capabilities=("repository_tests",)),
        expected_effect="change",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("e",),
    )
    outcome = ValidationOutcome(
        outcome_id="o1",
        validation_plan_id="v1",
        status=ValidationStatus.FAILED,
        summary="failed",
        failures=("x",),
    )
    proposal = RepairProposal(
        repair_id="rp1",
        request_id=request.request_id,
        attempt_number=1,
        diagnosis="fix",
        target_paths=("src/b.py",),
        validation_outcome_id="o1",
    )

    with pytest.raises(EngineeringRepairError, match="expands"):
        validate_repair_proposal(
            request=request,
            plan=plan,
            validation_outcome=outcome,
            proposal=proposal,
            attempt_number=1,
        )
