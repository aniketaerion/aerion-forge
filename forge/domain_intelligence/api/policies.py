"""Safety policies for M4.4 API Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.api.errors import ApiPolicyError
from forge.domain_intelligence.api.models import ApiAnalysisRequest


class ApiIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_remote_schema_fetch: bool = False
    allow_request_execution: bool = False
    allow_secret_inspection: bool = False
    allow_mutation: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=10000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=5_000_000,
        ge=1,
        le=100_000_000,
    )


def resolve_api_repository_root(
    repository_root: str | Path,
    policy: ApiIntelligencePolicy,
) -> Path:
    """Resolve and validate the API repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise ApiPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise ApiPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_api_request(
    request: ApiAnalysisRequest,
    policy: ApiIntelligencePolicy,
) -> None:
    """Validate API-analysis scope and bounds."""
    if request.max_files > policy.max_files:
        raise ApiPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise ApiPolicyError(
            "project root must remain repository-relative"
        )