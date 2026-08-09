from pathlib import Path

import pytest

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.edit_proposal_validator import (
    validate_generated_change_set,
)
from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import EditOperation, GeneratedChangeSet
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)
from forge.general_engineering.states import EditOperationType


def test_validator_rejects_stale_fingerprint(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update invoice approval",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(
        request
    ).specification
    file = ScannedRepositoryFile(
        path="src/invoice.py",
        size_bytes=5,
        suffix=".py",
        fingerprint="current",
        content="pass\n",
    )
    context = build_engineering_context(
        request=request,
        files=(file,),
        symbol_map={file.path: ()},
        scores=(
            RelevanceScore(
                path=file.path,
                score=1.0,
                matched_terms=("invoice",),
                matched_symbols=(),
            ),
        ),
    )
    plan = build_change_plan(
        request=request,
        specification=specification,
        context=context,
    )
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path=file.path,
        source_fingerprint="stale",
        proposed_content="value = 2\n",
        rationale="Implement requirement",
        originating_requirement_id=plan.requirements[0].requirement_id,
        evidence_ids=plan.evidence_ids,
    )
    change_set = GeneratedChangeSet(
        change_set_id="change-set-1",
        plan_id=plan.plan_id,
        operations=(operation,),
        evidence_ids=plan.evidence_ids,
    )

    with pytest.raises(EngineeringContractError, match="fingerprint mismatch"):
        validate_generated_change_set(
            request=request,
            context=context,
            plan=plan,
            change_set=change_set,
        )