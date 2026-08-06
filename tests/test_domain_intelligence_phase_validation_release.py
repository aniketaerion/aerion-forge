from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)
from forge.domain_intelligence.phase_validation.release import (
    build_release_manifest,
    validate_release_readiness,
)


def test_release_readiness_passes() -> None:
    result = validate_release_readiness(
        branch="feature/m4.8",
        commit="abc1234",
        worktree_clean=True,
        require_clean_worktree=True,
        tag=None,
        require_release_tag=False,
    )

    assert result.status is PhaseValidationStatus.PASS


def test_release_readiness_requires_tag() -> None:
    result = validate_release_readiness(
        branch="main",
        commit="abc1234",
        worktree_clean=True,
        require_clean_worktree=True,
        tag=None,
        require_release_tag=True,
    )

    assert result.status is PhaseValidationStatus.FAIL


def test_release_manifest_is_deterministic() -> None:
    first = build_release_manifest(
        phase="4",
        milestone="M4.8",
        branch="main",
        commit="abc1234",
        tag="forge-v0.3-m4.8",
        validation_result_ids=("result-1",),
    )
    second = build_release_manifest(
        phase="4",
        milestone="M4.8",
        branch="main",
        commit="abc1234",
        tag="forge-v0.3-m4.8",
        validation_result_ids=("result-1",),
    )

    assert first.manifest_id == second.manifest_id