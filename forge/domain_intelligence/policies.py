"""Policies for Phase 4 domain intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.errors import DomainIntelligencePolicyError
from forge.domain_intelligence.models import FrontendAnalysisRequest


class DomainIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_source_modification: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=5000, ge=1, le=100000)


def resolve_repository_root(
    repository_root: str | Path,
    policy: DomainIntelligencePolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise DomainIntelligencePolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise DomainIntelligencePolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_frontend_request(
    request: FrontendAnalysisRequest,
    policy: DomainIntelligencePolicy,
) -> None:
    if request.max_files > policy.max_files:
        raise DomainIntelligencePolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise DomainIntelligencePolicyError(
            "project root must remain repository-relative"
        )