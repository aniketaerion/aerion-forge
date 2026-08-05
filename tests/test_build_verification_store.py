from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    BuildVerificationRequest,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)
from forge.build_verification.store import BuildVerificationStore


def evidence_for(tmp_path: Path) -> BuildVerificationEvidence:
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
    return build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )


def test_store_round_trip(tmp_path: Path) -> None:
    evidence = evidence_for(tmp_path)
    decision = decide_release(
        evidence,
        BuildVerificationPolicy(),
    )
    store = BuildVerificationStore(tmp_path / "memory")

    store.save_evidence(evidence)
    store.save_decision(decision)

    assert store.load_evidence(evidence.evidence_id) == evidence
    assert store.load_decision(decision.decision_id) == decision


def test_store_lists_evidence_deterministically(tmp_path: Path) -> None:
    evidence = evidence_for(tmp_path)
    store = BuildVerificationStore(tmp_path / "memory")
    store.save_evidence(evidence)

    assert store.list_evidence_ids() == (evidence.evidence_id,)