from pathlib import Path

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)


def test_change_plan_uses_only_grounded_targets(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update invoice approval and add tests",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(
        request
    ).specification
    source = ScannedRepositoryFile(
        path="src/invoice.py",
        size_bytes=10,
        suffix=".py",
        fingerprint="abc",
        content="pass\n",
    )
    context = build_engineering_context(
        request=request,
        files=(source,),
        symbol_map={source.path: ()},
        scores=(
            RelevanceScore(
                path=source.path,
                score=0.8,
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

    assert tuple(item.path for item in plan.file_changes) == ("src/invoice.py",)
    assert plan.evidence_ids == context.relevant_files[0].evidence_ids