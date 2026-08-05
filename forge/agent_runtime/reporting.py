"""Reporting for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import json
from pathlib import Path

from forge.agent_runtime.errors import AgentRuntimeReportError
from forge.agent_runtime.models import AgentSession


def render_markdown(session: AgentSession) -> str:
    lines = [
        "# Unified Agent Runtime Report",
        "",
        f"- Session ID: `{session.session_id}`",
        f"- Status: `{session.status.value}`",
        f"- Objective: {session.request.objective.objective}",
        f"- Completed stages: `{len(session.stage_results)}`",
        "",
        "## Stages",
        "",
    ]

    for stage in session.stages:
        result = next(
            (
                item
                for item in session.stage_results
                if item.stage_id == stage.stage_id
            ),
            None,
        )

        lines.extend(
            [
                f"### {stage.sequence}. {stage.name}",
                "",
                f"- Capability: `{stage.capability.value}`",
                (
                    f"- Status: `{result.status.value}`"
                    if result is not None
                    else "- Status: `pending`"
                ),
                (
                    f"- Summary: {result.summary}"
                    if result is not None
                    else "- Summary: not executed"
                ),
                "",
            ]
        )

    return "\n".join(lines)


def write_report_bundle(
    session: AgentSession,
    destination: Path,
) -> dict[str, Path]:
    try:
        destination.mkdir(parents=True, exist_ok=True)

        json_path = destination / "AGENT_SESSION.json"
        markdown_path = destination / "AGENT_SESSION_REPORT.md"

        json_path.write_text(
            json.dumps(
                session.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown_path.write_text(
            render_markdown(session),
            encoding="utf-8",
        )
    except OSError as exc:
        raise AgentRuntimeReportError(
            f"unable to write agent runtime report: {exc}"
        ) from exc

    return {
        json_path.name: json_path,
        markdown_path.name: markdown_path,
    }