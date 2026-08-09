import hashlib
from pathlib import Path

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    FileChangePlan,
    GeneratedChangeSet,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.safe_edit_adapter import build_safe_edit_request
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)


def test_adapter_builds_safe_code_editing_request(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "service.py"
    original = "VALUE = 1\n"
    target.write_text(original, encoding="utf-8")
    fingerprint = hashlib.sha256(original.encode("utf-8")).hexdigest()

    request = build_engineering_request(
        objective="Update behavior",
        repository_root=tmp_path,
        allow_code_changes=True,
    )
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update behavior",
    )
    plan = ChangePlan(
        plan_id="plan-1",
        request_id=request.request_id,
        objective=request.objective,
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
        source_fingerprint=fingerprint,
        proposed_content="VALUE = 2\n",
        rationale="implement",
        originating_requirement_id="requirement-1",
        evidence_ids=("evidence-1",),
    )
    change_set = GeneratedChangeSet(
        change_set_id="change-set-1",
        plan_id=plan.plan_id,
        operations=(operation,),
        evidence_ids=("evidence-1",),
    )

    safe = build_safe_edit_request(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=True,
        dry_run=False,
    )

    assert safe.file_plans[0].relative_path == "src/service.py"
    assert safe.file_plans[0].operations[0].replacement_text == "VALUE = 2\n"