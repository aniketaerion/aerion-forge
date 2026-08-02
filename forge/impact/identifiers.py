"""Deterministic identifiers for the Impact Decision Engine."""

import hashlib
import json
import re
from typing import Any

from forge.impact.errors import ImpactValidationError
from forge.impact.models import (
    ImpactAssessment,
    ImpactDecisionGeneration,
)

ASSESSMENT_ID_PATTERN = re.compile(r"impact-[0-9a-f]{20}")
FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}")
GENERATION_ID_PATTERN = re.compile(r"impact-generation-[0-9a-f]{20}")


def _canonical_json(value: Any) -> str:
    """Serialize a value into canonical deterministic JSON."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )


def canonical_hash(value: Any) -> str:
    """Return a deterministic SHA-256 hexadecimal hash."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_identity(value: str, field: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise ImpactValidationError(f"{field} cannot be blank during identifier generation.")

    return normalized


def normalize_assessment_title(title: str) -> str:
    """Normalize a title for stable assessment identity."""

    normalized = " ".join(title.strip().casefold().split())

    if not normalized:
        raise ImpactValidationError("Assessment title cannot be blank.")

    return normalized


def build_assessment_id(
    *,
    mission_id: str,
    task_set_fingerprint: str,
    title: str,
    sequence: int,
) -> str:
    """Build a stable impact-assessment identifier."""

    if sequence < 0:
        raise ImpactValidationError("Assessment sequence cannot be negative.")

    payload = {
        "mission_id": _require_identity(
            mission_id,
            "mission_id",
        ),
        "task_set_fingerprint": _require_identity(
            task_set_fingerprint,
            "task_set_fingerprint",
        ),
        "title": normalize_assessment_title(title),
        "sequence": sequence,
    }

    return f"impact-{canonical_hash(payload)[:20]}"


def assessment_fingerprint_payload(
    assessment: ImpactAssessment,
) -> dict[str, Any]:
    """Return canonical assessment content without its fingerprint."""

    payload = assessment.model_dump(mode="json")
    payload["assessment_fingerprint"] = ""
    payload["task_ids"] = sorted(payload["task_ids"])
    payload["findings"] = sorted(
        payload["findings"],
        key=lambda item: item["finding_id"],
    )
    payload["recommendation"]["options"] = sorted(
        payload["recommendation"]["options"],
        key=lambda item: item["option_id"],
    )
    payload["recommendation"]["approval_requirements"] = sorted(
        payload["recommendation"]["approval_requirements"],
        key=lambda item: item["requirement_id"],
    )
    payload["recommendation"]["validation_requirements"] = sorted(
        payload["recommendation"]["validation_requirements"],
        key=lambda item: item["requirement_id"],
    )
    payload["source_fingerprints"] = dict(sorted(payload["source_fingerprints"].items()))

    return payload


def build_assessment_fingerprint(
    assessment: ImpactAssessment,
) -> str:
    """Build the deterministic assessment fingerprint."""

    return canonical_hash(assessment_fingerprint_payload(assessment))


def build_generation_id(
    *,
    assessment_id: str,
    assessment_fingerprint: str,
    previous_generation_id: str | None = None,
) -> str:
    """Build deterministic generation identity."""

    payload = {
        "assessment_id": _require_identity(
            assessment_id,
            "assessment_id",
        ),
        "assessment_fingerprint": _require_identity(
            assessment_fingerprint,
            "assessment_fingerprint",
        ),
        "previous_generation_id": previous_generation_id,
    }

    return f"impact-generation-{canonical_hash(payload)[:20]}"


def validate_assessment_id(assessment_id: str) -> bool:
    """Return whether an assessment ID matches the public contract."""

    return bool(ASSESSMENT_ID_PATTERN.fullmatch(assessment_id))


def validate_generation_id(generation_id: str) -> bool:
    """Return whether a generation ID matches the public contract."""

    return bool(GENERATION_ID_PATTERN.fullmatch(generation_id))


def validate_fingerprint(fingerprint: str) -> bool:
    """Return whether a value is canonical SHA-256 hexadecimal."""

    return bool(FINGERPRINT_PATTERN.fullmatch(fingerprint))


def generation_fingerprint_payload(
    generation: ImpactDecisionGeneration,
) -> dict[str, Any]:
    """Return canonical generation content."""

    return generation.model_dump(mode="json")
