"""Stable fingerprints for evaluated decision contexts."""

from __future__ import annotations

import hashlib
import json

from forge.autonomous_decision.models import DecisionContext


def decision_context_fingerprint(
    context: DecisionContext,
) -> str:
    """Return a stable fingerprint for one decision context."""
    payload = context.model_dump(mode="json")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()