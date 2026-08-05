"""Evidence construction for M3.7 Build Verification."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.identifiers import (
    verification_evidence_identifier,
)
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationRequest,
    VerificationStatus,
    VerificationStepResult,
)


def repository_fingerprint(
    repository_root: Path,
    target_paths: tuple[str, ...],
) -> str:
    """Hash bounded repository content deterministically."""
    root = repository_root.resolve()
    digest = hashlib.sha256()

    selected = target_paths or (".",)

    for relative_path in sorted(selected):
        candidate = (root / relative_path).resolve()
        candidate.relative_to(root)

        if candidate.is_file():
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(candidate.read_bytes())
            digest.update(b"\0")
            continue

        if candidate.is_dir():
            for file_path in sorted(
                path
                for path in candidate.rglob("*")
                if path.is_file()
                and ".git" not in path.parts
                and "__pycache__" not in path.parts
            ):
                relative = file_path.relative_to(root).as_posix()
                digest.update(relative.encode("utf-8"))
                digest.update(b"\0")
                digest.update(file_path.read_bytes())
                digest.update(b"\0")

    return digest.hexdigest()


def aggregate_status(
    results: tuple[VerificationStepResult, ...],
) -> VerificationStatus:
    """Aggregate step results using fail-closed precedence."""
    statuses = {result.status for result in results}

    if VerificationStatus.TIMED_OUT in statuses:
        return VerificationStatus.TIMED_OUT
    if VerificationStatus.BLOCKED in statuses:
        return VerificationStatus.BLOCKED
    if VerificationStatus.FAILED in statuses:
        return VerificationStatus.FAILED
    if VerificationStatus.CANCELLED in statuses:
        return VerificationStatus.CANCELLED
    if results and all(
        result.status is VerificationStatus.PASSED
        for result in results
    ):
        return VerificationStatus.PASSED

    return VerificationStatus.RUNNING


def build_evidence(
    request: BuildVerificationRequest,
    results: tuple[VerificationStepResult, ...],
    *,
    repository_root: Path,
    started_at: datetime,
    completed_at: datetime | None = None,
) -> BuildVerificationEvidence:
    """Construct deterministic build-verification evidence."""
    status = aggregate_status(results)
    terminal = status in {
        VerificationStatus.PASSED,
        VerificationStatus.FAILED,
        VerificationStatus.BLOCKED,
        VerificationStatus.TIMED_OUT,
        VerificationStatus.CANCELLED,
    }

    finished_at = completed_at
    if terminal and finished_at is None:
        finished_at = datetime.now(UTC)

    fingerprint = repository_fingerprint(
        repository_root,
        request.target_paths,
    )

    evidence_id = verification_evidence_identifier(
        {
            "request_id": request.request_id,
            "source_revision": request.source_revision,
            "repository_fingerprint": fingerprint,
            "status": status.value,
            "results": [
                {
                    "step_id": result.step_id,
                    "status": result.status.value,
                    "exit_code": result.exit_code,
                }
                for result in results
            ],
        }
    )

    return BuildVerificationEvidence(
        evidence_id=evidence_id,
        request=request,
        status=status,
        step_results=results,
        repository_fingerprint=fingerprint,
        started_at=started_at,
        completed_at=finished_at,
    )