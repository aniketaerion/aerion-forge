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

Write-Utf8NoBom "forge\domain_intelligence\embedded\cli.py" @'
"""CLI for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
)
from forge.domain_intelligence.embedded.reporting import (
    embedded_report_summary,
    write_embedded_report_bundle,
)
from forge.domain_intelligence.embedded.service import (
    EmbeddedIntelligenceService,
)

embedded_app = typer.Typer(
    help=(
        "Analyze PX4, ArduPilot, ROS 2, STM32, embedded interfaces, "
        "messages, build systems, and safety findings."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> EmbeddedAnalysisRequest:
    return EmbeddedAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@embedded_app.command("analyze")
def analyze_embedded(
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
            help="Repository-relative embedded project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete JSON report.",
        ),
    ] = False,
) -> None:
    """Analyze an embedded software project."""
    report = EmbeddedIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = embedded_report_summary(report)

    table = Table(title="Embedded Domain Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Platforms",
        ", ".join(summary["platforms"]) or "none detected",
    )
    table.add_row("Components", str(summary["component_count"]))
    table.add_row("Interfaces", str(summary["interface_count"]))
    table.add_row("Messages", str(summary["message_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    table.add_row("Build files", str(summary["build_file_count"]))

    console.print(table)


@embedded_app.command("summary")
def summarize_embedded(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise embedded-analysis summary."""
    report = EmbeddedIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            embedded_report_summary(report),
            sort_keys=True,
        )
    )


