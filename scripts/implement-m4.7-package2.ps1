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

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\cache.py" @'
"""Deterministic cache support for M4.7 Package 2."""

from __future__ import annotations

import json
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadReport,
)


class KnowledgeCache:
    """Read and write derived knowledge-loader cache files."""

    def __init__(self, cache_root: Path) -> None:
        self._cache_root = cache_root

    def report_path(self, report_id: str) -> Path:
        return self._cache_root / f"{report_id}.json"

    def write(self, report: KnowledgeLoadReport) -> Path:
        self._cache_root.mkdir(parents=True, exist_ok=True)
        path = self.report_path(report.report_id)
        path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def read(self, report_id: str) -> KnowledgeLoadReport | None:
        path = self.report_path(report_id)
        if not path.is_file():
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        return KnowledgeLoadReport.model_validate(payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\versioning.py" @'
"""Knowledge-source versioning for M4.7 Package 2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSource,
)


@dataclass(frozen=True, slots=True)
class KnowledgeSourceVersion:
    source_id: str
    path: str
    content_hash: str


def source_version(
    source: KnowledgeSource,
) -> KnowledgeSourceVersion:
    return KnowledgeSourceVersion(
        source_id=source.source_id,
        path=source.path,
        content_hash=source.content_hash,
    )


def changed_source_paths(
    previous: tuple[KnowledgeSource, ...],
    current: tuple[KnowledgeSource, ...],
) -> tuple[str, ...]:
    previous_by_path = {
        source.path: source.content_hash
        for source in previous
    }
    current_by_path = {
        source.path: source.content_hash
        for source in current
    }

    paths = set(previous_by_path) | set(current_by_path)

    return tuple(
        sorted(
            path
            for path in paths
            if previous_by_path.get(path)
            != current_by_path.get(path)
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\compatibility.py" @'
"""Compatibility analysis for M4.7 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_finding_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def analyze_knowledge_compatibility(
    sources: tuple[KnowledgeSource, ...],
    documents: tuple[KnowledgeDocument, ...],
) -> tuple[KnowledgeFinding, ...]:
    findings: list[KnowledgeFinding] = []
    documents_by_source = {
        document.source_id: document
        for document in documents
    }

    for source in sources:
        document = documents_by_source.get(source.source_id)

        if document is None:
            payload = {
                "category": "missing-document",
                "path": source.path,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="missing-document",
                    severity=KnowledgeFindingSeverity.HIGH,
                    message="Discovered source has no loaded document.",
                    path=source.path,
                )
            )
            continue

        if source.kind is KnowledgeSourceKind.UNKNOWN:
            payload = {
                "category": "unknown-source-kind",
                "path": source.path,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="unknown-source-kind",
                    severity=KnowledgeFindingSeverity.LOW,
                    message="Knowledge source kind is unknown.",
                    path=source.path,
                )
            )

        if not document.text.strip():
            payload = {
                "category": "empty-document",
                "path": source.path,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="empty-document",
                    severity=KnowledgeFindingSeverity.MEDIUM,
                    message="Knowledge document is empty.",
                    path=source.path,
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.severity.value,
                finding.category,
                finding.path or "",
            ),
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\validation.py" @'
"""Validation helpers for M4.7 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_finding_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFinding,
    KnowledgeFindingSeverity,
)


def validate_documents(
    documents: tuple[KnowledgeDocument, ...],
) -> tuple[KnowledgeFinding, ...]:
    findings: list[KnowledgeFinding] = []

    for document in documents:
        if not document.title.strip():
            payload = {
                "category": "missing-title",
                "document_id": document.document_id,
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="missing-title",
                    severity=KnowledgeFindingSeverity.LOW,
                    message="Knowledge document has no title.",
                    path=document.metadata.get("path"),
                )
            )

    return tuple(findings)


def validate_chunks(
    chunks: tuple[KnowledgeChunk, ...],
) -> tuple[KnowledgeFinding, ...]:
    findings: list[KnowledgeFinding] = []

    ordinals_by_document: dict[str, list[int]] = {}

    for chunk in chunks:
        ordinals_by_document.setdefault(
            chunk.document_id,
            [],
        ).append(chunk.ordinal)

    for document_id, ordinals in sorted(
        ordinals_by_document.items()
    ):
        expected = list(range(len(ordinals)))
        actual = sorted(ordinals)

        if actual != expected:
            payload = {
                "category": "chunk-ordinal-gap",
                "document_id": document_id,
                "actual": tuple(actual),
            }
            findings.append(
                KnowledgeFinding(
                    finding_id=knowledge_finding_identifier(payload),
                    category="chunk-ordinal-gap",
                    severity=KnowledgeFindingSeverity.MEDIUM,
                    message=(
                        "Knowledge chunk ordinals are not contiguous."
                    ),
                )
            )

    return tuple(findings)
'@

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\chunking.py" @'
"""Knowledge document chunking for M4.7 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_chunk_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
    KnowledgeDocument,
)


