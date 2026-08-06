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