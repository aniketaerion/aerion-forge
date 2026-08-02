"""Deterministic engineering-request normalization."""

import re

from forge.planning.errors import MissionNormalizationError
from forge.planning.models import (
    MissionRequestCategory,
    NormalizedEngineeringRequest,
    PlanningConfidence,
)

_ALIASES = {"integration": "integrate", "documentation": "document", "analysis": "analyze"}
_CATEGORIES = {item.value: item for item in MissionRequestCategory if item.value != "unknown"}
_STOP = {"a", "an", "the", "for", "to", "of", "and", "please"}


def normalize_request(raw_request: str) -> NormalizedEngineeringRequest:
    raw = raw_request.strip()
    if not raw:
        raise MissionNormalizationError("Engineering request cannot be empty.")
    normalized = re.sub(r"\s+", " ", raw.casefold())
    normalized = re.sub(r"[!?;,:\s]+$", "", normalized)
    words = re.findall(r"[a-z0-9][a-z0-9+.#_-]*", normalized)
    action = _ALIASES.get(words[0], words[0]) if words else "unknown"
    category = _CATEGORIES.get(action, MissionRequestCategory.UNKNOWN)
    primary_object = " ".join(words[1:]).strip()
    terms = tuple(sorted({word for word in words[1:] if word not in _STOP and len(word) > 1}))
    ambiguity = (
        PlanningConfidence.LOW
        if category is MissionRequestCategory.UNKNOWN or not primary_object
        else PlanningConfidence.MEDIUM
        if len(terms) < 2
        else PlanningConfidence.HIGH
    )
    domain = " ".join(word for word in words[1:] if word not in {"module", "system", "service"})
    return NormalizedEngineeringRequest(
        raw_request=raw,
        normalized_request=normalized,
        primary_action=action,
        primary_object=primary_object,
        category=category,
        target_domain_phrase=domain or None,
        ambiguity=ambiguity,
        terms=terms,
    )

