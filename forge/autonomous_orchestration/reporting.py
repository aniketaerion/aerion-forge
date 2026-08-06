"""Reporting helpers for autonomous mission orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_orchestration.models import MissionSession


def orchestration_summary(
    session: MissionSession,
) -> dict[str, Any]:
    """Return a deterministic JSON-serializable session summary."""
    return {
        "session_id": session.session_id,
        "mission_id": session.mission_id,
        "plan_id": session.plan_id,
        "plan_version": session.plan_version,
        "repository_root": session.repository_root,
        "state": session.state.value,
        "current_step_id": session.current_step_id,
        "completed_step_ids": list(session.completed_step_ids),
        "failed_step_ids": list(session.failed_step_ids),
        "cycle_count": session.cycle_count,
        "execution_count": session.execution_count,
        "retry_count": session.retry_count,
        "rollback_count": session.rollback_count,
        "replan_count": session.replan_count,
        "checkpoint_id": session.checkpoint_id,
        "stop_reason": session.stop_reason,
        "version": session.version,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def render_orchestration_markdown(
    session: MissionSession,
) -> str:
    """Render a concise orchestration report."""
    summary = orchestration_summary(session)

    return "\n".join(
        [
            "# Aerion Forge Autonomous Mission Orchestration",
            "",
            f"- Session ID: `{summary['session_id']}`",
            f"- Mission ID: `{summary['mission_id']}`",
            f"- Plan ID: `{summary['plan_id']}`",
            f"- Plan version: `{summary['plan_version']}`",
            f"- Repository: `{summary['repository_root']}`",
            f"- State: `{summary['state']}`",
            f"- Current step: `{summary['current_step_id']}`",
            f"- Completed steps: `{len(summary['completed_step_ids'])}`",
            f"- Failed steps: `{len(summary['failed_step_ids'])}`",
            f"- Cycles: `{summary['cycle_count']}`",
            f"- Executions: `{summary['execution_count']}`",
            f"- Retries: `{summary['retry_count']}`",
            f"- Rollbacks: `{summary['rollback_count']}`",
            f"- Replans: `{summary['replan_count']}`",
            f"- Checkpoint: `{summary['checkpoint_id']}`",
            f"- Stop reason: `{summary['stop_reason']}`",
            f"- Version: `{summary['version']}`",
            "",
        ]
    )


def write_orchestration_report(
    session: MissionSession,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown orchestration reports."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "ORCHESTRATION_SUMMARY.json"
    markdown_path = destination / "ORCHESTRATION_SUMMARY.md"

    json_path.write_text(
        json.dumps(
            orchestration_summary(session),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_orchestration_markdown(session),
        encoding="utf-8",
    )

    return json_path, markdown_path