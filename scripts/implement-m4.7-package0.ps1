[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\errors.py" @'
"""Typed errors for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class KnowledgeLoaderError(DomainIntelligenceError):
    """Base error for knowledge-loader intelligence."""


class KnowledgeLoaderConfigurationError(KnowledgeLoaderError):
    """Raised when knowledge-loader configuration is invalid."""


class KnowledgeLoaderPolicyError(KnowledgeLoaderError):
    """Raised when a loader operation violates policy."""


class KnowledgeSourceError(KnowledgeLoaderError):
    """Raised when a knowledge source cannot be read or parsed."""


class KnowledgeCompatibilityError(KnowledgeLoaderError):
    """Raised when knowledge content is incompatible."""
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\identifiers.py" @'
"""Deterministic identifiers for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def knowledge_source_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-source", payload)


def knowledge_document_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-document", payload)


def knowledge_chunk_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-chunk", payload)


def knowledge_manifest_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-manifest", payload)


def knowledge_finding_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-finding", payload)


def knowledge_report_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-report", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\models.py" @'
"""Immutable contracts for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeSourceKind(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    PYTHON = "python"
    DOCUMENTATION = "documentation"
    MANIFEST = "manifest"
    UNKNOWN = "unknown"


class KnowledgeLoadStatus(StrEnum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    SKIPPED = "skipped"
    REJECTED = "rejected"
    FAILED = "failed"


class KnowledgeFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableKnowledgeModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class KnowledgeLoadRequest(ImmutableKnowledgeModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    max_files: int = Field(default=5000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=2_000_000,
        ge=1,
        le=100_000_000,
    )
    chunk_size: int = Field(default=4000, ge=128, le=50000)


class KnowledgeSource(ImmutableKnowledgeModel):
    source_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    kind: KnowledgeSourceKind
    size_bytes: int = Field(ge=0)
    content_hash: str = Field(min_length=1)
    encoding: str = Field(default="utf-8", min_length=1)
    status: KnowledgeLoadStatus = KnowledgeLoadStatus.DISCOVERED


class KnowledgeDocument(ImmutableKnowledgeModel):
    document_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class KnowledgeChunk(ImmutableKnowledgeModel):
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    token_estimate: int = Field(ge=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class KnowledgeManifest(ImmutableKnowledgeModel):
    manifest_id: str = Field(min_length=1)
    project_root: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    document_ids: tuple[str, ...] = ()
    chunk_ids: tuple[str, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator(
        "source_ids",
        "document_ids",
        "chunk_ids",
    )
    @classmethod
    def ensure_unique_identifiers(
        cls,
        identifiers: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("knowledge identifiers must be unique")
        return identifiers


class KnowledgeFinding(ImmutableKnowledgeModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: KnowledgeFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class KnowledgeLoadReport(ImmutableKnowledgeModel):
    report_id: str = Field(min_length=1)
    manifest: KnowledgeManifest
    sources: tuple[KnowledgeSource, ...] = ()
    documents: tuple[KnowledgeDocument, ...] = ()
    chunks: tuple[KnowledgeChunk, ...] = ()
    findings: tuple[KnowledgeFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[KnowledgeFinding, ...],
    ) -> tuple[KnowledgeFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "knowledge finding identifiers must be unique"
            )
        return findings
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\policies.py" @'
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
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\__init__.py" @'
"""M4.7 Knowledge Loader Intelligence public API."""

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeCompatibilityError,
    KnowledgeLoaderConfigurationError,
    KnowledgeLoaderError,
    KnowledgeLoaderPolicyError,
    KnowledgeSourceError,
)
from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_chunk_identifier,
    knowledge_document_identifier,
    knowledge_finding_identifier,
    knowledge_manifest_identifier,
    knowledge_report_identifier,
    knowledge_source_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeLoadReport,
    KnowledgeLoadRequest,
    KnowledgeLoadStatus,
    KnowledgeManifest,
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    is_allowed_knowledge_path,
    resolve_knowledge_repository_root,
    validate_knowledge_request,
)

__all__ = [
    "KnowledgeChunk",
    "KnowledgeCompatibilityError",
    "KnowledgeDocument",
    "KnowledgeFinding",
    "KnowledgeFindingSeverity",
    "KnowledgeLoadReport",
    "KnowledgeLoadRequest",
    "KnowledgeLoadStatus",
    "KnowledgeLoaderConfigurationError",
    "KnowledgeLoaderError",
    "KnowledgeLoaderPolicy",
    "KnowledgeLoaderPolicyError",
    "KnowledgeManifest",
    "KnowledgeSource",
    "KnowledgeSourceError",
    "KnowledgeSourceKind",
    "is_allowed_knowledge_path",
    "knowledge_chunk_identifier",
    "knowledge_document_identifier",
    "knowledge_finding_identifier",
    "knowledge_manifest_identifier",
    "knowledge_report_identifier",
    "knowledge_source_identifier",
    "resolve_knowledge_repository_root",
    "validate_knowledge_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_identifiers.py" @'
from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_chunk_identifier,
    knowledge_source_identifier,
)


def test_knowledge_source_identifier_is_deterministic() -> None:
    first = knowledge_source_identifier(
        {"path": "docs/guide.md", "hash": "abc"}
    )
    second = knowledge_source_identifier(
        {"hash": "abc", "path": "docs/guide.md"}
    )

    assert first == second
    assert first.startswith("knowledge-source-")


def test_knowledge_chunk_identifier_changes_by_ordinal() -> None:
    first = knowledge_chunk_identifier(
        {"document_id": "doc-1", "ordinal": 0}
    )
    second = knowledge_chunk_identifier(
        {"document_id": "doc-1", "ordinal": 1}
    )

    assert first != second
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeLoadReport,
    KnowledgeManifest,
)


def test_knowledge_chunk_is_immutable() -> None:
    chunk = KnowledgeChunk(
        chunk_id="knowledge-chunk-1",
        document_id="knowledge-document-1",
        ordinal=0,
        text="Engineering knowledge.",
        token_estimate=4,
    )

    with pytest.raises(ValidationError):
        chunk.text = "Changed"


def test_knowledge_manifest_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        KnowledgeManifest(
            manifest_id="knowledge-manifest-1",
            project_root=".",
            source_ids=("source-1", "source-1"),
        )


def test_knowledge_report_rejects_duplicate_findings() -> None:
    manifest = KnowledgeManifest(
        manifest_id="knowledge-manifest-1",
        project_root=".",
    )
    finding = KnowledgeFinding(
        finding_id="knowledge-finding-1",
        category="compatibility",
        severity=KnowledgeFindingSeverity.MEDIUM,
        message="Unsupported schema version.",
    )

    with pytest.raises(ValidationError):
        KnowledgeLoadReport(
            report_id="knowledge-report-1",
            manifest=manifest,
            findings=(finding, finding),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeLoaderPolicyError,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    is_allowed_knowledge_path,
    resolve_knowledge_repository_root,
    validate_knowledge_request,
)


def test_knowledge_loader_policy_is_offline_read_only() -> None:
    policy = KnowledgeLoaderPolicy()

    assert not policy.allow_network
    assert not policy.allow_mutation
    assert not policy.allow_binary_files
    assert not policy.allow_external_paths


def test_knowledge_repository_requires_git(
    tmp_path: Path,
) -> None:
    with pytest.raises(KnowledgeLoaderPolicyError):
        resolve_knowledge_repository_root(
            tmp_path,
            KnowledgeLoaderPolicy(),
        )


def test_knowledge_request_rejects_path_escape() -> None:
    request = KnowledgeLoadRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(KnowledgeLoaderPolicyError):
        validate_knowledge_request(
            request,
            KnowledgeLoaderPolicy(),
        )


def test_allowed_knowledge_path_filters_binary_and_cache(
    tmp_path: Path,
) -> None:
    markdown = tmp_path / "guide.md"
    markdown.write_text("# Guide", encoding="utf-8")

    binary = tmp_path / "firmware.bin"
    binary.write_bytes(b"\x00\x01")

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    cached = cache / "data.json"
    cached.write_text("{}", encoding="utf-8")

    policy = KnowledgeLoaderPolicy()

    assert is_allowed_knowledge_path(
        markdown,
        tmp_path,
        policy,
    )
    assert not is_allowed_knowledge_path(
        binary,
        tmp_path,
        policy,
    )
    assert not is_allowed_knowledge_path(
        cached,
        tmp_path,
        policy,
    )
'@

Write-Utf8NoBom "docs\domain_intelligence\knowledge_loader\ARCHITECTURE.md" @'
# M4.7 Knowledge Loader Intelligence Architecture

M4.7 provides deterministic, offline, read-only loading of repository
knowledge into typed sources, documents, chunks, manifests, findings, and
reports.

Package 0 establishes immutable contracts, deterministic identifiers, typed
errors, file-policy boundaries, repository containment, and safe defaults.
'@

Write-Utf8NoBom "docs\domain_intelligence\knowledge_loader\SPECIFICATION.md" @'
# M4.7 Knowledge Loader Intelligence Specification

The subsystem shall discover, validate, load, normalize, chunk, cache,
version, resolve, and report repository knowledge without network access,
binary ingestion, source mutation, or external-path traversal.
'@

Write-Utf8NoBom "docs\domain_intelligence\knowledge_loader\DATA_MODEL.md" @'
# M4.7 Knowledge Loader Intelligence Data Model

Core models:

- `KnowledgeLoadRequest`
- `KnowledgeSource`
- `KnowledgeDocument`
- `KnowledgeChunk`
- `KnowledgeManifest`
- `KnowledgeFinding`
- `KnowledgeLoadReport`

All models are immutable and reject unknown fields.
'@

Write-Utf8NoBom "docs\domain_intelligence\knowledge_loader\SECURITY_MODEL.md" @'
# M4.7 Knowledge Loader Intelligence Security Model

Knowledge loading is offline and read-only by default.

The policy prohibits network use, repository mutation, binary ingestion,
external paths, oversized files, and traversal outside the selected project
root. Generated caches and reports must remain derived artifacts.
'@

Write-Utf8NoBom "docs\domain_intelligence\knowledge_loader\ACCEPTANCE_CRITERIA.md" @'
# M4.7 Package 0 Acceptance Criteria

- Typed knowledge-loader errors exist.
- Stable identifiers are deterministic.
- Models are immutable and validated.
- Duplicate identifiers are rejected.
- Policies prohibit network use and mutation.
- Binary, cached, external, and oversized files are rejected.
- Repository and project-root boundaries are enforced.
- Ruff, MyPy, focused tests, and the complete test suite pass.
'@

Write-Host ""
Write-Host "M4.7 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_knowledge_loader_identifiers.py `
    .\tests\test_domain_intelligence_knowledge_loader_models.py `
    .\tests\test_domain_intelligence_knowledge_loader_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.7 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.7 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short