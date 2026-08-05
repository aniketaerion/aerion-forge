"""Reporting for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from forge.domain_intelligence.backend.errors import (
    BackendIntelligenceError,
)
from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
)


def backend_report_summary(
    report: BackendAnalysisReport,
) -> dict[str, object]:
    """Return a deterministic machine-readable backend summary."""
    categories = Counter(
        finding.category for finding in report.findings
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
        "runtimes": [
            runtime.value
            for runtime in report.project.runtimes
        ],
        "frameworks": [
            framework.value
            for framework in report.project.frameworks
        ],
        "package_manager": report.project.package_manager,
        "source_directories": list(
            report.project.source_directories
        ),
        "configuration_files": list(
            report.project.configuration_files
        ),
        "service_files": list(
            report.project.service_files
        ),
        "worker_files": list(
            report.project.worker_files
        ),
        "finding_count": len(report.findings),
        "finding_categories": dict(
            sorted(categories.items())
        ),
    }


def render_backend_markdown(
    report: BackendAnalysisReport,
) -> str:
    """Render a stable Markdown backend-intelligence report."""
    lines = [
        "# Backend Intelligence Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Project ID: `{report.project.project_id}`",
        f"- Project root: `{report.project.root}`",
        (
            "- Runtimes: "
            + ", ".join(
                runtime.value
                for runtime in report.project.runtimes
            )
        ),
        (
            "- Frameworks: "
            + ", ".join(
                framework.value
                for framework in report.project.frameworks
            )
        ),
        (
            "- Package manager: "
            + (
                report.project.package_manager
                if report.project.package_manager is not None
                else "unknown"
            )
        ),
        f"- Findings: `{len(report.findings)}`",
        "",
        "## Backend Layout",
        "",
        (
            "- Source directories: "
            + (
                ", ".join(report.project.source_directories)
                if report.project.source_directories
                else "none detected"
            )
        ),
        (
            "- Configuration files: "
            + (
                ", ".join(report.project.configuration_files)
                if report.project.configuration_files
                else "none detected"
            )
        ),
        (
            "- Service files: "
            + (
                ", ".join(report.project.service_files)
                if report.project.service_files
                else "none detected"
            )
        ),
        (
            "- Worker files: "
            + (
                ", ".join(report.project.worker_files)
                if report.project.worker_files
                else "none detected"
            )
        ),
        "",
        "## Findings",
        "",
    ]

    if not report.findings:
        lines.append("No backend findings were produced.")
    else:
        for finding in report.findings:
            lines.extend(
                [
                    f"### {finding.category}",
                    "",
                    f"- Finding ID: `{finding.finding_id}`",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Message: {finding.message}",
                    (
                        f"- Path: `{finding.path}`"
                        if finding.path is not None
                        else "- Path: not applicable"
                    ),
                ]
            )

            if finding.evidence:
                lines.append("- Evidence:")
                for key, value in sorted(
                    finding.evidence.items()
                ):
                    lines.append(
                        f"  - `{key}`: `{value}`"
                    )

            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_backend_report_bundle(
    report: BackendAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write backend JSON, summary JSON, and Markdown reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        raw_json = destination / "BACKEND_ANALYSIS.json"
        summary_json = destination / "BACKEND_SUMMARY.json"
        markdown = destination / "BACKEND_ANALYSIS.md"

        raw_json.write_text(
            json.dumps(
                report.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        summary_json.write_text(
            json.dumps(
                backend_report_summary(report),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown.write_text(
            render_backend_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise BackendIntelligenceError(
            f"unable to write backend report bundle: {destination}"
        ) from exc

    return {
        raw_json.name: raw_json,
        summary_json.name: summary_json,
        markdown.name: markdown,
    }