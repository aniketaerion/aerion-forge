from pathlib import Path

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EngineeringContext,
    FileChangePlan,
    RelevantFile,
    RepairProposal,
    RepositoryEvidence,
    ValidationPlan,
)
from forge.general_engineering.repair_plan import build_repair_change_plan
from forge.general_engineering.states import EditOperationType, EngineeringRisk, EvidenceType


def test_repair_plan_refreshes_evidence(tmp_path: Path) -> None:
    requirement = ChangeRequirement(requirement_id="r1", description="change")
    original = ChangePlan(
        plan_id="p1",
        request_id="req",
        objective="change",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/a.py",
                rationale="old",
                evidence_ids=("old",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="c",
            ),
        ),
        validation_plan=ValidationPlan(validation_plan_id="v1", capabilities=("repository_tests",)),
        expected_effect="c",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("old",),
    )
    context = EngineeringContext(
        request_id="req",
        relevant_files=(RelevantFile(path="src/a.py", evidence_ids=("new",), rationale="fresh"),),
        evidence=(
            RepositoryEvidence(
                evidence_id="new",
                path="src/a.py",
                evidence_type=EvidenceType.FILE,
                rationale="fresh",
                relevance=1.0,
                fingerprint="fp",
            ),
        ),
    )
    proposal = RepairProposal(
        repair_id="rp1",
        request_id="req",
        attempt_number=1,
        diagnosis="repair",
        target_paths=("src/a.py",),
        validation_outcome_id="o1",
    )

    repaired = build_repair_change_plan(
        original_plan=original, refreshed_context=context, proposal=proposal
    )
    assert repaired.plan_id != original.plan_id
    assert repaired.evidence_ids == ("new",)
