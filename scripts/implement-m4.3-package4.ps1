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

Write-Utf8NoBom "forge\domain_intelligence\database\cli.py" @'
"""CLI for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
)
from forge.domain_intelligence.database.reporting import (
    database_report_summary,
    write_database_report_bundle,
)
from forge.domain_intelligence.database.service import (
    DatabaseIntelligenceService,
)

database_app = typer.Typer(
    help="Analyze database architecture and generate reports.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> DatabaseAnalysisRequest:
    return DatabaseAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@database_app.command("analyze")
def analyze_database(
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
            help="Repository-relative database project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print complete JSON report."),
    ] = False,
) -> None:
    """Analyze a database project."""
    report = DatabaseIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = database_report_summary(report)

    table = Table(title="Database Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Engines",
        ", ".join(
            engine.value for engine in report.project.engines
        ),
    )
    table.add_row("Tables", str(summary["table_count"]))
    table.add_row("Columns", str(summary["column_count"]))
    table.add_row(
        "Relationships",
        str(summary["relationship_count"]),
    )
    table.add_row("Findings", str(summary["finding_count"]))

    console.print(table)


@database_app.command("summary")
def summarize_database(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise database summary."""
    report = DatabaseIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            database_report_summary(report),
            sort_keys=True,
        )
    )


@database_app.command("report")
def report_database(
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
    ] = Path("reports/latest/database"),
) -> None:
    """Generate database JSON and Markdown reports."""
    root = repository_root.resolve()
    report = DatabaseIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_database_report_bundle(
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


@database_app.command("validate")
def validate_database(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that database analysis completes successfully."""
    report = DatabaseIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Database analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_cli.py" @'
import json
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.database.cli import database_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_database(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  db:\n    image: postgres:16\n",
        encoding="utf-8",
    )
    (tmp_path / "schema.sql").write_text(
        """
        CREATE TABLE public.orders (
            id uuid NOT NULL,
            PRIMARY KEY (id)
        );
        """,
        encoding="utf-8",
    )


def test_database_cli_help() -> None:
    result = runner.invoke(database_app, ["--help"])

    assert result.exit_code == 0
    assert "database architecture" in result.stdout


def test_database_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_database(tmp_path)

    result = runner.invoke(
        database_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"engines"' in result.stdout
    assert "postgresql" in result.stdout
    assert "orders" in result.stdout


def test_database_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_database(tmp_path)

    result = runner.invoke(
        database_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/database",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "database"
        / "DATABASE_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "database"
        / "DATABASE_ANALYSIS.md"
    ).is_file()


def test_database_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        database_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()
'@

Write-Utf8NoBom "scripts\validate-m4.3-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\database\__init__.py",
    ".\forge\domain_intelligence\database\errors.py",
    ".\forge\domain_intelligence\database\identifiers.py",
    ".\forge\domain_intelligence\database\models.py",
    ".\forge\domain_intelligence\database\policies.py",
    ".\forge\domain_intelligence\database\postgres.py",
    ".\forge\domain_intelligence\database\configuration.py",
    ".\forge\domain_intelligence\database\discovery.py",
    ".\forge\domain_intelligence\database\registry.py",
    ".\forge\domain_intelligence\database\schema.py",
    ".\forge\domain_intelligence\database\constraints.py",
    ".\forge\domain_intelligence\database\indexes.py",
    ".\forge\domain_intelligence\database\relationships.py",
    ".\forge\domain_intelligence\database\queries.py",
    ".\forge\domain_intelligence\database\risk.py",
    ".\forge\domain_intelligence\database\reporting.py",
    ".\forge\domain_intelligence\database\service.py",
    ".\forge\domain_intelligence\database\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_database_identifiers.py",
    ".\tests\test_domain_intelligence_database_models.py",
    ".\tests\test_domain_intelligence_database_policies.py",
    ".\tests\test_domain_intelligence_database_postgres.py",
    ".\tests\test_domain_intelligence_database_configuration.py",
    ".\tests\test_domain_intelligence_database_discovery.py",
    ".\tests\test_domain_intelligence_database_registry.py",
    ".\tests\test_domain_intelligence_database_schema.py",
    ".\tests\test_domain_intelligence_database_constraints.py",
    ".\tests\test_domain_intelligence_database_indexes.py",
    ".\tests\test_domain_intelligence_database_relationships.py",
    ".\tests\test_domain_intelligence_database_queries.py",
    ".\tests\test_domain_intelligence_database_risk.py",
    ".\tests\test_domain_intelligence_database_reporting.py",
    ".\tests\test_domain_intelligence_database_service.py",
    ".\tests\test_domain_intelligence_database_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\database\ARCHITECTURE.md",
    ".\docs\domain_intelligence\database\SPECIFICATION.md",
    ".\docs\domain_intelligence\database\DATA_MODEL.md",
    ".\docs\domain_intelligence\database\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\database\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.3 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.3 architecture file: $Path"
    }
}

$DatabaseCli = Get-Content `
    ".\forge\domain_intelligence\database\cli.py" `
    -Raw

if ($DatabaseCli -notmatch 'database_app\s*=\s*typer\.Typer') {
    throw "Database Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.database\.cli import database_app'
) {
    throw "Database CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(database_app,\s*name="database"\)'
) {
    throw "Database CLI registration is missing from forge\cli.py"
}

Write-Host "M4.3 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.3-completion.ps1" @'
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
    -File ".\scripts\validate-m4.3-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M4.3 architecture validation failed."
}

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['database', '--help']); raise SystemExit(result.exit_code)" | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw "M4.3 CLI verification failed."
}

Write-Host "M4.3 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCli = Get-Content $ForgeCliPath -Raw

$ImportLine =
    'from forge.domain_intelligence.database.cli import database_app'

if ($ForgeCli -notmatch [regex]::Escape($ImportLine)) {
    $ImportAnchor =
        'from forge.domain_intelligence.backend.cli import backend_app'

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
    'app.add_typer(database_app, name="database")'

if (
    $ForgeCli -notmatch
    'app\.add_typer\(database_app,\s*name="database"\)'
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
Write-Host "M4.3 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_database_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.3 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.3-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.3 architecture validation"

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['database', '--help']); raise SystemExit(result.exit_code)" | Out-Null
Assert-CommandSuccess "M4.3 CLI verification"

Write-Host ""
Write-Host "M4.3 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short