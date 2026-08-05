"""Mission reporting for M3.6 Mission Orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from forge.mission_orchestration.errors import MissionReportError
from forge.mission_orchestration.identifiers import (
    orchestration_report_identifier,
)
from forge.mission_orchestration.models import (
    MissionExecution,
    MissionReport,
    StageStatus,
)


def build_mission_report(
    execution: MissionExecution,
    *,
    started_at: datetime,
    completed_at: datetime | None = None,
    messages: tuple[str, ...] = (),
) -> MissionReport:
    """Build one deterministic final mission report."""
    artifacts = tuple(
        artifact
        for run in execution.stage_runs
        if run.result is not None
        for artifact in run.result.output_artifacts
    )

    report_id = orchestration_report_identifier(
        {
            "mission_id": execution.request.mission_id,
            "workflow_id": execution.workflow.workflow_id,
            "status": execution.status.value,
            "stage_run_ids": [
                run.stage_run_id for run in execution.stage_runs
            ],
            "output_artifacts": artifacts,
        }
    )

    return MissionReport(
        report_id=report_id,
        mission_id=execution.request.mission_id,
        workflow_id=execution.workflow.workflow_id,
        status=execution.status,
        stage_runs=execution.stage_runs,
        started_at=started_at,
        completed_at=completed_at,
        messages=messages,
        output_artifacts=artifacts,
    )


def render_markdown(report: MissionReport) -> str:
    """Render a compact human-readable mission report."""
    successful = sum(
        1 for run in report.stage_runs if run.status is StageStatus.SUCCEEDED
    )
    failed = sum(
        1 for run in report.stage_runs if run.status is StageStatus.FAILED
    )
    cancelled = sum(
        1 for run in report.stage_runs if run.status is StageStatus.CANCELLED
    )

    lines = [
        "# Engineering Mission Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Mission ID: `{report.mission_id}`",
        f"- Workflow ID: `{report.workflow_id}`",
        f"- Status: `{report.status.value}`",
        f"- Started: `{report.started_at.isoformat()}`",
        (
            f"- Completed: `{report.completed_at.isoformat()}`"
            if report.completed_at
            else "- Completed: `not completed`"
        ),
        f"- Successful stages: `{successful}`",
        f"- Failed stages: `{failed}`",
        f"- Cancelled stages: `{cancelled}`",
        "",
        "## Stage Timeline",
        "",
    ]

    for run in report.stage_runs:
        lines.extend(
            [
                f"### {run.stage_id}",
                "",
                f"- Attempt: `{run.attempt_number}`",
                f"- Status: `{run.status.value}`",
                f"- Started: `{run.started_at.isoformat() if run.started_at else 'not started'}`",
                (
                    f"- Completed: `{run.completed_at.isoformat()}`"
                    if run.completed_at
                    else "- Completed: `not completed`"
                ),
                "",
            ]
        )

    if report.output_artifacts:
        lines.extend(["## Output Artifacts", ""])
        lines.extend(f"- `{artifact}`" for artifact in report.output_artifacts)
        lines.append("")

    if report.messages:
        lines.extend(["## Messages", ""])
        lines.extend(f"- {message}" for message in report.messages)
        lines.append("")

    return "\n".join(lines)


def write_report_bundle(
    report: MissionReport,
    destination: Path,
) -> dict[str, Path]:
    """Persist JSON and Markdown mission evidence."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        json_path = destination / "MISSION_ORCHESTRATION_REPORT.json"
        markdown_path = destination / "MISSION_ORCHESTRATION_REPORT.md"

        json_path.write_text(
            json.dumps(
                report.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(
            render_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise MissionReportError(
            f"unable to write mission report bundle: {exc}"
        ) from exc

    return {
        json_path.name: json_path,
        markdown_path.name: markdown_path,
    }


def completed_now() -> datetime:
    """Return an explicit UTC completion timestamp."""
    return datetime.now(UTC)
