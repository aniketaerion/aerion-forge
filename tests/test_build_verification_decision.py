from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    BuildVerificationRequest,
    FindingSeverity,
    ReleaseDecision,
    VerificationFinding,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)


def evidence_for(
    tmp_path: Path,
    result: VerificationStepResult,
) -> BuildVerificationEvidence:
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
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
    started = datetime(2026, 1, 1, tzinfo=UTC)
    return build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )


def test_release_is_approved_when_required_step_passes(
    tmp_path: Path,
) -> None:
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime.now(UTC),
    )

    decision = decide_release(
        evidence_for(tmp_path, result),
        BuildVerificationPolicy(),
    )

    assert decision.decision is ReleaseDecision.APPROVED


def test_release_is_rejected_when_required_step_fails(
    tmp_path: Path,
) -> None:
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.FAILED,
        exit_code=1,
        completed_at=datetime.now(UTC),
    )

    decision = decide_release(
        evidence_for(tmp_path, result),
        BuildVerificationPolicy(),
    )

    assert decision.decision is ReleaseDecision.REJECTED


def test_high_finding_rejects_release(tmp_path: Path) -> None:
    finding = VerificationFinding(
        finding_id="finding-1",
        step_id="ruff",
        severity=FindingSeverity.HIGH,
        code="TEST",
        message="blocking",
    )
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        findings=(finding,),
        completed_at=datetime.now(UTC),
    )

    decision = decide_release(
        evidence_for(tmp_path, result),
        BuildVerificationPolicy(),
    )

    assert decision.decision is ReleaseDecision.REJECTED
    assert decision.blocking_findings == ("finding-1",)
