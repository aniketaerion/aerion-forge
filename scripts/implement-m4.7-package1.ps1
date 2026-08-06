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

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\discovery.py" @'
"""Knowledge-source discovery for M4.7 Package 1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_source_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadStatus,
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    is_allowed_knowledge_path,
)

_KIND_BY_SUFFIX = {
    ".md": KnowledgeSourceKind.MARKDOWN,
    ".txt": KnowledgeSourceKind.TEXT,
    ".json": KnowledgeSourceKind.JSON,
    ".yaml": KnowledgeSourceKind.YAML,
    ".yml": KnowledgeSourceKind.YAML,
    ".toml": KnowledgeSourceKind.TOML,
    ".py": KnowledgeSourceKind.PYTHON,
}


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def knowledge_source_kind(path: Path) -> KnowledgeSourceKind:
    return _KIND_BY_SUFFIX.get(
        path.suffix.lower(),
        KnowledgeSourceKind.UNKNOWN,
    )


def discover_knowledge_sources(
    project_root: Path,
    policy: KnowledgeLoaderPolicy,
    *,
    max_files: int,
) -> tuple[KnowledgeSource, ...]:
    """Discover deterministic, policy-approved knowledge files."""
    sources: list[KnowledgeSource] = []

    for path in sorted(project_root.rglob("*")):
        if len(sources) >= max_files:
            break

        if not is_allowed_knowledge_path(path, project_root, policy):
            continue

        relative = path.relative_to(project_root).as_posix()
        size_bytes = path.stat().st_size
        content_hash = _content_hash(path)
        source_ids = tuple(
            source.source_id for source in sources
        )
        document_ids = tuple(
            document.document_id for document in documents
        )

        payload = {
            "path": relative,
            "size_bytes": size_bytes,
            "content_hash": content_hash,
        }

        sources.append(
            KnowledgeSource(
                source_id=knowledge_source_identifier(payload),
                path=relative,
                kind=knowledge_source_kind(path),
                size_bytes=size_bytes,
                content_hash=content_hash,
                status=KnowledgeLoadStatus.DISCOVERED,
            )
        )

    return tuple(sources)
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\loader.py" @'
"""Knowledge document loading for M4.7 Package 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeSourceError,
)
from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_document_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def _title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if candidate.startswith("#"):
            title = candidate.lstrip("#").strip()
            if title:
                return title
    return path.stem.replace("_", " ").replace("-", " ").strip()


def _normalized_structured_text(
    value: Any,
) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )


def load_knowledge_document(
    project_root: Path,
    source: KnowledgeSource,
) -> KnowledgeDocument:
    """Load and normalize one discovered knowledge source."""
    path = project_root / source.path

    try:
        raw = path.read_text(encoding=source.encoding)
    except (OSError, UnicodeDecodeError) as exc:
        raise KnowledgeSourceError(
            f"unable to read knowledge source: {source.path}"
        ) from exc

    try:
        if source.kind is KnowledgeSourceKind.JSON:
            text = _normalized_structured_text(json.loads(raw))
        elif source.kind is KnowledgeSourceKind.YAML:
            text = _normalized_structured_text(
                yaml.safe_load(raw)
            )
        else:
            text = raw.replace("\r\n", "\n").replace("\r", "\n")
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise KnowledgeSourceError(
            f"unable to parse knowledge source: {source.path}"
        ) from exc

    title = _title_from_text(path, text)
    source_ids = tuple(
        source.source_id for source in sources
    )
    document_ids = tuple(
        document.document_id for document in documents
    )

    payload = {
        "source_id": source.source_id,
        "title": title,
        "content_hash": source.content_hash,
    }

    return KnowledgeDocument(
        document_id=knowledge_document_identifier(payload),
        source_id=source.source_id,
        title=title,
        text=text,
        metadata={
            "path": source.path,
            "kind": source.kind.value,
            "content_hash": source.content_hash,
        },
    )