@embedded_app.command("report")
def report_embedded(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    destination: Annotated[
        Path,
        typer.Option(
            "--destination",
            help="Repository-relative report destination.",
        ),
    ] = Path("reports/latest/embedded"),
) -> None:
    """Generate embedded JSON and Markdown reports."""
    root = repository_root.resolve()
    report = EmbeddedIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_embedded_report_bundle(
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


@embedded_app.command("validate")
def validate_embedded(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that embedded analysis completes."""
    report = EmbeddedIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Embedded-domain analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_cli.py" @'
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.embedded.cli import embedded_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_px4_project(tmp_path: Path) -> None:
    module = tmp_path / "src" / "modules" / "navigator"
    module.mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )
    (module / "navigator.cpp").write_text(
        "UART_Init();\n",
        encoding="utf-8",
    )


def test_embedded_analyze_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_px4_project(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Embedded Domain Intelligence" in normalized
    assert "px4" in normalized.lower()


def test_embedded_summary_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert '"component_count"' in result.stdout
    assert '"finding_count"' in result.stdout


def test_embedded_report_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/embedded",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "embedded"
        / "EMBEDDED_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "embedded"
        / "EMBEDDED_SUMMARY.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "embedded"
        / "EMBEDDED_ANALYSIS.md"
    ).is_file()


def test_embedded_validate_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()
'@

Write-Utf8NoBom "scripts\validate-m4.6-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\embedded\__init__.py",
    "forge\domain_intelligence\embedded\ardupilot.py",
    "forge\domain_intelligence\embedded\build_systems.py",
    "forge\domain_intelligence\embedded\cli.py",
    "forge\domain_intelligence\embedded\errors.py",
    "forge\domain_intelligence\embedded\identifiers.py",
    "forge\domain_intelligence\embedded\interfaces.py",
    "forge\domain_intelligence\embedded\messages.py",
    "forge\domain_intelligence\embedded\models.py",
    "forge\domain_intelligence\embedded\policies.py",
    "forge\domain_intelligence\embedded\px4.py",
    "forge\domain_intelligence\embedded\registry.py",
    "forge\domain_intelligence\embedded\reporting.py",
    "forge\domain_intelligence\embedded\ros2.py",
    "forge\domain_intelligence\embedded\safety.py",
    "forge\domain_intelligence\embedded\service.py",
    "forge\domain_intelligence\embedded\stm32.py",
    "docs\domain_intelligence\embedded\ARCHITECTURE.md",
    "docs\domain_intelligence\embedded\SPECIFICATION.md",
    "docs\domain_intelligence\embedded\DATA_MODEL.md",
    "docs\domain_intelligence\embedded\SECURITY_MODEL.md",
    "docs\domain_intelligence\embedded\ACCEPTANCE_CRITERIA.md"
)

$Missing = @(
    $RequiredFiles |
        Where-Object { -not (Test-Path $_) }
)

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }

    throw "M4.6 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'embedded_app') {
    throw "M4.6 embedded CLI is not registered in forge/cli.py."
}

if ($CliContent -notmatch 'name="embedded"') {
    throw "M4.6 embedded command is not registered."
}

$ServiceContent = Get-Content `
    ".\forge\domain_intelligence\embedded\service.py" `
    -Raw

foreach ($RequiredSymbol in @(
    "discover_embedded_build_files",
    "discover_embedded_interfaces",
    "discover_embedded_messages",
    "analyze_embedded_safety",
    "EmbeddedAnalyzerRegistry"
)) {
    if ($ServiceContent -notmatch [regex]::Escape($RequiredSymbol)) {
        throw "M4.6 service is missing $RequiredSymbol."
    }
}

Write-Host "M4.6 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.6-completion.ps1" @'
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
    .\tests\test_domain_intelligence_embedded_identifiers.py `
    .\tests\test_domain_intelligence_embedded_models.py `
    .\tests\test_domain_intelligence_embedded_policies.py `
    .\tests\test_domain_intelligence_embedded_px4.py `
    .\tests\test_domain_intelligence_embedded_ardupilot.py `
    .\tests\test_domain_intelligence_embedded_ros2.py `
    .\tests\test_domain_intelligence_embedded_stm32.py `
    .\tests\test_domain_intelligence_embedded_build_systems.py `
    .\tests\test_domain_intelligence_embedded_registry.py `
    .\tests\test_domain_intelligence_embedded_interfaces.py `
    .\tests\test_domain_intelligence_embedded_messages.py `
    .\tests\test_domain_intelligence_embedded_safety.py `
    .\tests\test_domain_intelligence_embedded_reporting.py `
    .\tests\test_domain_intelligence_embedded_service.py `
    .\tests\test_domain_intelligence_embedded_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.6 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.6-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.6 architecture validation"

Write-Host "M4.6 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCliContent = Get-Content $ForgeCliPath -Raw

$EmbeddedImport = @'
from forge.domain_intelligence.embedded.cli import embedded_app
'@

if (
    $ForgeCliContent -notmatch
    'from forge\.domain_intelligence\.embedded\.cli import embedded_app'
) {
    $CandidateAnchors = @(
        'from forge.domain_intelligence.business_domain.cli import business_domain_app',
        'from forge.domain_intelligence.api.cli import api_app',
        'from forge.domain_intelligence.backend.cli import backend_app'
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
        "$ImportAnchor`n$($EmbeddedImport.TrimEnd())"
    )
}

$EmbeddedRegistration = 'app.add_typer(embedded_app, name="embedded")'

if (
    $ForgeCliContent -notmatch
    'app\.add_typer\(embedded_app,\s*name="embedded"\)'
) {
    $RegistrationAnchors = @(
        'app.add_typer(business_domain_app, name="business-domain")',
        'app.add_typer(api_app, name="api")',
        'app.add_typer(backend_app, name="backend")'
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
        "$RegistrationAnchor`n$EmbeddedRegistration"
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ForgeCliPath),
    $ForgeCliContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Host ""
Write-Host "M4.6 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_embedded_cli.py `
    .\tests\test_domain_intelligence_embedded_reporting.py `
    .\tests\test_domain_intelligence_embedded_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.6 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.6-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.6 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.6-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.6 completion validation"

Write-Host ""
Write-Host "M4.6 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short