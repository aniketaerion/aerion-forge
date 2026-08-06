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

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\reporting.py" @'
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
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_reporting.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.phase_validation.models import (
    PhaseFindingSeverity,
    PhaseReleaseManifest,
    PhaseValidationCheck,
    PhaseValidationFinding,
    PhaseValidationKind,
    PhaseValidationReport,
    PhaseValidationResult,
    PhaseValidationStatus,
)
from forge.domain_intelligence.phase_validation.reporting import (
    phase_validation_report_markdown,
    phase_validation_report_summary,
    write_phase_validation_report_bundle,
)


def example_report() -> PhaseValidationReport:
    check = PhaseValidationCheck(
        check_id="check-1",
        name="Architecture validation",
        kind=PhaseValidationKind.ARCHITECTURE,
    )
    result = PhaseValidationResult(
        result_id="result-1",
        check_id=check.check_id,
        status=PhaseValidationStatus.PASS,
        message="Architecture validation passed.",
    )
    finding = PhaseValidationFinding(
        finding_id="finding-1",
        category="release-note",
        severity=PhaseFindingSeverity.INFO,
        message="Release note generated.",
    )
    manifest = PhaseReleaseManifest(
        manifest_id="manifest-1",
        phase="4",
        milestone="M4.8",
        commit="abc1234",
        branch="main",
        tag="forge-v0.3-m4.8",
        validation_result_ids=(result.result_id,),
    )

    return PhaseValidationReport(
        report_id="report-1",
        phase="4",
        milestone="M4.8",
        checks=(check,),
        results=(result,),
        findings=(finding,),
        release_manifest=manifest,
    )


def test_phase_validation_report_summary() -> None:
    summary = phase_validation_report_summary(
        example_report()
    )

    assert summary["passed"]
    assert summary["check_count"] == 1
    assert summary["result_count"] == 1
    assert summary["finding_count"] == 1
    assert summary["status_counts"] == {"pass": 1}
    assert summary["severity_counts"] == {"info": 1}
    assert summary["required_check_count"] == 1
    assert summary["passed_required_check_count"] == 1
    assert summary["release_manifest_id"] == "manifest-1"


def test_phase_validation_report_markdown() -> None:
    markdown = phase_validation_report_markdown(
        example_report()
    )

    assert "# Phase Validation Intelligence Report" in markdown
    assert "Architecture validation" in markdown
    assert "forge-v0.3-m4.8" in markdown
    assert "PASS" in markdown


def test_write_phase_validation_report_bundle(
    tmp_path: Path,
) -> None:
    paths = write_phase_validation_report_bundle(
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

    assert analysis["report_id"] == "report-1"
    assert summary["passed"] is True
    assert "Phase Validation Intelligence Report" in markdown
'@

$InitPath = ".\forge\domain_intelligence\phase_validation\__init__.py"
$InitContent = Get-Content $InitPath -Raw

if (
    $InitContent -notmatch
    'from forge\.domain_intelligence\.phase_validation\.reporting import'
) {
    $ImportAnchor = @'
from forge.domain_intelligence.phase_validation.policies import (
'@

    $ImportBlock = @'
from forge.domain_intelligence.phase_validation.reporting import (
    PhaseValidationReportSummary,
    phase_validation_report_markdown,
    phase_validation_report_summary,
    write_phase_validation_report_bundle,
)
from forge.domain_intelligence.phase_validation.policies import (
'@

    if (-not $InitContent.Contains($ImportAnchor)) {
        throw "Phase-validation __init__.py import anchor was not found."
    }

    $InitContent = $InitContent.Replace(
        $ImportAnchor,
        $ImportBlock
    )
}

if (
    $InitContent -notmatch
    '"PhaseValidationReportSummary"'
) {
    $AllAnchor = '    "PhaseValidationReport",'

    if (-not $InitContent.Contains($AllAnchor)) {
        throw "Phase-validation __all__ type anchor was not found."
    }

    $InitContent = $InitContent.Replace(
        $AllAnchor,
        @'
    "PhaseValidationReport",
    "PhaseValidationReportSummary",
'@
    )
}

foreach ($Export in @(
    "phase_validation_report_markdown",
    "phase_validation_report_summary",
    "write_phase_validation_report_bundle"
)) {
    if ($InitContent -notmatch "`"$Export`"") {
        $Anchor = '    "validate_phase_request",'

        if (-not $InitContent.Contains($Anchor)) {
            throw "Phase-validation __all__ function anchor was not found."
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

Write-Host "UPDATED forge\domain_intelligence\phase_validation\__init__.py" -ForegroundColor Green

Write-Host ""
Write-Host "M4.8 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_phase_validation_reporting.py `
    .\tests\test_domain_intelligence_phase_validation_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.8 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.8 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short