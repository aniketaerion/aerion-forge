from pathlib import Path

from forge.build_verification.models import (
    BuildVerificationRequest,
    ReleaseDecision,
    VerificationStatus,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.pipeline import BuildVerificationPipeline


def test_pipeline_approves_passing_verification(
    tmp_path: Path,
) -> None:
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

    evidence, decision = BuildVerificationPipeline().execute(request)

    assert evidence.status is VerificationStatus.PASSED
    assert decision.decision is ReleaseDecision.APPROVED


def test_pipeline_stops_after_required_failure(
    tmp_path: Path,
) -> None:
    (tmp_path / "bad.py").write_text(
        "import os\n",
        encoding="utf-8",
    )
    first = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("bad.py",),
    )
    second = VerificationStep(
        step_id="pytest",
        tool=VerificationTool.PYTEST,
        name="Pytest",
        arguments=("-q",),
    )
    request = BuildVerificationRequest(
        request_id="request-2",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(first, second),
        target_paths=("bad.py",),
    )

    evidence, decision = BuildVerificationPipeline().execute(request)

    assert evidence.status is VerificationStatus.FAILED
    assert len(evidence.step_results) == 1
    assert decision.decision is ReleaseDecision.REJECTED