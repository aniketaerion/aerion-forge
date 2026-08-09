from pathlib import Path

import pytest

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    FileChangePlan,
    RelevantFile,
    RepositoryEvidence,
    ValidationPlan,
)
from forge.general_engineering.plan_validator import validate_change_plan
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import EngineeringRequestUnderstandingService
from forge.general_engineering.states import EditOperationType, EngineeringRisk, EvidenceType


def test_validator_rejects_ungrounded_target(tmp_path: Path) -> None:
    request = build_engineering_request(objective="Update service", repository_root=tmp_path)
    specification = EngineeringRequestUnderstandingService().understand(request).specification
    evidence = RepositoryEvidence(
        evidence_id="evidence-1",
        path="src/service.py",
        evidence_type=EvidenceType.FILE,
        rationale="grounded",
        relevance=1.0,
    )
    context = EngineeringContext(
        request_id=request.request_id,
        relevant_files=(
            RelevantFile(
                path="src/service.py",
                evidence_ids=("evidence-1",),
                rationale="grounded",
            ),
        ),
        evidence=(evidence,),
    )
    plan = ChangePlan(
        plan_id="plan-1",
        request_id=request.request_id,
        objective=request.objective,
        requirements=specification.requirements,
        file_changes=(
            FileChangePlan(
                path="src/other.py",
                rationale="not grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="change",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="validation-1",
            capabilities=("repository_tests",),
        ),
        expected_effect="change",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )

    with pytest.raises(EngineeringContractError, match="not justified"):
        validate_change_plan(
            request=request,
            specification=specification,
            context=context,
            plan=plan,
        )