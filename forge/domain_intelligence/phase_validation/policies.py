"""Policies for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.phase_validation.errors import (
    PhaseValidationPolicyError,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)


class PhaseValidationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_repository_mutation: bool = False
    allow_destructive_commands: bool = False
    require_git_repository: bool = True
    require_clean_worktree: bool = True
    maximum_validation_seconds: int = Field(
        default=900,
        ge=1,
        le=7200,
    )
    minimum_test_count: int = Field(default=1, ge=0)
    minimum_coverage_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )


def resolve_phase_repository_root(
    repository_root: str | Path,
    policy: PhaseValidationPolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise PhaseValidationPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_git_repository and not (root / ".git").exists():
        raise PhaseValidationPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_phase_request(
    request: PhaseValidationRequest,
    policy: PhaseValidationPolicy,
) -> None:
    if not request.phase.strip():
        raise PhaseValidationPolicyError("phase must not be empty")

    if request.minimum_test_count < policy.minimum_test_count:
        raise PhaseValidationPolicyError(
            "requested minimum test count is below policy minimum"
        )

    if (
        request.minimum_coverage_percent
        < policy.minimum_coverage_percent
    ):
        raise PhaseValidationPolicyError(
            "requested coverage threshold is below policy minimum"
        )

    if (
        policy.require_clean_worktree
        and not request.require_clean_worktree
    ):
        raise PhaseValidationPolicyError(
            "clean working tree validation cannot be disabled"
        )