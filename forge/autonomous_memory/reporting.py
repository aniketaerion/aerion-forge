"""Reporting for autonomous memory and learning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryMatch,
    MemoryRecord,
)


@dataclass(frozen=True, slots=True)
class MemoryReport:
    """Serializable memory report."""

    records: tuple[MemoryRecord, ...]
    matches: tuple[MemoryMatch, ...]
    learning: tuple[LearningRecord, ...]


def memory_report_payload(
    report: MemoryReport,
) -> dict[str, Any]:
    """Return deterministic JSON-ready report payload."""
    return {
        "record_count": len(report.records),
        "match_count": len(report.matches),
        "learning_count": len(report.learning),
        "records": [
            record.model_dump(mode="json")
            for record in sorted(
                report.records,
                key=lambda item: item.memory_id,
            )
        ],
        "matches": [
            match.model_dump(mode="json")
            for match in sorted(
                report.matches,
                key=lambda item: (
                    -item.total_score,
                    item.memory_id,
                ),
            )
        ],
        "learning": [
            learning.model_dump(mode="json")
            for learning in sorted(
                report.learning,
                key=lambda item: item.learning_id,
            )
        ],
    }


def memory_report_json(
    report: MemoryReport,
) -> str:
    """Render memory report as JSON."""
    return json.dumps(
        memory_report_payload(report),
        indent=2,
        sort_keys=True,
    )


def memory_report_markdown(
    report: MemoryReport,
) -> str:
    """Render memory report as Markdown."""
    lines = [
        "# Autonomous Memory Report",
        "",
        f"- Records: {len(report.records)}",
        f"- Matches: {len(report.matches)}",
        f"- Learning records: {len(report.learning)}",
        "",
        "## Memory Records",
        "",
    ]

    for record in sorted(
        report.records,
        key=lambda item: item.memory_id,
    ):
        lines.extend(
            [
                f"### {record.memory_id}",
                "",
                f"- Kind: `{record.memory_kind.value}`",
                f"- Status: `{record.status.value}`",
                f"- Confidence: `{record.confidence:.3f}`",
                f"- Repository: `{record.repository_scope}`",
                "",
                record.statement,
                "",
            ]
        )

    lines.extend(["## Learning Records", ""])

    for learning in sorted(
        report.learning,
        key=lambda item: item.learning_id,
    ):
        lines.extend(
            [
                f"### {learning.learning_id}",
                "",
                f"- Successes: `{learning.success_count}`",
                f"- Failures: `{learning.failure_count}`",
                f"- Confidence: `{learning.confidence:.3f}`",
                "",
                learning.lesson,
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"