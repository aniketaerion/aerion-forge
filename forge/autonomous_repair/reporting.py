"""Reporting for M3.5 Autonomous Repair."""

from __future__ import annotations

import json
from pathlib import Path

from forge.autonomous_repair.errors import RepairPersistenceError
from forge.autonomous_repair.models import RepairExecutionReport


def render_markdown(report: RepairExecutionReport) -> str:
    """Render a compact human-readable repair report."""
    lines = [
        "# Autonomous Repair Report",
        "",
        f"- Session ID: `{report.session_id}`",
        f"- Status: `{report.status.value}`",
        f"- Succeeded: `{'yes' if report.succeeded else 'no'}`",
        f"- Attempts: `{len(report.attempts)}`",
        "",
        "## Attempts",
        "",
    ]
    for attempt in report.attempts:
        lines.extend(
            [
                f"### Attempt {attempt.attempt_number}",
                "",
                f"- Proposal: `{attempt.proposal_id}`",
                f"- Status: `{attempt.status.value}`",
                f"- Errors: `{len(attempt.errors)}`",
                "",
            ]
        )
    if report.messages:
        lines.extend(["## Messages", ""])
        lines.extend(f"- {message}" for message in report.messages)
        lines.append("")
    return "\n".join(lines)


def write_report_bundle(
    report: RepairExecutionReport,
    destination: Path,
) -> dict[str, Path]:
    """Persist JSON and Markdown report evidence."""
    try:
        destination.mkdir(parents=True, exist_ok=True)
        json_path = destination / "AUTONOMOUS_REPAIR_SESSION.json"
        markdown_path = destination / "AUTONOMOUS_REPAIR_REPORT.md"
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(render_markdown(report), encoding="utf-8")
    except OSError as exc:
        raise RepairPersistenceError(
            f"unable to persist autonomous repair report: {exc}"
        ) from exc
    return {
        json_path.name: json_path,
        markdown_path.name: markdown_path,
    }