"""Safety policies for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeLoaderPolicyError,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadRequest,
)

_DEFAULT_EXCLUDED_DIRECTORIES = (
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
)

_DEFAULT_ALLOWED_SUFFIXES = (
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
)


class KnowledgeLoaderPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_mutation: bool = False
    allow_binary_files: bool = False
    allow_external_paths: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=5000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=2_000_000,
        ge=1,
        le=100_000_000,
    )
    allowed_suffixes: tuple[str, ...] = _DEFAULT_ALLOWED_SUFFIXES
    excluded_directories: tuple[str, ...] = (
        _DEFAULT_EXCLUDED_DIRECTORIES
    )


def resolve_knowledge_repository_root(
    repository_root: str | Path,
    policy: KnowledgeLoaderPolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise KnowledgeLoaderPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise KnowledgeLoaderPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_knowledge_request(
    request: KnowledgeLoadRequest,
    policy: KnowledgeLoaderPolicy,
) -> None:
    if request.max_files > policy.max_files:
        raise KnowledgeLoaderPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    if request.max_file_bytes > policy.max_file_bytes:
        raise KnowledgeLoaderPolicyError(
            "request exceeds maximum knowledge file size"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise KnowledgeLoaderPolicyError(
            "project root must remain repository-relative"
        )


def is_allowed_knowledge_path(
    path: Path,
    project_root: Path,
    policy: KnowledgeLoaderPolicy,
) -> bool:
    try:
        relative = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return False

    if any(
        part in policy.excluded_directories
        for part in relative.parts
    ):
        return False

    if not path.is_file():
        return False

    if path.suffix.lower() not in policy.allowed_suffixes:
        return False

    try:
        size = path.stat().st_size
    except OSError:
        return False

    return size <= policy.max_file_bytes