from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    BuildVerificationRequest,
    ReleaseGateDecision,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)
from forge.build_verification.reporting import (
    render_markdown,
    write_report_bundle,
)


def report_inputs(tmp_path: Path) -> tuple[BuildVerificationEvidence, ReleaseGateDecision]:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(step,),
        target_paths=("sample.py",),
    )
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime.now(UTC),
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)
    evidence = build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )
    return evidence, decide_release(
        evidence,
        BuildVerificationPolicy(),
    )


def test_markdown_contains_release_decision(tmp_path: Path) -> None:
    evidence, decision = report_inputs(tmp_path)
    rendered = render_markdown(evidence, decision)

    assert "Build Verification Report" in rendered
    assert decision.decision.value in rendered


def test_report_bundle_writes_all_artifacts(tmp_path: Path) -> None:
    evidence, decision = report_inputs(tmp_path)
    written = write_report_bundle(
        evidence,
        decision,
        tmp_path / "reports",
    )

    assert set(written) == {
        "BUILD_VERIFICATION_EVIDENCE.json",
        "RELEASE_GATE_DECISION.json",
        "BUILD_VERIFICATION_REPORT.md",
    }