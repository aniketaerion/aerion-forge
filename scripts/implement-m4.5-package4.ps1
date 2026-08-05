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
    New-Item -ItemType Directory -Path (Split-Path $FullPath -Parent) -Force | Out-Null
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

Write-Utf8NoBom "forge\domain_intelligence\business_domain\cli.py" @'
"""CLI for M4.5 Business Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.reporting import (
    business_domain_report_summary,
    write_business_domain_report_bundle,
)
from forge.domain_intelligence.business_domain.service import (
    BusinessDomainIntelligenceService,
)

business_domain_app = typer.Typer(
    help=(
        "Analyze ERP, CRM, entities, workflows, rules, "
        "and business-domain architecture."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> BusinessDomainAnalysisRequest:
    return BusinessDomainAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@business_domain_app.command("analyze")
def analyze_business_domain(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root", help="Git repository root."),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option(
            "--project-root",
            help="Repository-relative business project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete JSON report."),
    ] = False,
) -> None:
    """Analyze business-domain architecture."""
    report = BusinessDomainIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = business_domain_report_summary(report)
    table = Table(title="Business Domain Intelligence")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Domains",
        ", ".join(
            domain.value for domain in report.project.domains
        ),
    )
    table.add_row(
        "Modules",
        ", ".join(report.project.modules) or "none detected",
    )
    table.add_row("Entities", str(summary["entity_count"]))
    table.add_row("Workflows", str(summary["workflow_count"]))
    table.add_row("Rules", str(summary["rule_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    console.print(table)


@business_domain_app.command("summary")
def summarize_business_domain(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise business-domain summary."""
    report = BusinessDomainIntelligenceService().analyze(
        _request(repository_root, project_root)
    )
    console.print_json(
        json.dumps(
            business_domain_report_summary(report),
            sort_keys=True,
        )
    )


@business_domain_app.command("report")
def report_business_domain(
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
    ] = Path("reports/latest/business-domain"),
) -> None:
    """Generate business-domain JSON and Markdown reports."""
    root = repository_root.resolve()
    report = BusinessDomainIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_business_domain_report_bundle(
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


@business_domain_app.command("validate")
def validate_business_domain(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that business-domain analysis completes."""
    report = BusinessDomainIntelligenceService().analyze(
        _request(repository_root, project_root)
    )
    console.print(
        "[green]Business-domain analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_cli.py" @'
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.business_domain.cli import (
    business_domain_app,
)

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_business_domain_analyze_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    procurement = tmp_path / "procurement"
    procurement.mkdir()
    (procurement / "models.py").write_text(
        "class PurchaseOrder:\n    pass\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        business_domain_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Business Domain Intelligence" in normalized
def test_business_domain_summary_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        business_domain_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert '"entity_count"' in result.stdout


def test_business_domain_report_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        business_domain_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/business-domain",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "business-domain"
        / "BUSINESS_DOMAIN_ANALYSIS.json"
    ).is_file()


def test_business_domain_validate_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        business_domain_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()
'@

Write-Utf8NoBom "scripts\validate-m4.5-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\business_domain\__init__.py",
    "forge\domain_intelligence\business_domain\cli.py",
    "forge\domain_intelligence\business_domain\crm.py",
    "forge\domain_intelligence\business_domain\entities.py",
    "forge\domain_intelligence\business_domain\erp.py",
    "forge\domain_intelligence\business_domain\errors.py",
    "forge\domain_intelligence\business_domain\identifiers.py",
    "forge\domain_intelligence\business_domain\manifest.py",
    "forge\domain_intelligence\business_domain\models.py",
    "forge\domain_intelligence\business_domain\ontology.py",
    "forge\domain_intelligence\business_domain\plugin.py",
    "forge\domain_intelligence\business_domain\policies.py",
    "forge\domain_intelligence\business_domain\registry.py",
    "forge\domain_intelligence\business_domain\reporting.py",
    "forge\domain_intelligence\business_domain\rules.py",
    "forge\domain_intelligence\business_domain\service.py",
    "forge\domain_intelligence\business_domain\workflows.py",
    "docs\domain_intelligence\business_domain\ARCHITECTURE.md",
    "docs\domain_intelligence\business_domain\SPECIFICATION.md",
    "docs\domain_intelligence\business_domain\DATA_MODEL.md",
    "docs\domain_intelligence\business_domain\SECURITY_MODEL.md",
    "docs\domain_intelligence\business_domain\ACCEPTANCE_CRITERIA.md"
)

$Missing = @($RequiredFiles | Where-Object { -not (Test-Path $_) })

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }
    throw "M4.5 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'business_domain_app') {
    throw "M4.5 CLI is not registered in forge/cli.py."
}

if ($CliContent -notmatch 'name="business-domain"') {
    throw "M4.5 business-domain command is not registered."
}

Write-Host "M4.5 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.5-completion.ps1" @'
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
    .\tests\test_domain_intelligence_business_domain_identifiers.py `
    .\tests\test_domain_intelligence_business_domain_models.py `
    .\tests\test_domain_intelligence_business_domain_policies.py `
    .\tests\test_domain_intelligence_business_domain_entities.py `
    .\tests\test_domain_intelligence_business_domain_erp.py `
    .\tests\test_domain_intelligence_business_domain_crm.py `
    .\tests\test_domain_intelligence_business_domain_manifest.py `
    .\tests\test_domain_intelligence_business_domain_registry.py `
    .\tests\test_domain_intelligence_business_domain_ontology.py `
    .\tests\test_domain_intelligence_business_domain_workflows.py `
    .\tests\test_domain_intelligence_business_domain_rules.py `
    .\tests\test_domain_intelligence_business_domain_plugin.py `
    .\tests\test_domain_intelligence_business_domain_reporting.py `
    .\tests\test_domain_intelligence_business_domain_service.py `
    .\tests\test_domain_intelligence_business_domain_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.5 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.5 architecture validation"

Write-Host "M4.5 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCliContent = Get-Content $ForgeCliPath -Raw

if (
    $ForgeCliContent -notmatch
    'from forge\.domain_intelligence\.business_domain\.cli import business_domain_app'
) {
    $Anchor = 'from forge.domain_intelligence.backend.cli import backend_app'
    if (-not $ForgeCliContent.Contains($Anchor)) {
        throw "Unable to locate domain-intelligence import anchor in forge/cli.py."
    }
    $ForgeCliContent = $ForgeCliContent.Replace(
        $Anchor,
        "$Anchor`nfrom forge.domain_intelligence.business_domain.cli import business_domain_app"
    )
}

if (
    $ForgeCliContent -notmatch
    'app\.add_typer\(business_domain_app, name="business-domain"\)'
) {
    $Anchor = 'app.add_typer(api_app, name="api")'
    if (-not $ForgeCliContent.Contains($Anchor)) {
        throw "Unable to locate domain-intelligence CLI registration anchor."
    }
    $ForgeCliContent = $ForgeCliContent.Replace(
        $Anchor,
        "$Anchor`napp.add_typer(business_domain_app, name=""business-domain"")"
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ForgeCliPath),
    $ForgeCliContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green
Write-Host ""
Write-Host "M4.5 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_business_domain_cli.py `
    .\tests\test_domain_intelligence_business_domain_service.py `
    .\tests\test_domain_intelligence_business_domain_reporting.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.5 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.5 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.5-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.5 completion validation"

Write-Host ""
Write-Host "M4.5 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short