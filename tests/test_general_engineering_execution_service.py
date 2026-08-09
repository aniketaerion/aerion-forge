from pathlib import Path

from forge.general_engineering.execution_service import EngineeringExecutionService
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    EngineeringRequest,
    FileChangePlan,
    GeneratedChangeSet,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)
from forge.safe_code_editing.identifiers import source_fingerprint


def _fixture(
    tmp_path: Path,
) -> tuple[Path, EngineeringRequest, ChangePlan, GeneratedChangeSet]:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "service.py"
    original = "VALUE = 1\n"
    target.write_text(original, encoding="utf-8")
    fingerprint = source_fingerprint(target.read_bytes().decode("utf-8"))

    request = build_engineering_request(
        objective="Update service value",
        repository_root=tmp_path,
        allow_code_changes=True,
    )
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update service value",
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
    return target, request, plan, change_set


def test_execution_service_dry_run_does_not_mutate(tmp_path: Path) -> None:
    target, request, plan, change_set = _fixture(tmp_path)

    result = EngineeringExecutionService().execute(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=False,
        dry_run=True,
    )

    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"
    assert result.report.dry_run is True


def test_execution_service_apply_mutates_through_safe_editing(tmp_path: Path) -> None:
    target, request, plan, change_set = _fixture(tmp_path)

    result = EngineeringExecutionService().execute(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=True,
        dry_run=False,
    )

    assert target.read_text(encoding="utf-8") == "VALUE = 2\n"
    assert result.report.approved is True