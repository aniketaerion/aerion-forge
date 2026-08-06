"""Reporting pipeline for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TypedDict

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
)


class EmbeddedReportSummary(TypedDict):
    """Serializable executive summary for an embedded report."""

    report_id: str
    project_id: str
    project_root: str
    platforms: tuple[str, ...]
    source_file_count: int
    configuration_file_count: int
    build_file_count: int
    component_count: int
    interface_count: int
    message_count: int
    finding_count: int
    finding_severity_counts: dict[str, int]
    component_platform_counts: dict[str, int]
    interface_kind_counts: dict[str, int]


def embedded_report_summary(
    report: EmbeddedAnalysisReport,
) -> EmbeddedReportSummary:
    """Build a deterministic executive summary."""
    severity_counts = Counter(
        finding.severity.value for finding in report.findings
    )
    platform_counts = Counter(
        component.platform.value for component in report.components
    )
    interface_counts = Counter(
        interface.kind.value for interface in report.interfaces
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
        "platforms": tuple(
            platform.value for platform in report.project.platforms
        ),
        "source_file_count": len(report.project.source_files),
        "configuration_file_count": len(
            report.project.configuration_files
        ),
        "build_file_count": len(report.project.build_files),
        "component_count": len(report.components),
        "interface_count": len(report.interfaces),
        "message_count": len(report.messages),
        "finding_count": len(report.findings),
        "finding_severity_counts": dict(
            sorted(severity_counts.items())
        ),
        "component_platform_counts": dict(
            sorted(platform_counts.items())
        ),
        "interface_kind_counts": dict(
            sorted(interface_counts.items())
        ),
    }


def embedded_report_markdown(
    report: EmbeddedAnalysisReport,
) -> str:
    """Render an embedded analysis report as Markdown."""
    summary = embedded_report_summary(report)

    lines = [
        "# Embedded Domain Intelligence Report",
        "",
        "## Executive Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Report ID | `{summary['report_id']}` |",
        f"| Project ID | `{summary['project_id']}` |",
        f"| Project root | `{summary['project_root']}` |",
        (
            "| Platforms | "
            + (
                ", ".join(summary["platforms"])
                if summary["platforms"]
                else "none"
            )
            + " |"
        ),
        f"| Components | {summary['component_count']} |",
        f"| Interfaces | {summary['interface_count']} |",
        f"| Messages | {summary['message_count']} |",
        f"| Findings | {summary['finding_count']} |",
        f"| Build files | {summary['build_file_count']} |",
        "",
        "## Components",
        "",
    ]

    if report.components:
        lines.extend(
            (
                "| Name | Platform | Kind | Source paths |",
                "|---|---|---|---|",
            )
        )
        for component in report.components:
            lines.append(
                "| "
                f"{component.name} | "
                f"{component.platform.value} | "
                f"{component.kind.value} | "
                f"{', '.join(component.source_paths) or '-'} |"
            )
    else:
        lines.append("No embedded components were detected.")

    lines.extend(("", "## Interfaces", ""))

    if report.interfaces:
        lines.extend(
            (
                "| Name | Kind | Source |",
                "|---|---|---|",
            )
        )
        for interface in report.interfaces:
            lines.append(
                "| "
                f"{interface.name} | "
                f"{interface.kind.value} | "
                f"{interface.source_path or '-'} |"
            )
    else:
        lines.append("No embedded interfaces were detected.")

    lines.extend(("", "## Messages", ""))

    if report.messages:
        lines.extend(
            (
                "| Name | Protocol | Fields | Source |",
                "|---|---|---|---|",
            )
        )
        for message in report.messages:
            lines.append(
                "| "
                f"{message.name} | "
                f"{message.protocol} | "
                f"{', '.join(message.fields) or '-'} | "
                f"{message.source_path or '-'} |"
            )
    else:
        lines.append("No embedded messages were detected.")

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
        lines.append("No embedded findings were produced.")

    lines.append("")
    return "\n".join(lines)


def write_embedded_report_bundle(
    report: EmbeddedAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON, summary JSON, and Markdown reports."""
    destination.mkdir(parents=True, exist_ok=True)

    analysis_path = destination / "EMBEDDED_ANALYSIS.json"
    summary_path = destination / "EMBEDDED_SUMMARY.json"
    markdown_path = destination / "EMBEDDED_ANALYSIS.md"

    analysis_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(
            embedded_report_summary(report),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    markdown_path.write_text(
        embedded_report_markdown(report),
        encoding="utf-8",
    )

    return {
        "analysis_json": analysis_path,
        "summary_json": summary_path,
        "analysis_markdown": markdown_path,
    }