def _token_estimate(text: str) -> int:
    return max(1, len(text.split()))


def chunk_document(
    document: KnowledgeDocument,
    *,
    chunk_size: int,
) -> tuple[KnowledgeChunk, ...]:
    text = document.text.strip()
    if not text:
        return ()

    chunks: list[KnowledgeChunk] = []

    for ordinal, start in enumerate(range(0, len(text), chunk_size)):
        chunk_text = text[start : start + chunk_size].strip()
        if not chunk_text:
            continue

        payload = {
            "document_id": document.document_id,
            "ordinal": ordinal,
            "text": chunk_text,
        }

        chunks.append(
            KnowledgeChunk(
                chunk_id=knowledge_chunk_identifier(payload),
                document_id=document.document_id,
                ordinal=ordinal,
                text=chunk_text,
                token_estimate=_token_estimate(chunk_text),
                metadata={
                    "source_id": document.source_id,
                    **document.metadata,
                },
            )
        )

    return tuple(chunks)


def chunk_documents(
    documents: tuple[KnowledgeDocument, ...],
    *,
    chunk_size: int,
) -> tuple[KnowledgeChunk, ...]:
    return tuple(
        chunk
        for document in documents
        for chunk in chunk_document(
            document,
            chunk_size=chunk_size,
        )
    )
'@

$ServicePath = ".\forge\domain_intelligence\knowledge_loader\service.py"
$ServiceContent = Get-Content $ServicePath -Raw

$ImportAnchor = @'
from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
'@

$ImportBlock = @'
from forge.domain_intelligence.knowledge_loader.chunking import (
    chunk_documents,
)
from forge.domain_intelligence.knowledge_loader.compatibility import (
    analyze_knowledge_compatibility,
)
from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
from forge.domain_intelligence.knowledge_loader.validation import (
    validate_chunks,
    validate_documents,
)
'@

if (
    $ServiceContent -notmatch
    'from forge\.domain_intelligence\.knowledge_loader\.chunking import'
) {
    if (-not $ServiceContent.Contains($ImportAnchor)) {
        throw "Service import anchor not found."
    }

    $ServiceContent = $ServiceContent.Replace(
        $ImportAnchor,
        $ImportBlock
    )
}

