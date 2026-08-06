"""Reporting helpers for autonomous execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_execution.models import StepExecutionRecord


def execution_summary(
    record: StepExecutionRecord,
) -> dict[str, Any]:
    """Return a deterministic JSON-serializable execution summary."""
    return {
        "execution_id": record.execution_id,
        "mission_id": record.mission_id,
        "step_id": record.step_id,
        "attempt_number": record.attempt_number,
        "lease_id": record.lease_id,
        "checkpoint_id": record.checkpoint_id,
        "state": record.state.value,
        "failure_class": (
            record.failure_class.value
            if record.failure_class is not None
            else None
        ),
        "invocation_count": len(record.invocation_results),
        "evidence_count": len(record.evidence_ids),
        "started_at": record.started_at.isoformat(),
        "completed_at": (
            record.completed_at.isoformat()
            if record.completed_at is not None
            else None
        ),
    }


def render_execution_markdown(
    record: StepExecutionRecord,
) -> str:
    """Render a concise execution report."""
    summary = execution_summary(record)

    return "\n".join(
        [
            "# Aerion Forge Autonomous Execution",
            "",
            f"- Execution ID: `{summary['execution_id']}`",
            f"- Mission ID: `{summary['mission_id']}`",
            f"- Step ID: `{summary['step_id']}`",
            f"- Attempt: `{summary['attempt_number']}`",
            f"- State: `{summary['state']}`",
            f"- Lease: `{summary['lease_id']}`",
            f"- Checkpoint: `{summary['checkpoint_id']}`",
            f"- Failure class: `{summary['failure_class']}`",
            f"- Invocations: `{summary['invocation_count']}`",
            f"- Evidence records: `{summary['evidence_count']}`",
            f"- Started: `{summary['started_at']}`",
            f"- Completed: `{summary['completed_at']}`",
            "",
        ]
    )


def write_execution_report(
    record: StepExecutionRecord,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown execution reports."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "EXECUTION_SUMMARY.json"
    markdown_path = destination / "EXECUTION_SUMMARY.md"

    json_path.write_text(
        json.dumps(
            execution_summary(record),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_execution_markdown(record),
        encoding="utf-8",
    )

    return json_path, markdown_path