"""Fingerprint and evidence helpers for M5.9 Package 4."""

from __future__ import annotations

from forge.general_engineering.models import EngineeringContext


def evidence_fingerprint_map(
    context: EngineeringContext,
) -> dict[str, str]:
    """Return one current source fingerprint per grounded repository path."""
    result: dict[str, str] = {}

    for evidence in context.evidence:
        if evidence.fingerprint:
            result[evidence.path] = evidence.fingerprint

    return result


def context_evidence_ids(context: EngineeringContext) -> frozenset[str]:
    return frozenset(item.evidence_id for item in context.evidence)