$Old = @'
        manifest = build_knowledge_manifest(
            relative_root,
            sources,
            documents,
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

$New = @'
        chunks = chunk_documents(
            documents,
            chunk_size=request.chunk_size,
        )

        manifest = build_knowledge_manifest(
            relative_root,
            sources,
            documents,
        ).model_copy(
            update={
                "chunk_ids": tuple(
                    chunk.chunk_id for chunk in chunks
                )
            }
        )

        findings = (
            *analyze_knowledge_compatibility(
                sources,
                documents,
            ),
            *validate_documents(documents),
            *validate_chunks(chunks),
        )

        payload = {
            "manifest_id": manifest.manifest_id,
            "source_ids": manifest.source_ids,
            "document_ids": manifest.document_ids,
            "chunk_ids": manifest.chunk_ids,
            "finding_ids": tuple(
                finding.finding_id for finding in findings
            ),
        }

        return KnowledgeLoadReport(
            report_id=knowledge_report_identifier(payload),
            manifest=manifest,
            sources=sources,
            documents=documents,
            chunks=chunks,
            findings=findings,
        )
'@

if (-not $ServiceContent.Contains($Old)) {
    throw "Service report block not found."
}

$ServiceContent = $ServiceContent.Replace($Old, $New)

[System.IO.File]::WriteAllText(
    (Resolve-Path $ServicePath),
    $ServiceContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\domain_intelligence\knowledge_loader\service.py" -ForegroundColor Green

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_cache.py" @'
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.cache import (
    KnowledgeCache,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadReport,
    KnowledgeManifest,
)


def test_knowledge_cache_round_trip(tmp_path: Path) -> None:
    report = KnowledgeLoadReport(
        report_id="knowledge-report-1",
        manifest=KnowledgeManifest(
            manifest_id="knowledge-manifest-1",
            project_root=".",
        ),
    )
    cache = KnowledgeCache(tmp_path)

    path = cache.write(report)
    loaded = cache.read(report.report_id)

    assert path.is_file()
    assert loaded == report
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_versioning.py" @'
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.versioning import (
    changed_source_paths,
)


def source(path: str, content_hash: str) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=f"source-{path}-{content_hash}",
        path=path,
        kind=KnowledgeSourceKind.TEXT,
        size_bytes=10,
        content_hash=content_hash,
    )


def test_changed_source_paths() -> None:
    previous = (
        source("a.txt", "one"),
        source("b.txt", "same"),
    )
    current = (
        source("a.txt", "two"),
        source("b.txt", "same"),
        source("c.txt", "new"),
    )

    assert changed_source_paths(previous, current) == (
        "a.txt",
        "c.txt",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_compatibility.py" @'
from forge.domain_intelligence.knowledge_loader.compatibility import (
    analyze_knowledge_compatibility,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def test_compatibility_detects_missing_document() -> None:
    source = KnowledgeSource(
        source_id="source-1",
        path="guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=10,
        content_hash="abc",
    )

    findings = analyze_knowledge_compatibility(
        (source,),
        (),
    )

    assert findings[0].category == "missing-document"


def test_compatibility_detects_empty_document() -> None:
    source = KnowledgeSource(
        source_id="source-1",
        path="guide.md",
        kind=KnowledgeSourceKind.MARKDOWN,
        size_bytes=0,
        content_hash="abc",
    )
    document = KnowledgeDocument(
        document_id="document-1",
        source_id=source.source_id,
        title="Guide",
        text="",
    )

    findings = analyze_knowledge_compatibility(
        (source,),
        (document,),
    )

    assert findings[0].category == "empty-document"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_validation.py" @'
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
)
from forge.domain_intelligence.knowledge_loader.validation import (
    validate_chunks,
)


def test_validation_detects_chunk_ordinal_gap() -> None:
    chunks = (
        KnowledgeChunk(
            chunk_id="chunk-1",
            document_id="document-1",
            ordinal=0,
            text="First",
            token_estimate=1,
        ),
        KnowledgeChunk(
            chunk_id="chunk-2",
            document_id="document-1",
            ordinal=2,
            text="Third",
            token_estimate=1,
        ),
    )

    findings = validate_chunks(chunks)

    assert findings[0].category == "chunk-ordinal-gap"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_chunking.py" @'
from forge.domain_intelligence.knowledge_loader.chunking import (
    chunk_document,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
)


def test_document_chunking_is_deterministic() -> None:
    document = KnowledgeDocument(
        document_id="document-1",
        source_id="source-1",
        title="Guide",
        text="abcdefghij",
    )

    chunks = chunk_document(document, chunk_size=4)

    assert [chunk.text for chunk in chunks] == [
        "abcd",
        "efgh",
        "ij",
    ]
    assert [chunk.ordinal for chunk in chunks] == [0, 1, 2]
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
            chunk_size=128,
        )
    )

    assert report.manifest.project_root == "docs"
    assert len(report.sources) == 1
    assert len(report.documents) == 1
    assert len(report.chunks) >= 1
    assert report.manifest.chunk_ids == tuple(
        chunk.chunk_id for chunk in report.chunks
    )
'@

Write-Host ""
Write-Host "M4.7 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_knowledge_loader_cache.py `
    .\tests\test_domain_intelligence_knowledge_loader_versioning.py `
    .\tests\test_domain_intelligence_knowledge_loader_compatibility.py `
    .\tests\test_domain_intelligence_knowledge_loader_validation.py `
    .\tests\test_domain_intelligence_knowledge_loader_chunking.py `
    .\tests\test_domain_intelligence_knowledge_loader_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.7 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.7 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short
