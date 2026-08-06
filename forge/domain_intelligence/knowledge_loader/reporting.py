"""Reporting pipeline for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TypedDict

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadReport,
)


class KnowledgeLoaderReportSummary(TypedDict):
    """Serializable executive summary for a knowledge load report."""

    report_id: str
    manifest_id: str
    project_root: str
    source_count: int
    document_count: int
    chunk_count: int
    finding_count: int
    source_kind_counts: dict[str, int]
    finding_severity_counts: dict[str, int]
    total_source_bytes: int
    total_chunk_tokens: int


def knowledge_loader_report_summary(
    report: KnowledgeLoadReport,
) -> KnowledgeLoaderReportSummary:
    """Build a deterministic executive summary."""
    source_kind_counts = Counter(
        source.kind.value for source in report.sources
    )
    finding_severity_counts = Counter(
        finding.severity.value for finding in report.findings
    )

    return {
        "report_id": report.report_id,
        "manifest_id": report.manifest.manifest_id,
        "project_root": report.manifest.project_root,
        "source_count": len(report.sources),
        "document_count": len(report.documents),
        "chunk_count": len(report.chunks),
        "finding_count": len(report.findings),
        "source_kind_counts": dict(
            sorted(source_kind_counts.items())
        ),
        "finding_severity_counts": dict(
            sorted(finding_severity_counts.items())
        ),
        "total_source_bytes": sum(
            source.size_bytes for source in report.sources
        ),
        "total_chunk_tokens": sum(
            chunk.token_estimate for chunk in report.chunks
        ),
    }


def knowledge_loader_report_markdown(
    report: KnowledgeLoadReport,
) -> str:
    """Render a knowledge-loader report as Markdown."""
    summary = knowledge_loader_report_summary(report)

    lines = [
        "# Knowledge Loader Intelligence Report",
        "",
        "## Executive Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Report ID | `{summary['report_id']}` |",
        f"| Manifest ID | `{summary['manifest_id']}` |",
        f"| Project root | `{summary['project_root']}` |",
        f"| Sources | {summary['source_count']} |",
        f"| Documents | {summary['document_count']} |",
        f"| Chunks | {summary['chunk_count']} |",
        f"| Findings | {summary['finding_count']} |",
        f"| Total source bytes | {summary['total_source_bytes']} |",
        f"| Estimated chunk tokens | {summary['total_chunk_tokens']} |",
        "",
        "## Sources",
        "",
    ]

    if report.sources:
        lines.extend(
            (
                "| Path | Kind | Bytes | Status |",
                "|---|---|---:|---|",
            )
        )
        for source in report.sources:
            lines.append(
                "| "
                f"{source.path} | "
                f"{source.kind.value} | "
                f"{source.size_bytes} | "
                f"{source.status.value} |"
            )
    else:
        lines.append("No knowledge sources were discovered.")

    lines.extend(("", "## Documents", ""))

    if report.documents:
        lines.extend(
            (
                "| Title | Source ID | Characters |",
                "|---|---|---:|",
            )
        )
        for document in report.documents:
            lines.append(
                "| "
                f"{document.title} | "
                f"`{document.source_id}` | "
                f"{len(document.text)} |"
            )
    else:
        lines.append("No knowledge documents were loaded.")

    lines.extend(("", "## Chunks", ""))

    if report.chunks:
        lines.extend(
            (
                "| Document ID | Ordinal | Tokens |",
                "|---|---:|---:|",
            )
        )
        for chunk in report.chunks:
            lines.append(
                "| "
                f"`{chunk.document_id}` | "
                f"{chunk.ordinal} | "
                f"{chunk.token_estimate} |"
            )
    else:
        lines.append("No knowledge chunks were generated.")

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
        lines.append("No knowledge-loader findings were produced.")

    lines.append("")
    return "\n".join(lines)


def write_knowledge_loader_report_bundle(
    report: KnowledgeLoadReport,
    destination: Path,
) -> dict[str, Path]:
    """Write detailed JSON, summary JSON, and Markdown reports."""
    destination.mkdir(parents=True, exist_ok=True)

    analysis_path = destination / "KNOWLEDGE_LOAD_REPORT.json"
    summary_path = destination / "KNOWLEDGE_LOAD_SUMMARY.json"
    markdown_path = destination / "KNOWLEDGE_LOAD_REPORT.md"

    analysis_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(
            knowledge_loader_report_summary(report),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    markdown_path.write_text(
        knowledge_loader_report_markdown(report),
        encoding="utf-8",
    )

    return {
        "analysis_json": analysis_path,
        "summary_json": summary_path,
        "analysis_markdown": markdown_path,
    }