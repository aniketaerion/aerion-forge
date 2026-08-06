"""Reporting helpers for autonomous decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_decision.decision_service import DecisionResult


def decision_summary(
    result: DecisionResult,
) -> dict[str, Any]:
    """Return a deterministic JSON-serializable decision summary."""
    record = result.record

    return {
        "decision_id": record.decision_id,
        "request_id": record.request_id,
        "context_id": record.context_id,
        "decision_kind": record.decision_kind.value,
        "disposition": record.disposition.value,
        "selected_candidate_id": record.selected_candidate_id,
        "alternative_candidate_ids": list(
            record.alternative_candidate_ids
        ),
        "rejected_candidate_ids": list(
            record.rejected_candidate_ids
        ),
        "assessment_ids": list(record.assessment_ids),
        "evidence_references": list(
            record.evidence_references
        ),
        "approval_required": record.approval_required,
        "confidence": record.confidence,
        "context_fingerprint": record.context_fingerprint,
        "rationale": record.rationale,
        "stop": (
            {
                "stop_id": result.stop.stop_id,
                "stop_kind": result.stop.stop_kind.value,
                "reason": result.stop.reason,
                "resumable": result.stop.resumable,
                "approval_required": (
                    result.stop.approval_required
                ),
            }
            if result.stop is not None
            else None
        ),
        "ranked_candidates": [
            {
                "rank": ranked.rank,
                "candidate_id": ranked.candidate.candidate_id,
                "action_kind": ranked.candidate.action_kind.value,
                "total_score": ranked.assessment.total_score,
                "risk_score": ranked.assessment.risk_score,
                "confidence_score": (
                    ranked.assessment.confidence_score
                ),
                "evidence_score": (
                    ranked.assessment.evidence_score
                ),
                "utility_score": (
                    ranked.assessment.utility_score
                ),
                "reversibility_score": (
                    ranked.assessment.reversibility_score
                ),
            }
            for ranked in result.selection.ranked
        ],
        "created_at": record.created_at.isoformat(),
    }


def render_decision_markdown(
    result: DecisionResult,
) -> str:
    """Render a concise human-readable decision report."""
    summary = decision_summary(result)

    lines = [
        "# Aerion Forge Autonomous Decision",
        "",
        f"- Decision ID: `{summary['decision_id']}`",
        f"- Request ID: `{summary['request_id']}`",
        f"- Context ID: `{summary['context_id']}`",
        f"- Kind: `{summary['decision_kind']}`",
        f"- Disposition: `{summary['disposition']}`",
        (
            "- Selected candidate: "
            f"`{summary['selected_candidate_id']}`"
        ),
        f"- Approval required: `{summary['approval_required']}`",
        f"- Confidence: `{summary['confidence']}`",
        f"- Context fingerprint: `{summary['context_fingerprint']}`",
        "",
        "## Rationale",
        "",
        str(summary["rationale"]),
        "",
        "## Ranked Candidates",
        "",
    ]

    ranked_candidates = summary["ranked_candidates"]

    if ranked_candidates:
        for ranked in ranked_candidates:
            lines.append(
                f"{ranked['rank']}. "
                f"`{ranked['candidate_id']}` — "
                f"{ranked['action_kind']} — "
                f"score `{ranked['total_score']}`"
            )
    else:
        lines.append("_No acceptable candidates._")

    if summary["stop"] is not None:
        stop = summary["stop"]
        lines.extend(
            [
                "",
                "## Stop Decision",
                "",
                f"- Kind: `{stop['stop_kind']}`",
                f"- Resumable: `{stop['resumable']}`",
                f"- Reason: {stop['reason']}",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def write_decision_report(
    result: DecisionResult,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown reports for one decision."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "AUTONOMOUS_DECISION.json"
    markdown_path = destination / "AUTONOMOUS_DECISION.md"

    json_path.write_text(
        json.dumps(
            decision_summary(result),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_decision_markdown(result),
        encoding="utf-8",
    )

    return json_path, markdown_path