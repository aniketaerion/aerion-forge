"""Deterministic requirement extraction for M5.9 Package 1."""

from __future__ import annotations

import re

from forge.general_engineering.identifiers import (
    change_requirement_identifier,
)
from forge.general_engineering.models import ChangeRequirement
from forge.general_engineering.normalization import normalize_text

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
_CONJUNCTION_SPLIT = re.compile(
    r"\s+(?:and then|then|and)\s+",
    flags=re.IGNORECASE,
)


def _candidate_clauses(objective: str) -> tuple[str, ...]:
    normalized = normalize_text(objective)
    if not normalized:
        return ()

    clauses: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(normalized):
        for part in _CONJUNCTION_SPLIT.split(sentence):
            cleaned = part.strip(" .;")
            if cleaned:
                clauses.append(cleaned)

    return tuple(clauses)


def extract_change_requirements(
    *,
    objective: str,
    acceptance_criteria: tuple[str, ...] = (),
) -> tuple[ChangeRequirement, ...]:
    """Extract generic verifiable requirements from a normalized objective.

    Package 1 intentionally uses deterministic generic segmentation only.
    Provider-assisted semantic understanding is introduced later.
    """
    clauses = _candidate_clauses(objective)
    if not clauses:
        return ()

    result: list[ChangeRequirement] = []
    normalized_acceptance = tuple(
        item for item in (normalize_text(value) for value in acceptance_criteria) if item
    )

    for index, clause in enumerate(clauses, start=1):
        payload = {
            "index": index,
            "description": clause,
            "acceptance_criteria": normalized_acceptance,
        }
        result.append(
            ChangeRequirement(
                requirement_id=change_requirement_identifier(payload),
                description=clause,
                acceptance_criteria=normalized_acceptance,
            )
        )

    return tuple(result)