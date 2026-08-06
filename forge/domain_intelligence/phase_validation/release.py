"""Release-readiness validation for M4.8 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_release_manifest_identifier,
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseReleaseManifest,
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def release_check() -> PhaseValidationCheck:
    payload = {
        "name": "Release readiness validation",
        "kind": PhaseValidationKind.RELEASE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Release readiness validation",
        kind=PhaseValidationKind.RELEASE,
        description=(
            "Validate branch, commit, working-tree, and release-tag "
            "requirements."
        ),
    )


def validate_release_readiness(
    *,
    branch: str,
    commit: str,
    worktree_clean: bool,
    require_clean_worktree: bool,
    tag: str | None,
    require_release_tag: bool,
) -> PhaseValidationResult:
    check = release_check()

    clean_pass = (
        worktree_clean
        if require_clean_worktree
        else True
    )
    tag_pass = (
        bool(tag)
        if require_release_tag
        else True
    )
    passed = bool(branch and commit) and clean_pass and tag_pass
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )

    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "branch": branch,
        "commit": commit,
        "worktree_clean": worktree_clean,
        "tag": tag,
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Release-readiness requirements passed."
            if passed
            else "Release-readiness requirements failed."
        ),
        evidence={
            "branch": branch,
            "commit": commit,
            "worktree_clean": str(worktree_clean).lower(),
            "tag": tag or "",
            "require_release_tag": str(
                require_release_tag
            ).lower(),
        },
    )


def build_release_manifest(
    *,
    phase: str,
    milestone: str | None,
    branch: str,
    commit: str,
    tag: str | None,
    validation_result_ids: tuple[str, ...],
) -> PhaseReleaseManifest:
    payload = {
        "phase": phase,
        "milestone": milestone,
        "branch": branch,
        "commit": commit,
        "tag": tag,
        "validation_result_ids": validation_result_ids,
    }

    return PhaseReleaseManifest(
        manifest_id=phase_release_manifest_identifier(payload),
        phase=phase,
        milestone=milestone,
        branch=branch,
        commit=commit,
        tag=tag,
        validation_result_ids=validation_result_ids,
    )