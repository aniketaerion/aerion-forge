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

Write-Utf8NoBom "forge\domain_intelligence\api\cli.py" @'
"""CLI for M4.4 API Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.api.models import (
    ApiAnalysisRequest,
)
from forge.domain_intelligence.api.reporting import (
    api_report_summary,
    write_api_report_bundle,
)
from forge.domain_intelligence.api.service import (
    ApiIntelligenceService,
)

api_app = typer.Typer(
    help="Analyze API architecture, contracts, compatibility, and security.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> ApiAnalysisRequest:
    return ApiAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@api_app.command("analyze")
def analyze_api(
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
            help="Repository-relative API project root.",
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
    """Analyze an API project."""
    report = ApiIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = api_report_summary(report)

    table = Table(title="API Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Styles",
        ", ".join(
            style.value for style in report.project.styles
        ),
    )
    table.add_row("Contracts", str(summary["contract_count"]))
    table.add_row("Endpoints", str(summary["endpoint_count"]))
    table.add_row(
        "Authenticated endpoints",
        str(summary["authenticated_endpoint_count"]),
    )
    table.add_row("Findings", str(summary["finding_count"]))

    console.print(table)


@api_app.command("summary")
def summarize_api(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise API summary."""
    report = ApiIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            api_report_summary(report),
            sort_keys=True,
        )
    )


@api_app.command("report")
def report_api(
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
    ] = Path("reports/latest/api"),
) -> None:
    """Generate API JSON and Markdown reports."""
    root = repository_root.resolve()
    report = ApiIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_api_report_bundle(
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


@api_app.command("validate")
def validate_api(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that API analysis completes successfully."""
    report = ApiIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]API analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_api_cli.py" @'
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.api.cli import api_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_api(tmp_path: Path) -> None:
    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /v1/orders:
            get:
              operationId: listOrders
              responses:
                "200":
                  description: Success
        """,
        encoding="utf-8",
    )


def test_api_cli_help() -> None:
    result = runner.invoke(api_app, ["--help"])

    assert result.exit_code == 0
    assert "API architecture" in result.stdout


def test_api_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_api(tmp_path)

    result = runner.invoke(
        api_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"styles"' in result.stdout
    assert "openapi" in result.stdout
    assert "/v1/orders" in result.stdout


def test_api_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_api(tmp_path)

    result = runner.invoke(
        api_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/api",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path / "reports" / "api" / "API_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path / "reports" / "api" / "API_ANALYSIS.md"
    ).is_file()


def test_api_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        api_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()
'@

Write-Utf8NoBom "scripts\validate-m4.4-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\api\__init__.py",
    ".\forge\domain_intelligence\api\errors.py",
    ".\forge\domain_intelligence\api\identifiers.py",
    ".\forge\domain_intelligence\api\models.py",
    ".\forge\domain_intelligence\api\policies.py",
    ".\forge\domain_intelligence\api\rest.py",
    ".\forge\domain_intelligence\api\openapi.py",
    ".\forge\domain_intelligence\api\discovery.py",
    ".\forge\domain_intelligence\api\registry.py",
    ".\forge\domain_intelligence\api\graphql.py",
    ".\forge\domain_intelligence\api\dependencies.py",
    ".\forge\domain_intelligence\api\versioning.py",
    ".\forge\domain_intelligence\api\compatibility.py",
    ".\forge\domain_intelligence\api\security.py",
    ".\forge\domain_intelligence\api\contracts.py",
    ".\forge\domain_intelligence\api\reporting.py",
    ".\forge\domain_intelligence\api\service.py",
    ".\forge\domain_intelligence\api\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_api_identifiers.py",
    ".\tests\test_domain_intelligence_api_models.py",
    ".\tests\test_domain_intelligence_api_policies.py",
    ".\tests\test_domain_intelligence_api_rest.py",
    ".\tests\test_domain_intelligence_api_openapi.py",
    ".\tests\test_domain_intelligence_api_discovery.py",
    ".\tests\test_domain_intelligence_api_registry.py",
    ".\tests\test_domain_intelligence_api_graphql.py",
    ".\tests\test_domain_intelligence_api_dependencies.py",
    ".\tests\test_domain_intelligence_api_versioning.py",
    ".\tests\test_domain_intelligence_api_compatibility.py",
    ".\tests\test_domain_intelligence_api_security.py",
    ".\tests\test_domain_intelligence_api_contracts.py",
    ".\tests\test_domain_intelligence_api_reporting.py",
    ".\tests\test_domain_intelligence_api_service.py",
    ".\tests\test_domain_intelligence_api_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\api\ARCHITECTURE.md",
    ".\docs\domain_intelligence\api\SPECIFICATION.md",
    ".\docs\domain_intelligence\api\DATA_MODEL.md",
    ".\docs\domain_intelligence\api\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\api\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.4 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.4 architecture file: $Path"
    }
}

$ApiCli = Get-Content `
    ".\forge\domain_intelligence\api\cli.py" `
    -Raw

if ($ApiCli -notmatch 'api_app\s*=\s*typer\.Typer') {
    throw "API Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.api\.cli import api_app'
) {
    throw "API CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(api_app,\s*name="api"\)'
) {
    throw "API CLI registration is missing from forge\cli.py"
}

Write-Host "M4.4 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.4-completion.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "Ruff validation failed."
}

python -m mypy .
if ($LASTEXITCODE -ne 0) {
    throw "MyPy validation failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Pytest validation failed."
}

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M4.4 architecture validation failed."
}

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['api', '--help']); raise SystemExit(result.exit_code)" | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw "M4.4 CLI verification failed."
}

Write-Host "M4.4 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCli = Get-Content $ForgeCliPath -Raw

$ImportLine =
    'from forge.domain_intelligence.api.cli import api_app'

if ($ForgeCli -notmatch [regex]::Escape($ImportLine)) {
    $ImportAnchor =
        'from forge.domain_intelligence.database.cli import database_app'

    if ($ForgeCli.Contains($ImportAnchor)) {
        $ForgeCli = $ForgeCli.Replace(
            $ImportAnchor,
            $ImportAnchor + "`n" + $ImportLine
        )
    }
    else {
        $FirstFutureImportPattern =
            '(?m)^from __future__ import annotations\s*$'

        if ($ForgeCli -match $FirstFutureImportPattern) {
            $ForgeCli = [regex]::Replace(
                $ForgeCli,
                $FirstFutureImportPattern,
                '$0' + "`n`n" + $ImportLine,
                1
            )
        }
        else {
            $ForgeCli = $ImportLine + "`n" + $ForgeCli
        }
    }
}

$RegistrationLine =
    'app.add_typer(api_app, name="api")'

if (
    $ForgeCli -notmatch
    'app\.add_typer\(api_app,\s*name="api"\)'
) {
    $LastAddTyper = [regex]::Matches(
        $ForgeCli,
        '(?m)^app\.add_typer\([^\r\n]+\)\s*$'
    )

    if ($LastAddTyper.Count -gt 0) {
        $Match = $LastAddTyper[$LastAddTyper.Count - 1]
        $InsertAt = $Match.Index + $Match.Length
        $ForgeCli = $ForgeCli.Insert(
            $InsertAt,
            "`n" + $RegistrationLine
        )
    }
    else {
        throw "Could not find CLI registration anchor."
    }
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ForgeCliPath),
    $ForgeCli,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green
Write-Host ""
Write-Host "M4.4 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_api_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.4 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.4 architecture validation"

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['api', '--help']); raise SystemExit(result.exit_code)" | Out-Null
Assert-CommandSuccess "M4.4 CLI verification"

Write-Host ""
Write-Host "M4.4 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short
