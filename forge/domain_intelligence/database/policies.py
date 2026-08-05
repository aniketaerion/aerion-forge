"""Safety policies for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.database.errors import DatabasePolicyError
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
)


class DatabaseIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_database_connections: bool = False
    allow_query_execution: bool = False
    allow_schema_modification: bool = False
    inspect_secrets: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=10000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=5_000_000,
        ge=1,
        le=100_000_000,
    )


def resolve_database_repository_root(
    repository_root: str | Path,
    policy: DatabaseIntelligencePolicy,
) -> Path:
    """Resolve and validate the database repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise DatabasePolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise DatabasePolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_database_request(
    request: DatabaseAnalysisRequest,
    policy: DatabaseIntelligencePolicy,
) -> None:
    """Validate database-analysis scope and bounds."""
    if request.max_files > policy.max_files:
        raise DatabasePolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise DatabasePolicyError(
            "project root must remain repository-relative"
        )