"""Safety policies for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.backend.errors import BackendPolicyError
from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
)


class BackendIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_process_execution: bool = False
    allow_source_modification: bool = False
    inspect_secrets: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=7500, ge=1, le=100000)


def resolve_backend_repository_root(
    repository_root: str | Path,
    policy: BackendIntelligencePolicy,
) -> Path:
    """Resolve and validate the backend repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise BackendPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise BackendPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_backend_request(
    request: BackendAnalysisRequest,
    policy: BackendIntelligencePolicy,
) -> None:
    """Validate request bounds and repository-relative scope."""
    if request.max_files > policy.max_files:
        raise BackendPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise BackendPolicyError(
            "project root must remain repository-relative"
        )