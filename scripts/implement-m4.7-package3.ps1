[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\reporting.py" @'
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
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_reporting.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeLoadReport,
    KnowledgeManifest,
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.reporting import (
    knowledge_loader_report_markdown,
    knowledge_loader_report_summary,
    write_knowledge_loader_report_bundle,
)


def example_report() -> KnowledgeLoadReport:
    source = KnowledgeSource(
        source_id="knowledge-source-1",
        path="docs/guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=100,
        content_hash="abc",
    )
    document = KnowledgeDocument(
        document_id="knowledge-document-1",
        source_id=source.source_id,
        title="Forge Guide",
        text="Knowledge loading.",
    )
    chunk = KnowledgeChunk(
        chunk_id="knowledge-chunk-1",
        document_id=document.document_id,
        ordinal=0,
        text="Knowledge loading.",
        token_estimate=2,
    )
    manifest = KnowledgeManifest(
        manifest_id="knowledge-manifest-1",
        project_root="docs",
        source_ids=(source.source_id,),
        document_ids=(document.document_id,),
        chunk_ids=(chunk.chunk_id,),
    )
    finding = KnowledgeFinding(
        finding_id="knowledge-finding-1",
        category="compatibility",
        severity=KnowledgeFindingSeverity.LOW,
        message="Compatibility review required.",
        path=source.path,
    )

    return KnowledgeLoadReport(
        report_id="knowledge-report-1",
        manifest=manifest,
        sources=(source,),
        documents=(document,),
        chunks=(chunk,),
        findings=(finding,),
    )


def test_knowledge_loader_report_summary() -> None:
    summary = knowledge_loader_report_summary(example_report())

    assert summary["source_count"] == 1
    assert summary["document_count"] == 1
    assert summary["chunk_count"] == 1
    assert summary["finding_count"] == 1
    assert summary["source_kind_counts"] == {
        "markdown": 1,
    }
    assert summary["finding_severity_counts"] == {
        "low": 1,
    }
    assert summary["total_source_bytes"] == 100
    assert summary["total_chunk_tokens"] == 2


def test_knowledge_loader_report_markdown() -> None:
    markdown = knowledge_loader_report_markdown(
        example_report()
    )

    assert "# Knowledge Loader Intelligence Report" in markdown
    assert "Forge Guide" in markdown
    assert "docs/guide.md" in markdown
    assert "compatibility" in markdown


def test_write_knowledge_loader_report_bundle(
    tmp_path: Path,
) -> None:
    paths = write_knowledge_loader_report_bundle(
        example_report(),
        tmp_path,
    )

    assert set(paths) == {
        "analysis_json",
        "summary_json",
        "analysis_markdown",
    }
    assert all(path.is_file() for path in paths.values())

    analysis = json.loads(
        paths["analysis_json"].read_text(encoding="utf-8")
    )
    summary = json.loads(
        paths["summary_json"].read_text(encoding="utf-8")
    )
    markdown = paths["analysis_markdown"].read_text(
        encoding="utf-8"
    )

    assert analysis["report_id"] == "knowledge-report-1"
    assert summary["source_count"] == 1
    assert "Knowledge Loader Intelligence Report" in markdown
'@

$InitPath = ".\forge\domain_intelligence\knowledge_loader\__init__.py"
$InitContent = Get-Content $InitPath -Raw

if (
    $InitContent -notmatch
    'from forge\.domain_intelligence\.knowledge_loader\.reporting import'
) {
    $ImportAnchor = @'
from forge.domain_intelligence.knowledge_loader.policies import (
'@

    $ImportBlock = @'
from forge.domain_intelligence.knowledge_loader.reporting import (
    KnowledgeLoaderReportSummary,
    knowledge_loader_report_markdown,
    knowledge_loader_report_summary,
    write_knowledge_loader_report_bundle,
)
from forge.domain_intelligence.knowledge_loader.policies import (
'@

    if (-not $InitContent.Contains($ImportAnchor)) {
        throw "Knowledge-loader __init__.py import anchor was not found."
    }

    $InitContent = $InitContent.Replace(
        $ImportAnchor,
        $ImportBlock
    )
}

if (
    $InitContent -notmatch
    '"KnowledgeLoaderReportSummary"'
) {
    $AllAnchor = '    "KnowledgeLoaderPolicyError",'

    if (-not $InitContent.Contains($AllAnchor)) {
        throw "Knowledge-loader __all__ type anchor was not found."
    }

    $InitContent = $InitContent.Replace(
        $AllAnchor,
        @'
    "KnowledgeLoaderPolicyError",
    "KnowledgeLoaderReportSummary",
'@
    )
}

foreach ($Export in @(
    "knowledge_loader_report_markdown",
    "knowledge_loader_report_summary",
    "write_knowledge_loader_report_bundle"
)) {
    if ($InitContent -notmatch "`"$Export`"") {
        $Anchor = '    "validate_knowledge_request",'

        if (-not $InitContent.Contains($Anchor)) {
            throw "Knowledge-loader __all__ function anchor was not found."
        }

        $InitContent = $InitContent.Replace(
            $Anchor,
            "    `"$Export`",`n$Anchor"
        )
    }
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $InitPath),
    $InitContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\domain_intelligence\knowledge_loader\__init__.py" -ForegroundColor Green

Write-Host ""
Write-Host "M4.7 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_knowledge_loader_reporting.py `
    .\tests\test_domain_intelligence_knowledge_loader_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.7 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.7 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short