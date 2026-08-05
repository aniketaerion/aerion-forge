from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.evidence import (
    aggregate_status,
    build_evidence,
    repository_fingerprint,
)
from forge.build_verification.models import (
    BuildVerificationRequest,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)


def request_for(tmp_path: Path) -> BuildVerificationRequest:
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
    )
    return BuildVerificationRequest(
        request_id="request-1",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(step,),
        target_paths=("sample.py",),
    )


def test_repository_fingerprint_changes_with_content(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    first = repository_fingerprint(tmp_path, ("sample.py",))

    target.write_text("value = 2\n", encoding="utf-8")
    second = repository_fingerprint(tmp_path, ("sample.py",))

    assert first != second


def test_aggregate_status_is_fail_closed() -> None:
    passed = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime.now(UTC),
    )
    failed = VerificationStepResult(
        step_id="pytest",
        status=VerificationStatus.FAILED,
        exit_code=1,
        completed_at=datetime.now(UTC),
    )

    assert aggregate_status((passed, failed)) is VerificationStatus.FAILED


def test_evidence_identifier_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    request = request_for(tmp_path)
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)

    first = build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )
    second = build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )

    assert first.evidence_id == second.evidence_id