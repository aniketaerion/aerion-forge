from pathlib import Path
from typing import cast

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EngineeringContext,
    EngineeringRequest,
    FileChangePlan,
    RelevantFile,
    RepositoryEvidence,
    ValidationOutcome,
    ValidationPlan,
)
from forge.general_engineering.protocols import EngineeringProvider
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
    EvidenceType,
    ValidationStatus,
)
from forge.general_engineering.validation_executor import (
    EngineeringValidationExecutor,
)
from forge.general_engineering.validation_repair_loop import (
    ValidationRepairLoop,
)


class PassingValidation(EngineeringValidationExecutor):
    def validate(
        self,
        *,
        request: EngineeringRequest,
        plan: ChangePlan,
    ) -> ValidationOutcome:
        del request

        return ValidationOutcome(
            outcome_id="ok",
            validation_plan_id=plan.validation_plan.validation_plan_id,
            status=ValidationStatus.PASSED,
            summary="passed",
        )


def test_loop_stops_immediately_when_validation_passes(
    tmp_path: Path,
) -> None:
    request = build_engineering_request(
        objective="change",
        repository_root=tmp_path,
    )

    requirement = ChangeRequirement(
        requirement_id="r1",
        description="change",
    )

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
        validation_plan=ValidationPlan(
            validation_plan_id="v1",
            capabilities=("repository_tests",),
        ),
        expected_effect="c",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("e",),
    )

    context = EngineeringContext(
        request_id=request.request_id,
        relevant_files=(
            RelevantFile(
                path="src/a.py",
                evidence_ids=("e",),
                rationale="g",
            ),
        ),
        evidence=(
            RepositoryEvidence(
                evidence_id="e",
                path="src/a.py",
                evidence_type=EvidenceType.FILE,
                rationale="g",
                relevance=1.0,
            ),
        ),
    )

    provider = cast(EngineeringProvider, object())

    result = ValidationRepairLoop(
        validation=PassingValidation(),
    ).run(
        provider=provider,
        request=request,
        context=context,
        plan=plan,
        approve_repairs=False,
    )

    assert result.completed is True
    assert result.repairs == ()
