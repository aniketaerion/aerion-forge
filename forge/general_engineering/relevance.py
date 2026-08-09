"""Deterministic relevance scoring for repository grounding."""

from __future__ import annotations

import re
from dataclasses import dataclass

from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.symbol_discovery import DiscoveredSymbol

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_STOP = frozenset({
    "add", "and", "the", "for", "with", "from", "into", "when", "then",
    "create", "update", "change", "modify", "implement", "make", "ensure",
})


@dataclass(frozen=True)
class RelevanceScore:
    path: str
    score: float
    matched_terms: tuple[str, ...]
    matched_symbols: tuple[str, ...]


def objective_terms(objective: str) -> tuple[str, ...]:
    terms = {token.casefold() for token in _TOKEN.findall(objective)}
    return tuple(sorted(term for term in terms if term not in _STOP))


def score_file_relevance(
    objective: str,
    file: ScannedRepositoryFile,
    symbols: tuple[DiscoveredSymbol, ...],
) -> RelevanceScore:
    terms = objective_terms(objective)
    path_text = file.path.casefold()
    content_text = file.content.casefold()
    symbol_map = {symbol.name.casefold(): symbol.name for symbol in symbols}

    matched_terms: list[str] = []
    matched_symbols: list[str] = []
    score = 0.0

    for term in terms:
        matched = False
        if term in path_text:
            score += 4.0
            matched = True
        if term in symbol_map:
            score += 5.0
            matched_symbols.append(symbol_map[term])
            matched = True
        occurrences = content_text.count(term)
        if occurrences:
            score += min(3.0, occurrences * 0.5)
            matched = True
        if matched:
            matched_terms.append(term)

    if (
        file.path.casefold().startswith("tests/")
        or "/test" in file.path.casefold()
    ) and any(term in content_text for term in terms):
        score += 1.0

    normalized = min(1.0, score / 12.0)
    return RelevanceScore(
        path=file.path,
        score=normalized,
        matched_terms=tuple(sorted(set(matched_terms))),
        matched_symbols=tuple(sorted(set(matched_symbols))),
    )