def load_knowledge_documents(
    project_root: Path,
    sources: tuple[KnowledgeSource, ...],
) -> tuple[KnowledgeDocument, ...]:
    """Load discovered sources into deterministic documents."""
    return tuple(
        load_knowledge_document(project_root, source)
        for source in sources
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\resolver.py" @'
"""Knowledge path and document resolution for M4.7 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeLoaderPolicyError,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
)


def resolve_knowledge_project_root(
    repository_root: Path,
    project_root: str,
) -> Path:
    resolved = (repository_root / project_root).resolve()

    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as exc:
        raise KnowledgeLoaderPolicyError(
            "knowledge project root escapes repository"
        ) from exc

    if not resolved.is_dir():
        raise KnowledgeLoaderPolicyError(
            f"knowledge project root does not exist: {resolved}"
        )

    return resolved


def source_by_id(
    sources: tuple[KnowledgeSource, ...],
    source_id: str,
) -> KnowledgeSource | None:
    return next(
        (
            source
            for source in sources
            if source.source_id == source_id
        ),
        None,
    )


def document_by_id(
    documents: tuple[KnowledgeDocument, ...],
    document_id: str,
) -> KnowledgeDocument | None:
    return next(
        (
            document
            for document in documents
            if document.document_id == document_id
        ),
        None,
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\manifest.py" @'
"""Knowledge manifest generation for M4.7 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_manifest_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeManifest,
    KnowledgeSource,
)


def build_knowledge_manifest(
    project_root: str,
    sources: tuple[KnowledgeSource, ...],
    documents: tuple[KnowledgeDocument, ...],
) -> KnowledgeManifest:
    source_ids = tuple(
        source.source_id for source in sources
    )
    document_ids = tuple(
        document.document_id for document in documents
    )

    payload = {
        "project_root": project_root,
        "source_ids": source_ids,
        "document_ids": document_ids,
    }

    return KnowledgeManifest(
        manifest_id=knowledge_manifest_identifier(payload),
        project_root=project_root,
        source_ids=source_ids,
        document_ids=document_ids,
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\registry.py" @'
"""Loader registry for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.loader import (
    load_knowledge_document,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)

Loader = Callable[[Path, KnowledgeSource], KnowledgeDocument]


class KnowledgeLoaderRegistry:
    """Deterministic registry of source-kind loaders."""

    def __init__(self) -> None:
        self._loaders: dict[KnowledgeSourceKind, Loader] = {}

    @classmethod
    def default(cls) -> "KnowledgeLoaderRegistry":
        registry = cls()

        for kind in (
            KnowledgeSourceKind.MARKDOWN,
            KnowledgeSourceKind.TEXT,
            KnowledgeSourceKind.JSON,
            KnowledgeSourceKind.YAML,
            KnowledgeSourceKind.TOML,
            KnowledgeSourceKind.PYTHON,
            KnowledgeSourceKind.DOCUMENTATION,
            KnowledgeSourceKind.MANIFEST,
            KnowledgeSourceKind.UNKNOWN,
        ):
            registry.register(kind, load_knowledge_document)

        return registry

    def register(
        self,
        kind: KnowledgeSourceKind,
        loader: Loader,
    ) -> None:
        self._loaders[kind] = loader

    def kinds(self) -> tuple[KnowledgeSourceKind, ...]:
        return tuple(
            sorted(
                self._loaders,
                key=lambda kind: kind.value,
            )
        )

    def load(
        self,
        project_root: Path,
        source: KnowledgeSource,
    ) -> KnowledgeDocument:
        loader = self._loaders.get(source.kind)
        if loader is None:
            loader = load_knowledge_document
        return loader(project_root, source)
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\service.py" @'
"""Knowledge loading service for M4.7 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_report_identifier,
)
from forge.domain_intelligence.knowledge_loader.manifest import (
    build_knowledge_manifest,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadReport,
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    resolve_knowledge_repository_root,
    validate_knowledge_request,
)
from forge.domain_intelligence.knowledge_loader.registry import (
    KnowledgeLoaderRegistry,
)
from forge.domain_intelligence.knowledge_loader.resolver import (
    resolve_knowledge_project_root,
)


class KnowledgeLoaderService:
    """Discover and load repository knowledge deterministically."""

    def __init__(
        self,
        *,
        policy: KnowledgeLoaderPolicy | None = None,
        registry: KnowledgeLoaderRegistry | None = None,
    ) -> None:
        self._policy = policy or KnowledgeLoaderPolicy()
        self._registry = (
            registry or KnowledgeLoaderRegistry.default()
        )

    def load(
        self,
        request: KnowledgeLoadRequest,
    ) -> KnowledgeLoadReport:
        validate_knowledge_request(request, self._policy)

        repository_root = resolve_knowledge_repository_root(
            request.repository_root,
            self._policy,
        )
        project_root = resolve_knowledge_project_root(
            repository_root,
            request.project_root,
        )

        sources = discover_knowledge_sources(
            project_root,
            self._policy,
            max_files=request.max_files,
        )
        documents = tuple(
            self._registry.load(project_root, source)
            for source in sources
        )

        relative_root = project_root.relative_to(
            repository_root
        ).as_posix()

        manifest = build_knowledge_manifest(
            relative_root,
            sources,
            documents,
        )

        source_ids = tuple(

            source.source_id for source in sources

        )

        document_ids = tuple(

            document.document_id for document in documents

        )


        payload = {
            "manifest_id": manifest.manifest_id,
            "source_ids": manifest.source_ids,
            "document_ids": manifest.document_ids,
        }

        return KnowledgeLoadReport(
            report_id=knowledge_report_identifier(payload),
            manifest=manifest,
            sources=sources,
            documents=documents,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_discovery.py" @'
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
)


