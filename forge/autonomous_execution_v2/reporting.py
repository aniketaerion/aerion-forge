"""Reporting for M5.7 autonomous execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from forge.autonomous_execution_v2.history import ExecutionHistory
from forge.autonomous_execution_v2.models import ExecutionRun


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Serializable report for one execution run."""

    run: ExecutionRun
    history: ExecutionHistory


def execution_report_payload(
    report: ExecutionReport,
) -> dict[str, Any]:
    """Return deterministic JSON-ready execution report."""
    succeeded_steps = sum(
        1
        for step in report.run.steps
        if step.state.value == "succeeded"
    )
    failed_steps = sum(
        1
        for step in report.run.steps
        if step.state.value == "failed"
    )

    return {
        "run": report.run.model_dump(mode="json"),
        "attempts": [
            attempt.model_dump(mode="json")
            for attempt in report.history.attempts
        ],
        "evidence": [
            item.model_dump(mode="json")
            for item in report.history.evidence
        ],
        "recovery_decisions": [
            item.model_dump(mode="json")
            for item in report.history.recovery_decisions
        ],
        "summary": {
            "step_count": len(report.run.steps),
            "succeeded_steps": succeeded_steps,
            "failed_steps": failed_steps,
            "attempt_count": len(report.history.attempts),
            "evidence_count": len(report.history.evidence),
            "recovery_count": len(
                report.history.recovery_decisions
            ),
        },
    }


def execution_report_json(
    report: ExecutionReport,
) -> str:
    """Render execution report as JSON."""
    return json.dumps(
        execution_report_payload(report),
        indent=2,
        sort_keys=True,
    )


def execution_report_markdown(
    report: ExecutionReport,
) -> str:
    """Render execution report as Markdown."""
    payload = execution_report_payload(report)
    summary = payload["summary"]

    lines = [
        "# Autonomous Execution Report",
        "",
        f"- Run ID: `{report.run.run_id}`",
        f"- Plan ID: `{report.run.plan_id}`",
        f"- Plan Version: `{report.run.plan_version}`",
        f"- State: `{report.run.state.value}`",
        f"- Repository: `{report.run.repository_root}`",
        f"- Steps: `{summary['step_count']}`",
        f"- Successful Steps: `{summary['succeeded_steps']}`",
        f"- Failed Steps: `{summary['failed_steps']}`",
        f"- Attempts: `{summary['attempt_count']}`",
        f"- Evidence Items: `{summary['evidence_count']}`",
        f"- Recovery Decisions: `{summary['recovery_count']}`",
        "",
        "## Steps",
        "",
    ]

    for step in report.run.steps:
        lines.extend(
            [
                f"### {step.sequence}. {step.name}",
                "",
                f"- Step ID: `{step.step_id}`",
                f"- State: `{step.state.value}`",
                f"- Risk: `{step.risk}`",
                "",
                step.description,
                "",
            ]
        )

    lines.extend(["## Attempts", ""])

    if not report.history.attempts:
        lines.extend(["No execution attempts recorded.", ""])
    else:
        for attempt in report.history.attempts:
            lines.extend(
                [
                    f"### Attempt {attempt.attempt_number}",
                    "",
                    f"- Attempt ID: `{attempt.attempt_id}`",
                    f"- Step ID: `{attempt.step_id}`",
                    f"- State: `{attempt.state.value}`",
                    (
                        f"- Failure: `{attempt.failure_reason}`"
                        if attempt.failure_reason
                        else "- Failure: `none`"
                    ),
                    "",
                ]
            )

    lines.extend(["## Evidence", ""])

    if not report.history.evidence:
        lines.extend(["No execution evidence recorded.", ""])
    else:
        for item in report.history.evidence:
            lines.extend(
                [
                    f"### {item.kind.value}",
                    "",
                    f"- Evidence ID: `{item.evidence_id}`",
                    f"- Step ID: `{item.step_id}`",
                    "",
                    item.summary,
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"