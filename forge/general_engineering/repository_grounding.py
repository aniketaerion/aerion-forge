"""Repository-grounding orchestration for M5.9 Package 2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.errors import EngineeringEvidenceError
from forge.general_engineering.models import EngineeringContext, EngineeringRequest
from forge.general_engineering.relevance import score_file_relevance
from forge.general_engineering.repository_scanner import scan_repository
from forge.general_engineering.symbol_discovery import discover_symbols


@dataclass(frozen=True)
class RepositoryGroundingResult:
    context: EngineeringContext
    scanned_file_count: int
    relevant_file_count: int


class RepositoryGroundingService:
    """Create read-only, evidence-backed EngineeringContext."""

    def ground(self, request: EngineeringRequest) -> RepositoryGroundingResult:
        files = scan_repository(request.repository_root)
        if not files:
            raise EngineeringEvidenceError("Repository scan produced no readable files.")

        symbol_map = {file.path: discover_symbols(file) for file in files}
        scores = tuple(
            score_file_relevance(request.objective, file, symbol_map[file.path])
            for file in files
        )
        context = build_engineering_context(
            request=request,
            files=files,
            symbol_map=symbol_map,
            scores=scores,
        )
        if not context.relevant_files:
            raise EngineeringEvidenceError(
                "Repository grounding found no evidence-backed relevant files."
            )
        return RepositoryGroundingResult(
            context=context,
            scanned_file_count=len(files),
            relevant_file_count=len(context.relevant_files),
        )


repository_grounding_service = RepositoryGroundingService()