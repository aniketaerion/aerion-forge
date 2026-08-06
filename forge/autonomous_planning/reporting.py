"""Reporting for autonomous planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningValidationResult,
)


@dataclass(frozen=True, slots=True)
class PlanningReport:
    """Serializable planning report."""

    plan: PlanningPlan
    validation: PlanningValidationResult


def planning_report_payload(
    report: PlanningReport,
) -> dict[str, Any]:
    """Return deterministic JSON-ready planning report."""
    return {
        "plan": report.plan.model_dump(mode="json"),
        "validation": report.validation.model_dump(
            mode="json"
        ),
        "step_count": len(report.plan.steps),
        "dependency_count": len(report.plan.dependencies),
        "blocking_findings": sum(
            1
            for finding in report.validation.findings
            if finding.blocking
        ),
    }


def planning_report_json(
    report: PlanningReport,
) -> str:
    """Render planning report as JSON."""
    return json.dumps(
        planning_report_payload(report),
        indent=2,
        sort_keys=True,
    )


def planning_report_markdown(
    report: PlanningReport,
) -> str:
    """Render planning report as Markdown."""
    lines = [
        "# Autonomous Planning Report",
        "",
        f"- Plan ID: `{report.plan.plan_id}`",
        f"- Request ID: `{report.plan.request_id}`",
        f"- Version: `{report.plan.version}`",
        f"- State: `{report.plan.state.value}`",
        f"- Risk: `{report.plan.risk.value}`",
        f"- Valid: `{str(report.validation.valid).lower()}`",
        f"- Steps: `{len(report.plan.steps)}`",
        f"- Dependencies: `{len(report.plan.dependencies)}`",
        "",
        "## Summary",
        "",
        report.plan.summary,
        "",
        "## Steps",
        "",
    ]

    for step in report.plan.steps:
        lines.extend(
            [
                f"### {step.sequence}. {step.name}",
                "",
                f"- ID: `{step.step_id}`",
                f"- Kind: `{step.kind.value}`",
                f"- Risk: `{step.risk.value}`",
                (
                    "- Approval: "
                    f"`{step.approval_requirement.value}`"
                ),
                "",
                step.description,
                "",
            ]
        )

    lines.extend(["## Validation Findings", ""])

    if not report.validation.findings:
        lines.extend(["No validation findings.", ""])
    else:
        for finding in report.validation.findings:
            lines.extend(
                [
                    f"### {finding.code}",
                    "",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Blocking: `{str(finding.blocking).lower()}`",
                    "",
                    finding.message,
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"