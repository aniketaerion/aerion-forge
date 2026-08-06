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

Write-Utf8NoBom "forge\domain_intelligence\embedded\reporting.py" @'
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
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_reporting.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedFinding,
    EmbeddedFindingSeverity,
    EmbeddedInterface,
    EmbeddedInterfaceKind,
    EmbeddedMessage,
    EmbeddedPlatformKind,
    EmbeddedProject,
)
from forge.domain_intelligence.embedded.reporting import (
    embedded_report_markdown,
    embedded_report_summary,
    write_embedded_report_bundle,
)


def example_report() -> EmbeddedAnalysisReport:
    project = EmbeddedProject(
        project_id="embedded-project-1",
        root="firmware",
        platforms=(EmbeddedPlatformKind.PX4,),
        build_files=("CMakeLists.txt",),
    )
    component = EmbeddedComponent(
        component_id="embedded-component-1",
        name="navigator",
        kind=EmbeddedComponentKind.AUTOPILOT_MODULE,
        platform=EmbeddedPlatformKind.PX4,
        source_paths=("src/modules/navigator",),
    )
    interface = EmbeddedInterface(
        interface_id="embedded-interface-1",
        name="uart:navigator.cpp",
        kind=EmbeddedInterfaceKind.UART,
        source_path="src/modules/navigator/navigator.cpp",
    )
    message = EmbeddedMessage(
        message_id="embedded-message-1",
        name="VehicleState",
        protocol="ros2",
        fields=("latitude", "longitude"),
        source_path="msg/VehicleState.msg",
    )
    finding = EmbeddedFinding(
        finding_id="embedded-finding-1",
        category="blocking-delay",
        severity=EmbeddedFindingSeverity.MEDIUM,
        message="Blocking delay detected in embedded code.",
        path="src/control.c",
    )

    return EmbeddedAnalysisReport(
        report_id="embedded-report-1",
        project=project,
        components=(component,),
        interfaces=(interface,),
        messages=(message,),
        findings=(finding,),
    )


def test_embedded_report_summary() -> None:
    summary = embedded_report_summary(example_report())

    assert summary["platforms"] == ("px4",)
    assert summary["component_count"] == 1
    assert summary["interface_count"] == 1
    assert summary["message_count"] == 1
    assert summary["finding_count"] == 1
    assert summary["finding_severity_counts"] == {
        "medium": 1,
    }


def test_embedded_report_markdown() -> None:
    markdown = embedded_report_markdown(example_report())

    assert "# Embedded Domain Intelligence Report" in markdown
    assert "navigator" in markdown
    assert "VehicleState" in markdown
    assert "blocking-delay" in markdown


def test_write_embedded_report_bundle(
    tmp_path: Path,
) -> None:
    paths = write_embedded_report_bundle(
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

    assert analysis["report_id"] == "embedded-report-1"
    assert summary["component_count"] == 1
    assert "Embedded Domain Intelligence Report" in markdown
'@

$InitPath = ".\forge\domain_intelligence\embedded\__init__.py"
$InitContent = Get-Content $InitPath -Raw

if (
    $InitContent -notmatch
    'from forge\.domain_intelligence\.embedded\.reporting import'
) {
    $ImportAnchor = @'
from forge.domain_intelligence.embedded.policies import (
'@

    $ImportBlock = @'
from forge.domain_intelligence.embedded.reporting import (
    EmbeddedReportSummary,
    embedded_report_markdown,
    embedded_report_summary,
    write_embedded_report_bundle,
)
from forge.domain_intelligence.embedded.policies import (
'@

    if (-not $InitContent.Contains($ImportAnchor)) {
        throw "Embedded __init__.py import anchor was not found."
    }

    $InitContent = $InitContent.Replace(
        $ImportAnchor,
        $ImportBlock
    )
}

if (
    $InitContent -notmatch
    '"EmbeddedReportSummary"'
) {
    $AllAnchor = '    "EmbeddedProject",'

    if (-not $InitContent.Contains($AllAnchor)) {
        throw "Embedded __all__ anchor was not found."
    }

    $InitContent = $InitContent.Replace(
        $AllAnchor,
        @'
    "EmbeddedProject",
    "EmbeddedReportSummary",
'@
    )
}

foreach ($Export in @(
    "embedded_report_markdown",
    "embedded_report_summary",
    "write_embedded_report_bundle"
)) {
    if ($InitContent -notmatch "`"$Export`"") {
        $Anchor = '    "validate_embedded_request",'

        if (-not $InitContent.Contains($Anchor)) {
            throw "Embedded __all__ function anchor was not found."
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

Write-Host "UPDATED forge\domain_intelligence\embedded\__init__.py" -ForegroundColor Green

Write-Host ""
Write-Host "M4.6 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_embedded_reporting.py `
    .\tests\test_domain_intelligence_embedded_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.6 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.6 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short