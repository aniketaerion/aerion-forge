"""Build EngineeringContext from repository-grounding evidence."""

from __future__ import annotations

from forge.general_engineering.identifiers import repository_evidence_identifier
from forge.general_engineering.models import (
    EngineeringContext,
    EngineeringRequest,
    RelevantFile,
    RelevantSymbol,
    RepositoryEvidence,
)
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.states import EvidenceType
from forge.general_engineering.symbol_discovery import DiscoveredSymbol


def build_engineering_context(
    *,
    request: EngineeringRequest,
    files: tuple[ScannedRepositoryFile, ...],
    symbol_map: dict[str, tuple[DiscoveredSymbol, ...]],
    scores: tuple[RelevanceScore, ...],
    minimum_relevance: float = 0.10,
    max_relevant_files: int = 20,
) -> EngineeringContext:
    by_path = {item.path: item for item in files}
    selected_scores = [item for item in scores if item.score >= minimum_relevance]
    selected_scores.sort(key=lambda item: (-item.score, item.path))
    selected_scores = selected_scores[:max_relevant_files]

    evidence: list[RepositoryEvidence] = []
    relevant_files: list[RelevantFile] = []

    for score in selected_scores:
        file = by_path[score.path]
        rationale = (
            f"Matched objective terms: {', '.join(score.matched_terms) or 'none'}; "
            f"relevance={score.score:.3f}."
        )
        evidence_payload = {
            "request_id": request.request_id,
            "path": file.path,
            "fingerprint": file.fingerprint,
            "score": score.score,
            "terms": score.matched_terms,
        }
        evidence_id = repository_evidence_identifier(evidence_payload)
        evidence.append(
            RepositoryEvidence(
                evidence_id=evidence_id,
                path=file.path,
                evidence_type=EvidenceType.FILE,
                rationale=rationale,
                relevance=score.score,
                fingerprint=file.fingerprint,
                provenance=("repository_scan", "deterministic_relevance"),
            )
        )

        relevant_symbols: list[RelevantSymbol] = []
        for symbol in symbol_map.get(file.path, ()):
            if symbol.name in score.matched_symbols or any(
                term in symbol.name.casefold() for term in score.matched_terms
            ):
                relevant_symbols.append(
                    RelevantSymbol(
                        name=symbol.name,
                        kind=symbol.kind,
                        path=file.path,
                        evidence_ids=(evidence_id,),
                        rationale="Symbol name matches objective-grounding terms.",
                    )
                )

        relevant_files.append(
            RelevantFile(
                path=file.path,
                evidence_ids=(evidence_id,),
                rationale=rationale,
                symbols=tuple(relevant_symbols),
            )
        )

    return EngineeringContext(
        request_id=request.request_id,
        relevant_files=tuple(relevant_files),
        evidence=tuple(evidence),
    )