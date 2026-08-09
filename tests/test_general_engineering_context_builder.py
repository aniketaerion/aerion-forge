from pathlib import Path

from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request


def test_context_contains_traceable_repository_evidence(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update invoice approval",
        repository_root=tmp_path,
    )
    file = ScannedRepositoryFile(
        path="src/invoice.py",
        size_bytes=10,
        suffix=".py",
        fingerprint="abc",
        content="pass\n",
    )
    score = RelevanceScore(
        path=file.path,
        score=0.8,
        matched_terms=("invoice",),
        matched_symbols=(),
    )
    context = build_engineering_context(
        request=request,
        files=(file,),
        symbol_map={file.path: ()},
        scores=(score,),
    )
    assert context.relevant_files[0].path == "src/invoice.py"
    assert context.evidence[0].fingerprint == "abc"