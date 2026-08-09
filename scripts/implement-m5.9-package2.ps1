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

$ExpectedBranch = "feature/m5.9-general-engineering-agent"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.9 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

if (-not (Test-Path ".\forge\general_engineering\request_understanding.py")) {
    throw "M5.9 Package 1 prerequisite is missing."
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.9 Package 2."
}

Write-Utf8NoBom "forge\general_engineering\repository_scanner.py" @'
"""Read-only repository scanning for M5.9 Package 2."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


_DEFAULT_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "coverage",
    }
)

_DEFAULT_TEXT_SUFFIXES = frozenset(
    {
        ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt",
        ".dart", ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".hpp",
        ".cs", ".php", ".rb", ".swift", ".sql", ".sh", ".ps1", ".md",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml",
        ".html", ".css", ".scss", ".vue", ".svelte",
    }
)


@dataclass(frozen=True)
class ScannedRepositoryFile:
    path: str
    size_bytes: int
    suffix: str
    fingerprint: str
    content: str


def _fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_repository(
    repository_root: str | Path,
    *,
    max_file_bytes: int = 1_000_000,
    max_files: int = 5000,
) -> tuple[ScannedRepositoryFile, ...]:
    """Read eligible text files without mutating the repository."""
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise ValueError(f"Repository root does not exist: {root}")

    scanned: list[ScannedRepositoryFile] = []
    for path in sorted(root.rglob("*")):
        if len(scanned) >= max_files:
            break
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in _DEFAULT_IGNORED_DIRS for part in relative.parts):
            continue
        suffix = path.suffix.casefold()
        if suffix not in _DEFAULT_TEXT_SUFFIXES and path.name not in {
            "Dockerfile", "Makefile", "CMakeLists.txt",
        }:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_file_bytes:
            continue
        try:
            data = path.read_bytes()
            content = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned.append(
            ScannedRepositoryFile(
                path=relative.as_posix(),
                size_bytes=size,
                suffix=suffix,
                fingerprint=_fingerprint(data),
                content=content,
            )
        )
    return tuple(scanned)
'@

Write-Utf8NoBom "forge\general_engineering\symbol_discovery.py" @'
"""Read-only symbol discovery for M5.9 Package 2."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from forge.general_engineering.repository_scanner import ScannedRepositoryFile


@dataclass(frozen=True)
class DiscoveredSymbol:
    name: str
    kind: str
    path: str
    line: int | None


_GENERIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("class", re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
    ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
    ("type", re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*=", re.MULTILINE)),
)


def _python_symbols(file: ScannedRepositoryFile) -> tuple[DiscoveredSymbol, ...]:
    try:
        tree = ast.parse(file.content)
    except SyntaxError:
        return ()
    result: list[DiscoveredSymbol] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            result.append(DiscoveredSymbol(node.name, "class", file.path, node.lineno))
        elif isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            result.append(DiscoveredSymbol(node.name, "function", file.path, node.lineno))
    return tuple(sorted(result, key=lambda item: (item.line or 0, item.name)))


def discover_symbols(file: ScannedRepositoryFile) -> tuple[DiscoveredSymbol, ...]:
    if file.suffix in {".py", ".pyi"}:
        return _python_symbols(file)

    result: list[DiscoveredSymbol] = []
    for kind, pattern in _GENERIC_PATTERNS:
        for match in pattern.finditer(file.content):
            line = file.content.count("\n", 0, match.start()) + 1
            result.append(DiscoveredSymbol(match.group(1), kind, file.path, line))
    return tuple(sorted(result, key=lambda item: (item.line or 0, item.name)))
'@

Write-Utf8NoBom "forge\general_engineering\relevance.py" @'
"""Deterministic relevance scoring for repository grounding."""

from __future__ import annotations

import re
from dataclasses import dataclass

from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.symbol_discovery import DiscoveredSymbol


_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_STOP = frozenset({
    "add", "and", "the", "for", "with", "from", "into", "when", "then",
    "create", "update", "change", "modify", "implement", "make", "ensure",
})


@dataclass(frozen=True)
class RelevanceScore:
    path: str
    score: float
    matched_terms: tuple[str, ...]
    matched_symbols: tuple[str, ...]


def objective_terms(objective: str) -> tuple[str, ...]:
    terms = {token.casefold() for token in _TOKEN.findall(objective)}
    return tuple(sorted(term for term in terms if term not in _STOP))


def score_file_relevance(
    objective: str,
    file: ScannedRepositoryFile,
    symbols: tuple[DiscoveredSymbol, ...],
) -> RelevanceScore:
    terms = objective_terms(objective)
    path_text = file.path.casefold()
    content_text = file.content.casefold()
    symbol_map = {symbol.name.casefold(): symbol.name for symbol in symbols}

    matched_terms: list[str] = []
    matched_symbols: list[str] = []
    score = 0.0

    for term in terms:
        matched = False
        if term in path_text:
            score += 4.0
            matched = True
        if term in symbol_map:
            score += 5.0
            matched_symbols.append(symbol_map[term])
            matched = True
        occurrences = content_text.count(term)
        if occurrences:
            score += min(3.0, occurrences * 0.5)
            matched = True
        if matched:
            matched_terms.append(term)

    if file.path.casefold().startswith("tests/") or "/test" in file.path.casefold():
        if any(term in content_text for term in terms):
            score += 1.0

    normalized = min(1.0, score / 12.0)
    return RelevanceScore(
        path=file.path,
        score=normalized,
        matched_terms=tuple(sorted(set(matched_terms))),
        matched_symbols=tuple(sorted(set(matched_symbols))),
    )
'@

Write-Utf8NoBom "forge\general_engineering\context_builder.py" @'
"""Build EngineeringContext from repository-grounding evidence."""

from __future__ import annotations

from forge.general_engineering.identifiers import repository_evidence_identifier
from forge.general_engineering.models import (
    EngineeringContext,
    EngineeringRequest,
    RelevantFile,
    RelevantSymbol,
    RepositoryEvidence,
)
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.states import EvidenceType
from forge.general_engineering.symbol_discovery import DiscoveredSymbol


def build_engineering_context(
    *,
    request: EngineeringRequest,
    files: tuple[ScannedRepositoryFile, ...],
    symbol_map: dict[str, tuple[DiscoveredSymbol, ...]],
    scores: tuple[RelevanceScore, ...],
    minimum_relevance: float = 0.10,
    max_relevant_files: int = 20,
) -> EngineeringContext:
    by_path = {item.path: item for item in files}
    selected_scores = [item for item in scores if item.score >= minimum_relevance]
    selected_scores.sort(key=lambda item: (-item.score, item.path))
    selected_scores = selected_scores[:max_relevant_files]

    evidence: list[RepositoryEvidence] = []
    relevant_files: list[RelevantFile] = []

    for score in selected_scores:
        file = by_path[score.path]
        rationale = (
            f"Matched objective terms: {', '.join(score.matched_terms) or 'none'}; "
            f"relevance={score.score:.3f}."
        )
        evidence_payload = {
            "request_id": request.request_id,
            "path": file.path,
            "fingerprint": file.fingerprint,
            "score": score.score,
            "terms": score.matched_terms,
        }
        evidence_id = repository_evidence_identifier(evidence_payload)
        evidence.append(
            RepositoryEvidence(
                evidence_id=evidence_id,
                path=file.path,
                evidence_type=EvidenceType.FILE,
                rationale=rationale,
                relevance=score.score,
                fingerprint=file.fingerprint,
                provenance=("repository_scan", "deterministic_relevance"),
            )
        )

        relevant_symbols: list[RelevantSymbol] = []
        for symbol in symbol_map.get(file.path, ()):
            if symbol.name in score.matched_symbols or any(
                term in symbol.name.casefold() for term in score.matched_terms
            ):
                relevant_symbols.append(
                    RelevantSymbol(
                        name=symbol.name,
                        kind=symbol.kind,
                        path=file.path,
                        evidence_ids=(evidence_id,),
                        rationale="Symbol name matches objective-grounding terms.",
                    )
                )

        relevant_files.append(
            RelevantFile(
                path=file.path,
                evidence_ids=(evidence_id,),
                rationale=rationale,
                symbols=tuple(relevant_symbols),
            )
        )

    return EngineeringContext(
        request_id=request.request_id,
        relevant_files=tuple(relevant_files),
        evidence=tuple(evidence),
    )
'@

Write-Utf8NoBom "forge\general_engineering\repository_grounding.py" @'
"""Repository-grounding orchestration for M5.9 Package 2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.errors import EngineeringEvidenceError
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.models import EngineeringContext, EngineeringRequest
from forge.general_engineering.repository_scanner import scan_repository
from forge.general_engineering.relevance import score_file_relevance
from forge.general_engineering.symbol_discovery import discover_symbols


@dataclass(frozen=True)
class RepositoryGroundingResult:
    context: EngineeringContext
    scanned_file_count: int
    relevant_file_count: int


class RepositoryGroundingService:
    """Create read-only, evidence-backed EngineeringContext."""

    def ground(self, request: EngineeringRequest) -> RepositoryGroundingResult:
        files = scan_repository(request.repository_root)
        if not files:
            raise EngineeringEvidenceError("Repository scan produced no readable files.")

        symbol_map = {file.path: discover_symbols(file) for file in files}
        scores = tuple(
            score_file_relevance(request.objective, file, symbol_map[file.path])
            for file in files
        )
        context = build_engineering_context(
            request=request,
            files=files,
            symbol_map=symbol_map,
            scores=scores,
        )
        if not context.relevant_files:
            raise EngineeringEvidenceError(
                "Repository grounding found no evidence-backed relevant files."
            )
        return RepositoryGroundingResult(
            context=context,
            scanned_file_count=len(files),
            relevant_file_count=len(context.relevant_files),
        )


repository_grounding_service = RepositoryGroundingService()
'@

Write-Utf8NoBom "tests\test_general_engineering_repository_scanner.py" @'
from pathlib import Path

from forge.general_engineering.repository_scanner import scan_repository


def test_scanner_reads_text_and_ignores_git(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret\n", encoding="utf-8")

    files = scan_repository(tmp_path)
    assert tuple(item.path for item in files) == ("src/service.py",)
    assert len(files[0].fingerprint) == 64
'@

Write-Utf8NoBom "tests\test_general_engineering_symbol_discovery.py" @'
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.symbol_discovery import discover_symbols


def test_python_symbol_discovery_is_read_only_and_structured() -> None:
    file = ScannedRepositoryFile(
        path="src/service.py",
        size_bytes=50,
        suffix=".py",
        fingerprint="abc",
        content="class AccountService:\n    def validate(self):\n        return True\n",
    )
    symbols = discover_symbols(file)
    assert {item.name for item in symbols} == {"AccountService", "validate"}
'@

Write-Utf8NoBom "tests\test_general_engineering_relevance.py" @'
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.relevance import score_file_relevance
from forge.general_engineering.symbol_discovery import discover_symbols


def test_relevance_prefers_matching_repository_evidence() -> None:
    relevant = ScannedRepositoryFile(
        path="src/invoice_service.py",
        size_bytes=30,
        suffix=".py",
        fingerprint="a",
        content="def approve_invoice():\n    pass\n",
    )
    unrelated = ScannedRepositoryFile(
        path="src/logger.py",
        size_bytes=20,
        suffix=".py",
        fingerprint="b",
        content="def log_event():\n    pass\n",
    )
    a = score_file_relevance("Approve invoice", relevant, discover_symbols(relevant))
    b = score_file_relevance("Approve invoice", unrelated, discover_symbols(unrelated))
    assert a.score > b.score
'@

Write-Utf8NoBom "tests\test_general_engineering_context_builder.py" @'
from pathlib import Path

from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.request_builder import build_engineering_request


def test_context_contains_traceable_repository_evidence(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update invoice approval",
        repository_root=tmp_path,
    )
    file = ScannedRepositoryFile(
        path="src/invoice.py",
        size_bytes=10,
        suffix=".py",
        fingerprint="abc",
        content="pass\n",
    )
    score = RelevanceScore(
        path=file.path,
        score=0.8,
        matched_terms=("invoice",),
        matched_symbols=(),
    )
    context = build_engineering_context(
        request=request,
        files=(file,),
        symbol_map={file.path: ()},
        scores=(score,),
    )
    assert context.relevant_files[0].path == "src/invoice.py"
    assert context.evidence[0].fingerprint == "abc"
'@

Write-Utf8NoBom "tests\test_general_engineering_repository_grounding.py" @'
from pathlib import Path

from forge.general_engineering.repository_grounding import RepositoryGroundingService
from forge.general_engineering.request_builder import build_engineering_request


def test_grounding_selects_relevant_file_without_task_specific_logic(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "shipment_service.py").write_text(
        "def schedule_shipment():\n    return 'scheduled'\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "logger.py").write_text(
        "def log_event():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_shipment.py").write_text(
        "def test_schedule_shipment():\n    pass\n",
        encoding="utf-8",
    )

    request = build_engineering_request(
        objective="Change shipment scheduling behavior and update shipment tests",
        repository_root=tmp_path,
    )
    result = RepositoryGroundingService().ground(request)
    paths = {item.path for item in result.context.relevant_files}
    assert "src/shipment_service.py" in paths
    assert "tests/test_shipment.py" in paths
    assert "src/logger.py" not in paths
'@

Write-Utf8NoBom "scripts\validate-m5.9-package2.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @("feature/m5.9-general-engineering-agent", "main")
$CurrentBranch = git branch --show-current
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 2 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Files = @(
    ".\forge\general_engineering\repository_scanner.py",
    ".\forge\general_engineering\symbol_discovery.py",
    ".\forge\general_engineering\relevance.py",
    ".\forge\general_engineering\context_builder.py",
    ".\forge\general_engineering\repository_grounding.py",
    ".\tests\test_general_engineering_repository_scanner.py",
    ".\tests\test_general_engineering_symbol_discovery.py",
    ".\tests\test_general_engineering_relevance.py",
    ".\tests\test_general_engineering_context_builder.py",
    ".\tests\test_general_engineering_repository_grounding.py"
)
foreach ($Path in $Files) {
    if (-not (Test-Path $Path)) { throw "Missing Package 2 file: $Path" }
    if ((Get-Item $Path).Length -eq 0) { throw "Empty Package 2 file: $Path" }
}

$Core = $Files[0..4]
$Forbidden = Select-String -Path $Core -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" -ErrorAction SilentlyContinue
if ($Forbidden) {
    $Forbidden
    throw "Package 2 contains forbidden mutation/execution authority."
}

$Specific = Select-String -Path $Core -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service|shipment_service" -ErrorAction SilentlyContinue
if ($Specific) {
    $Specific
    throw "Package 2 contains task-specific acceptance logic."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 2 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Grounding modules: 5"
Write-Host "Focused test files: 5"
Write-Host "Repository mutation authority: NONE"
'@

Write-Host ""
Write-Host "M5.9 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff"
python -m mypy .
Assert-CommandSuccess "MyPy"
python -m pytest `
    .\tests\test_general_engineering_repository_scanner.py `
    .\tests\test_general_engineering_symbol_discovery.py `
    .\tests\test_general_engineering_relevance.py `
    .\tests\test_general_engineering_context_builder.py `
    .\tests\test_general_engineering_repository_grounding.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.9 Package 2 focused tests"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.9-package2.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.9 Package 2 validation"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository regression"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "M5.9 PACKAGE 2 REPOSITORY GROUNDING COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "Package 2 is read-only. It does not synthesize or execute edits." -ForegroundColor Yellow
Write-Host ""
git status --short