def test_knowledge_source_discovery(tmp_path: Path) -> None:
    (tmp_path / "guide.md").write_text(
        "# Engineering Guide",
        encoding="utf-8",
    )
    (tmp_path / "config.json").write_text(
        '{"version": 1}',
        encoding="utf-8",
    )
    (tmp_path / "firmware.bin").write_bytes(b"\x00\x01")

    sources = discover_knowledge_sources(
        tmp_path,
        KnowledgeLoaderPolicy(),
        max_files=100,
    )

    assert len(sources) == 2
    assert {source.kind for source in sources} == {
        KnowledgeSourceKind.MARKDOWN,
        KnowledgeSourceKind.JSON,
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_loader.py" @'
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
from forge.domain_intelligence.knowledge_loader.loader import (
    load_knowledge_documents,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
)


def test_knowledge_document_loading(tmp_path: Path) -> None:
    (tmp_path / "guide.md").write_text(
        "# Flight Safety\nUse deterministic checks.",
        encoding="utf-8",
    )

    sources = discover_knowledge_sources(
        tmp_path,
        KnowledgeLoaderPolicy(),
        max_files=100,
    )
    documents = load_knowledge_documents(tmp_path, sources)

    assert len(documents) == 1
    assert documents[0].title == "Flight Safety"
    assert "deterministic checks" in documents[0].text
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_manifest.py" @'
from forge.domain_intelligence.knowledge_loader.manifest import (
    build_knowledge_manifest,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def test_knowledge_manifest_generation() -> None:
    source = KnowledgeSource(
        source_id="knowledge-source-1",
        path="guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=10,
        content_hash="abc",
    )
    document = KnowledgeDocument(
        document_id="knowledge-document-1",
        source_id=source.source_id,
        title="Guide",
        text="Text",
    )

    manifest = build_knowledge_manifest(
        ".",
        (source,),
        (document,),
    )

    assert manifest.source_ids == (source.source_id,)
    assert manifest.document_ids == (document.document_id,)
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_registry.py" @'
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.registry import (
    KnowledgeLoaderRegistry,
)


def test_default_knowledge_loader_registry() -> None:
    registry = KnowledgeLoaderRegistry.default()

    assert KnowledgeSourceKind.MARKDOWN in registry.kinds()
    assert KnowledgeSourceKind.JSON in registry.kinds()
    assert KnowledgeSourceKind.PYTHON in registry.kinds()
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_resolver.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeLoaderPolicyError,
)
from forge.domain_intelligence.knowledge_loader.resolver import (
    resolve_knowledge_project_root,
)


def test_knowledge_project_root_resolution(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()

    assert resolve_knowledge_project_root(
        tmp_path,
        "docs",
    ) == docs.resolve()


def test_knowledge_project_root_rejects_escape(
    tmp_path: Path,
) -> None:
    with pytest.raises(KnowledgeLoaderPolicyError):
        resolve_knowledge_project_root(
            tmp_path,
            "../outside",
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_service.py" @'
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.service import (
    KnowledgeLoaderService,
)


def test_knowledge_loader_service(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "# Forge Guide\nKnowledge loading.",
        encoding="utf-8",
    )

    report = KnowledgeLoaderService().load(
        KnowledgeLoadRequest(
            repository_root=str(tmp_path),
            project_root="docs",
        )
    )

    assert report.manifest.project_root == "docs"
    assert len(report.sources) == 1
    assert len(report.documents) == 1
    assert report.documents[0].title == "Forge Guide"
'@

Write-Host ""
Write-Host "M4.7 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_knowledge_loader_discovery.py `
    .\tests\test_domain_intelligence_knowledge_loader_loader.py `
    .\tests\test_domain_intelligence_knowledge_loader_manifest.py `
    .\tests\test_domain_intelligence_knowledge_loader_registry.py `
    .\tests\test_domain_intelligence_knowledge_loader_resolver.py `
    .\tests\test_domain_intelligence_knowledge_loader_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.7 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.7 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
