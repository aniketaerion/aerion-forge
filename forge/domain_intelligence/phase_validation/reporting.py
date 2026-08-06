"""Reporting pipeline for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TypedDict

from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationReport,
)


class PhaseValidationReportSummary(TypedDict):
    """Serializable executive summary for phase validation."""

    report_id: str
    phase: str
    milestone: str | None
    passed: bool
    check_count: int
    result_count: int
    finding_count: int
    status_counts: dict[str, int]
    severity_counts: dict[str, int]
    required_check_count: int
    passed_required_check_count: int
    release_manifest_id: str | None


def phase_validation_report_summary(
    report: PhaseValidationReport,
) -> PhaseValidationReportSummary:
    """Build a deterministic executive summary."""
    status_counts = Counter(
        result.status.value for result in report.results
    )
    severity_counts = Counter(
        finding.severity.value for finding in report.findings
    )
    required_ids = {
        check.check_id
        for check in report.checks
        if check.required
    }
    passed_required = {
        result.check_id
        for result in report.results
        if (
            result.check_id in required_ids
            and result.status.value == "pass"
        )
    }

    return {
        "report_id": report.report_id,
        "phase": report.phase,
        "milestone": report.milestone,
        "passed": report.passed,
        "check_count": len(report.checks),
        "result_count": len(report.results),
        "finding_count": len(report.findings),
        "status_counts": dict(sorted(status_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "required_check_count": len(required_ids),
        "passed_required_check_count": len(passed_required),
        "release_manifest_id": (
            None
            if report.release_manifest is None
            else report.release_manifest.manifest_id
        ),
    }


def phase_validation_report_markdown(
    report: PhaseValidationReport,
) -> str:
    """Render a phase-validation report as Markdown."""
    summary = phase_validation_report_summary(report)

    lines = [
        "# Phase Validation Intelligence Report",
        "",
        "## Executive Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Report ID | `{summary['report_id']}` |",
        f"| Phase | `{summary['phase']}` |",
        f"| Milestone | `{summary['milestone'] or '-'}` |",
        f"| Overall result | {'PASS' if summary['passed'] else 'FAIL'} |",
        f"| Checks | {summary['check_count']} |",
        f"| Results | {summary['result_count']} |",
        f"| Findings | {summary['finding_count']} |",
        (
            "| Required checks passed | "
            f"{summary['passed_required_check_count']}/"
            f"{summary['required_check_count']} |"
        ),
        "",
        "## Validation Checks",
        "",
    ]

    if report.checks:
        lines.extend(
            (
                "| Name | Kind | Required | Check ID |",
                "|---|---|---|---|",
            )
        )
        for check in report.checks:
            lines.append(
                "| "
                f"{check.name} | "
                f"{check.kind.value} | "
                f"{str(check.required).lower()} | "
                f"`{check.check_id}` |"
            )
    else:
        lines.append("No validation checks were registered.")

    lines.extend(("", "## Validation Results", ""))

    if report.results:
        lines.extend(
            (
                "| Status | Check ID | Message | Duration |",
                "|---|---|---|---:|",
            )
        )
        for result in report.results:
            lines.append(
                "| "
                f"{result.status.value} | "
                f"`{result.check_id}` | "
                f"{result.message} | "
                f"{result.duration_seconds:.2f} sec |"
            )
    else:
        lines.append("No validation results were produced.")

    lines.extend(("", "## Findings", ""))

    if report.findings:
        lines.extend(
            (
                "| Severity | Category | Message | Path |",
                "|---|---|---|---|",
            )
        )
        for finding in report.findings:
            lines.append(
                "| "
                f"{finding.severity.value} | "
                f"{finding.category} | "
                f"{finding.message} | "
                f"{finding.path or '-'} |"
            )
    else:
        lines.append("No phase-validation findings were produced.")

    lines.extend(("", "## Release Manifest", ""))

    if report.release_manifest is None:
        lines.append("No release manifest was generated.")
    else:
        manifest = report.release_manifest
        lines.extend(
            (
                "| Field | Value |",
                "|---|---|",
                f"| Manifest ID | `{manifest.manifest_id}` |",
                f"| Branch | `{manifest.branch}` |",
                f"| Commit | `{manifest.commit}` |",
                f"| Tag | `{manifest.tag or '-'}` |",
            )
        )

    lines.append("")
    return "\n".join(lines)


def write_phase_validation_report_bundle(
    report: PhaseValidationReport,
    destination: Path,
) -> dict[str, Path]:
    """Write detailed JSON, summary JSON, and Markdown outputs."""
    destination.mkdir(parents=True, exist_ok=True)

    analysis_path = destination / "PHASE_VALIDATION_REPORT.json"
    summary_path = destination / "PHASE_VALIDATION_SUMMARY.json"
    markdown_path = destination / "PHASE_VALIDATION_REPORT.md"

    analysis_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(
            phase_validation_report_summary(report),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    markdown_path.write_text(
        phase_validation_report_markdown(report),
        encoding="utf-8",
    )

    return {
        "analysis_json": analysis_path,
        "summary_json": summary_path,
        "analysis_markdown": markdown_path,
    }