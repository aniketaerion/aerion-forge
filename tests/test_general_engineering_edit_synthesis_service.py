from pathlib import Path

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.edit_synthesis_service import (
    EngineeringEditSynthesisService,
)
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EditOperation,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)
from forge.general_engineering.states import EditOperationType


class FakeEngineeringProvider:
    def understand_request(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
    ) -> ChangeSpecification:
        raise NotImplementedError

    def propose_change_plan(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        specification: ChangeSpecification,
    ) -> ChangePlan:
        raise NotImplementedError

    def synthesize_edits(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
    ) -> GeneratedChangeSet:
        evidence = context.evidence[0]
        operation = EditOperation(
            operation_id="operation-1",
            operation_type=EditOperationType.REPLACE,
            target_path=plan.file_changes[0].path,
            source_fingerprint=evidence.fingerprint,
            proposed_content="def schedule_delivery():\n    return True\n",
            rationale="Implement approved requirement",
            originating_requirement_id=plan.requirements[0].requirement_id,
            evidence_ids=plan.evidence_ids,
        )
        return GeneratedChangeSet(
            change_set_id="provider-change-set",
            plan_id=plan.plan_id,
            operations=(operation,),
            evidence_ids=plan.evidence_ids,
        )

    def propose_repair(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
        validation_outcome: ValidationOutcome,
        attempt_number: int,
    ) -> RepairProposal:
        raise NotImplementedError


def test_service_accepts_safe_provider_edit_proposal(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update delivery scheduling",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(
        request
    ).specification
    file = ScannedRepositoryFile(
        path="src/delivery.py",
        size_bytes=20,
        suffix=".py",
        fingerprint="fingerprint-1",
        content="def schedule_delivery():\n    return False\n",
    )
    context = build_engineering_context(
        request=request,
        files=(file,),
        symbol_map={file.path: ()},
        scores=(
            RelevanceScore(
                path=file.path,
                score=1.0,
                matched_terms=("delivery",),
                matched_symbols=(),
            ),
        ),
    )
    plan = build_change_plan(
        request=request,
        specification=specification,
        context=context,
    )

    result = EngineeringEditSynthesisService().synthesize(
        provider=FakeEngineeringProvider(),
        request=request,
        context=context,
        plan=plan,
    )

    assert result.operation_count == 1
    assert result.affected_paths == ("src/delivery.py",)
    assert result.change_set.operations[0].proposed_content is not None