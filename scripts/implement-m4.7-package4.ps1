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

Write-Utf8NoBom "forge\domain_intelligence\knowledge_loader\cli.py" @'
"""CLI for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.reporting import (
    knowledge_loader_report_summary,
    write_knowledge_loader_report_bundle,
)
from forge.domain_intelligence.knowledge_loader.service import (
    KnowledgeLoaderService,
)

knowledge_loader_app = typer.Typer(
    help=(
        "Discover, load, normalize, chunk, validate, cache, "
        "version, and report repository knowledge."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
    chunk_size: int,
) -> KnowledgeLoadRequest:
    return KnowledgeLoadRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
        chunk_size=chunk_size,
    )


@knowledge_loader_app.command("load")
def load_knowledge(
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            help="Git repository root.",
        ),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option(
            "--project-root",
            help="Repository-relative knowledge root.",
        ),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option(
            "--chunk-size",
            min=128,
            max=50000,
            help="Maximum characters per chunk.",
        ),
    ] = 4000,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete JSON report.",
        ),
    ] = False,
) -> None:
    """Load and analyze repository knowledge."""
    report = KnowledgeLoaderService().load(
        _request(
            repository_root,
            project_root,
            chunk_size,
        )
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = knowledge_loader_report_summary(report)

    table = Table(title="Knowledge Loader Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project root", str(summary["project_root"]))
    table.add_row("Sources", str(summary["source_count"]))
    table.add_row("Documents", str(summary["document_count"]))
    table.add_row("Chunks", str(summary["chunk_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    table.add_row(
        "Source bytes",
        str(summary["total_source_bytes"]),
    )
    table.add_row(
        "Estimated tokens",
        str(summary["total_chunk_tokens"]),
    )

    console.print(table)


@knowledge_loader_app.command("summary")
def summarize_knowledge(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option("--chunk-size", min=128, max=50000),
    ] = 4000,
) -> None:
    """Print a concise knowledge-loader summary."""
    report = KnowledgeLoaderService().load(
        _request(
            repository_root,
            project_root,
            chunk_size,
        )
    )

    console.print_json(
        json.dumps(
            knowledge_loader_report_summary(report),
            sort_keys=True,
        )
    )


@knowledge_loader_app.command("report")
def report_knowledge(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option("--chunk-size", min=128, max=50000),
    ] = 4000,
    destination: Annotated[
        Path,
        typer.Option(
            "--destination",
            help="Repository-relative report destination.",
        ),
    ] = Path("reports/latest/knowledge-loader"),
) -> None:
    """Generate knowledge-loader JSON and Markdown reports."""
    root = repository_root.resolve()
    report = KnowledgeLoaderService().load(
        _request(
            root,
            project_root,
            chunk_size,
        )
    )
    written = write_knowledge_loader_report_bundle(
        report,
        root / destination,
    )

    console.print_json(
        json.dumps(
            {
                name: str(path)
                for name, path in sorted(written.items())
            },
            sort_keys=True,
        )
    )


@knowledge_loader_app.command("validate")
def validate_knowledge(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option("--chunk-size", min=128, max=50000),
    ] = 4000,
) -> None:
    """Validate that knowledge loading completes."""
    report = KnowledgeLoaderService().load(
        _request(
            repository_root,
            project_root,
            chunk_size,
        )
    )

    console.print(
        "[green]Knowledge-loader validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_knowledge_loader_cli.py" @'
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.knowledge_loader.cli import (
    knowledge_loader_app,
)

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_knowledge_project(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "# Forge Guide\nKnowledge loading.",
        encoding="utf-8",
    )


def test_knowledge_loader_load_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "load",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Knowledge Loader Intelligence" in normalized
    assert "Sources" in normalized


def test_knowledge_loader_summary_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
        ],
    )

    assert result.exit_code == 0
    assert '"source_count"' in result.stdout
    assert '"chunk_count"' in result.stdout


def test_knowledge_loader_report_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
            "--destination",
            "reports/knowledge-loader",
        ],
    )

    assert result.exit_code == 0
    report_root = (
        tmp_path / "reports" / "knowledge-loader"
    )
    assert (
        report_root / "KNOWLEDGE_LOAD_REPORT.json"
    ).is_file()
    assert (
        report_root / "KNOWLEDGE_LOAD_SUMMARY.json"
    ).is_file()
    assert (
        report_root / "KNOWLEDGE_LOAD_REPORT.md"
    ).is_file()


def test_knowledge_loader_validate_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()
'@

Write-Utf8NoBom "scripts\validate-m4.7-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\knowledge_loader\__init__.py",
    "forge\domain_intelligence\knowledge_loader\cache.py",
    "forge\domain_intelligence\knowledge_loader\chunking.py",
    "forge\domain_intelligence\knowledge_loader\cli.py",
    "forge\domain_intelligence\knowledge_loader\compatibility.py",
    "forge\domain_intelligence\knowledge_loader\discovery.py",
    "forge\domain_intelligence\knowledge_loader\errors.py",
    "forge\domain_intelligence\knowledge_loader\identifiers.py",
    "forge\domain_intelligence\knowledge_loader\loader.py",
    "forge\domain_intelligence\knowledge_loader\manifest.py",
    "forge\domain_intelligence\knowledge_loader\models.py",
    "forge\domain_intelligence\knowledge_loader\policies.py",
    "forge\domain_intelligence\knowledge_loader\registry.py",
    "forge\domain_intelligence\knowledge_loader\reporting.py",
    "forge\domain_intelligence\knowledge_loader\resolver.py",
    "forge\domain_intelligence\knowledge_loader\service.py",
    "forge\domain_intelligence\knowledge_loader\validation.py",
    "forge\domain_intelligence\knowledge_loader\versioning.py",
    "docs\domain_intelligence\knowledge_loader\ARCHITECTURE.md",
    "docs\domain_intelligence\knowledge_loader\SPECIFICATION.md",
    "docs\domain_intelligence\knowledge_loader\DATA_MODEL.md",
    "docs\domain_intelligence\knowledge_loader\SECURITY_MODEL.md",
    "docs\domain_intelligence\knowledge_loader\ACCEPTANCE_CRITERIA.md"
)

$Missing = @(
    $RequiredFiles |
        Where-Object { -not (Test-Path $_) }
)

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }

    throw "M4.7 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'knowledge_loader_app') {
    throw "M4.7 knowledge-loader CLI is not registered."
}

if ($CliContent -notmatch 'name="knowledge-loader"') {
    throw "M4.7 knowledge-loader command is not registered."
}

$ServiceContent = Get-Content `
    ".\forge\domain_intelligence\knowledge_loader\service.py" `
    -Raw

foreach ($RequiredSymbol in @(
    "discover_knowledge_sources",
    "chunk_documents",
    "analyze_knowledge_compatibility",
    "validate_documents",
    "validate_chunks",
    "KnowledgeLoaderRegistry"
)) {
    if ($ServiceContent -notmatch [regex]::Escape($RequiredSymbol)) {
        throw "M4.7 service is missing $RequiredSymbol."
    }
}

Write-Host "M4.7 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.7-completion.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_knowledge_loader_identifiers.py `
    .\tests\test_domain_intelligence_knowledge_loader_models.py `
    .\tests\test_domain_intelligence_knowledge_loader_policies.py `
    .\tests\test_domain_intelligence_knowledge_loader_discovery.py `
    .\tests\test_domain_intelligence_knowledge_loader_loader.py `
    .\tests\test_domain_intelligence_knowledge_loader_manifest.py `
    .\tests\test_domain_intelligence_knowledge_loader_registry.py `
    .\tests\test_domain_intelligence_knowledge_loader_resolver.py `
    .\tests\test_domain_intelligence_knowledge_loader_cache.py `
    .\tests\test_domain_intelligence_knowledge_loader_chunking.py `
    .\tests\test_domain_intelligence_knowledge_loader_compatibility.py `
    .\tests\test_domain_intelligence_knowledge_loader_validation.py `
    .\tests\test_domain_intelligence_knowledge_loader_versioning.py `
    .\tests\test_domain_intelligence_knowledge_loader_reporting.py `
    .\tests\test_domain_intelligence_knowledge_loader_service.py `
    .\tests\test_domain_intelligence_knowledge_loader_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.7 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.7-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.7 architecture validation"

Write-Host "M4.7 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCliContent = Get-Content $ForgeCliPath -Raw

if (
    $ForgeCliContent -notmatch
    'from forge\.domain_intelligence\.knowledge_loader\.cli import'
) {
    $CandidateAnchors = @(
        'from forge.domain_intelligence.embedded.cli import embedded_app',
        'from forge.domain_intelligence.business_domain.cli import business_domain_app',
        'from forge.domain_intelligence.api.cli import api_app'
    )

    $ImportAnchor = $null

    foreach ($Candidate in $CandidateAnchors) {
        if ($ForgeCliContent.Contains($Candidate)) {
            $ImportAnchor = $Candidate
            break
        }
    }

    if ($null -eq $ImportAnchor) {
        throw "Unable to locate domain-intelligence import anchor in forge/cli.py."
    }

    $ForgeCliContent = $ForgeCliContent.Replace(
        $ImportAnchor,
        "$ImportAnchor`nfrom forge.domain_intelligence.knowledge_loader.cli import knowledge_loader_app"
    )
}

$Registration = 'app.add_typer(knowledge_loader_app, name="knowledge-loader")'

if (
    $ForgeCliContent -notmatch
    'app\.add_typer\(knowledge_loader_app,\s*name="knowledge-loader"\)'
) {
    $RegistrationAnchors = @(
        'app.add_typer(embedded_app, name="embedded")',
        'app.add_typer(business_domain_app, name="business-domain")',
        'app.add_typer(api_app, name="api")'
    )

    $RegistrationAnchor = $null

    foreach ($Candidate in $RegistrationAnchors) {
        if ($ForgeCliContent.Contains($Candidate)) {
            $RegistrationAnchor = $Candidate
            break
        }
    }

    if ($null -eq $RegistrationAnchor) {
        throw "Unable to locate CLI registration anchor in forge/cli.py."
    }

    $ForgeCliContent = $ForgeCliContent.Replace(
        $RegistrationAnchor,
        "$RegistrationAnchor`n$Registration"
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ForgeCliPath),
    $ForgeCliContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Host ""
Write-Host "M4.7 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_knowledge_loader_cli.py `
    .\tests\test_domain_intelligence_knowledge_loader_reporting.py `
    .\tests\test_domain_intelligence_knowledge_loader_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.7 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.7-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.7 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.7-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.7 completion validation"

Write-Host ""
Write-Host "M4.7 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short
