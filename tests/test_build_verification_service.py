from pathlib import Path

from forge.build_verification.models import (
    ReleaseDecision,
    VerificationTool,
)
from forge.build_verification.service import BuildVerificationService
from forge.build_verification.store import BuildVerificationStore


def initialize_git_repository(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(
        ("git", "init"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.email", "test@example.com"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.name", "Test User"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    subprocess.run(
        ("git", "add", "sample.py"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "commit", "-m", "initial"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def test_service_creates_deterministic_request(tmp_path: Path) -> None:
    initialize_git_repository(tmp_path)
    service = BuildVerificationService()

    first = service.create_request(
        tmp_path,
        objective="verify",
        tools=(VerificationTool.RUFF,),
        target_paths=("sample.py",),
    )
    second = service.create_request(
        tmp_path,
        objective="verify",
        tools=(VerificationTool.RUFF,),
        target_paths=("sample.py",),
    )

    assert first.request_id == second.request_id


def test_service_verifies_and_persists(tmp_path: Path) -> None:
    initialize_git_repository(tmp_path)
    service = BuildVerificationService()
    request = service.create_request(
        tmp_path,
        objective="verify",
        tools=(VerificationTool.RUFF,),
        target_paths=("sample.py",),
    )
    store = BuildVerificationStore(tmp_path / "memory")

    decision = service.verify(
        request,
        store=store,
        report_directory=tmp_path / "reports",
    )

    assert decision.decision is ReleaseDecision.APPROVED
    assert len(store.list_evidence_ids()) == 1
    assert (tmp_path / "reports" / "BUILD_VERIFICATION_REPORT.md").is_file()