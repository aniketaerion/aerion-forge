"""Deterministic identifiers for Mission Reporting."""

import hashlib
import json
from types import MappingProxyType
from typing import Any

from forge.mission_reporting.models import (
    MissionReport,
    MissionReportRisk,
    MissionReportSection,
    MissionTraceabilityItem,
)


def _canonical_json(payload: Any) -> str:
    """Return canonical JSON for deterministic hashing."""

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _digest(payload: Any) -> str:
    """Return a SHA-256 digest for canonical content."""

    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def build_report_id(
    *,
    mission_id: str,
    mission_fingerprint: str,
    task_set_fingerprint: str,
    assessment_id: str,
    assessment_fingerprint: str,
    engineering_memory_generation_id: str,
) -> str:
    """Build the deterministic Mission Report identifier."""

    digest = _digest(
        {
            "assessment_fingerprint": assessment_fingerprint,
            "assessment_id": assessment_id,
            "engineering_memory_generation_id": (engineering_memory_generation_id),
            "mission_fingerprint": mission_fingerprint,
            "mission_id": mission_id,
            "task_set_fingerprint": task_set_fingerprint,
        }
    )

    return f"mission-report-{digest[:20]}"


def build_section_id(
    *,
    report_id: str,
    section_type: str,
    title: str,
    source_ids: tuple[str, ...] = (),
) -> str:
    """Build a deterministic report-section identifier."""

    digest = _digest(
        {
            "report_id": report_id,
            "section_type": section_type,
            "source_ids": sorted(source_ids),
            "title": title.strip(),
        }
    )

    return f"mission-section-{digest[:20]}"


def build_risk_id(
    *,
    report_id: str,
    source_type: str,
    source_id: str,
    title: str,
) -> str:
    """Build a deterministic risk identifier."""

    digest = _digest(
        {
            "report_id": report_id,
            "source_id": source_id,
            "source_type": source_type,
            "title": title.strip(),
        }
    )

    return f"mission-risk-{digest[:20]}"


def build_traceability_id(
    *,
    report_id: str,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    relationship: str,
) -> str:
    """Build a deterministic traceability identifier."""

    digest = _digest(
        {
            "relationship": relationship.strip(),
            "report_id": report_id,
            "source_id": source_id,
            "source_type": source_type,
            "target_id": target_id,
            "target_type": target_type,
        }
    )

    return f"mission-trace-{digest[:20]}"


def build_report_fingerprint(
    report: MissionReport,
) -> str:
    """Build the canonical Mission Report fingerprint."""

    payload = report.model_dump(
        mode="json",
        exclude={"report_fingerprint"},
        fallback=lambda value: dict(value) if isinstance(value, MappingProxyType) else str(value),
    )

    return _digest(payload)


def build_section_fingerprint(
    section: MissionReportSection,
) -> str:
    """Build a deterministic section fingerprint."""

    return _digest(section.model_dump(mode="json"))


def build_risk_fingerprint(
    risk: MissionReportRisk,
) -> str:
    """Build a deterministic risk fingerprint."""

    return _digest(risk.model_dump(mode="json"))


def build_traceability_fingerprint(
    item: MissionTraceabilityItem,
) -> str:
    """Build a deterministic traceability fingerprint."""

    return _digest(item.model_dump(mode="json"))
