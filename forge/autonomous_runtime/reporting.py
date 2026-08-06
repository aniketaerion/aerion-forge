"""Reporting helpers for autonomous-runtime missions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.transitions import allowed_targets


def mission_summary(
    mission: AutonomousMission,
) -> dict[str, Any]:
    """Return a deterministic, JSON-serializable mission summary."""
    return {
        "mission_id": mission.mission_id,
        "version": mission.version,
        "state": mission.state.value,
        "risk_class": mission.risk_class.name,
        "granted_authority": mission.granted_authority.name,
        "current_step_id": mission.current_step_id,
        "attempt_count": mission.attempt_count,
        "replan_count": mission.replan_count,
        "tool_call_count": mission.tool_call_count,
        "event_sequence": mission.event_sequence,
        "available_transitions": tuple(
            state.value
            for state in sorted(
                allowed_targets(mission.state),
                key=lambda item: item.value,
            )
        ),
        "outcome_id": mission.outcome_id,
        "updated_at": mission.updated_at.isoformat(),
    }


def render_mission_markdown(
    mission: AutonomousMission,
) -> str:
    """Render a concise mission report."""
    summary = mission_summary(mission)
    transitions = summary["available_transitions"]
    transition_text = (
        ", ".join(transitions)
        if transitions
        else "None"
    )

    return "\n".join(
        [
            "# Aerion Forge Autonomous Mission",
            "",
            f"- Mission ID: `{summary['mission_id']}`",
            f"- Version: `{summary['version']}`",
            f"- State: `{summary['state']}`",
            f"- Risk: `{summary['risk_class']}`",
            f"- Authority: `{summary['granted_authority']}`",
            f"- Current step: `{summary['current_step_id']}`",
            f"- Attempts: `{summary['attempt_count']}`",
            f"- Replans: `{summary['replan_count']}`",
            f"- Tool calls: `{summary['tool_call_count']}`",
            f"- Event sequence: `{summary['event_sequence']}`",
            f"- Available transitions: `{transition_text}`",
            f"- Outcome: `{summary['outcome_id']}`",
            f"- Updated: `{summary['updated_at']}`",
            "",
        ]
    )


def write_mission_report(
    mission: AutonomousMission,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown mission reports."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "MISSION_SUMMARY.json"
    markdown_path = destination / "MISSION_SUMMARY.md"

    json_path.write_text(
        json.dumps(
            mission_summary(mission),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_mission_markdown(mission),
        encoding="utf-8",
    )

    return json_path, markdown_path