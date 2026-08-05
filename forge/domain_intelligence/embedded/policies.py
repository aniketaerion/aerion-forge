"""Safety policies for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.embedded.errors import (
    EmbeddedPolicyError,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
)


class EmbeddedIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_device_access: bool = False
    allow_serial_access: bool = False
    allow_firmware_flash: bool = False
    allow_build_execution: bool = False
    allow_mutation: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=10000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=5_000_000,
        ge=1,
        le=100_000_000,
    )


def resolve_embedded_repository_root(
    repository_root: str | Path,
    policy: EmbeddedIntelligencePolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise EmbeddedPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise EmbeddedPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_embedded_request(
    request: EmbeddedAnalysisRequest,
    policy: EmbeddedIntelligencePolicy,
) -> None:
    if request.max_files > policy.max_files:
        raise EmbeddedPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise EmbeddedPolicyError(
            "project root must remain repository-relative"
        )