from pathlib import Path

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.edit_synthesis_policy import (
    build_edit_synthesis_decision,
)
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)
from forge.general_engineering.states import EditOperationType


def test_edit_synthesis_decision_is_bounded_to_plan(tmp_path: Path) -> None:
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
        fingerprint="abc",
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

    decision = build_edit_synthesis_decision(request, plan)

    assert decision.allowed_paths == ("src/invoice.py",)
    assert decision.allowed_operation_types == (EditOperationType.REPLACE,)