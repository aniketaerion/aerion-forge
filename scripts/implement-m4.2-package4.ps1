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

Write-Utf8NoBom "forge\domain_intelligence\backend\cli.py" @'
"""CLI for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
)
from forge.domain_intelligence.backend.reporting import (
    backend_report_summary,
    write_backend_report_bundle,
)
from forge.domain_intelligence.backend.service import (
    BackendIntelligenceService,
)

backend_app = typer.Typer(
    help="Analyze backend architecture and generate reports.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> BackendAnalysisRequest:
    return BackendAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@backend_app.command("analyze")
def analyze_backend(
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
            help="Repository-relative backend project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print complete JSON report."),
    ] = False,
) -> None:
    """Analyze a backend project."""
    report = BackendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = backend_report_summary(report)

    table = Table(title="Backend Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Runtimes",
        ", ".join(
            runtime.value
            for runtime in report.project.runtimes
        ),
    )
    table.add_row(
        "Frameworks",
        ", ".join(
            framework.value
            for framework in report.project.frameworks
        ),
    )
    table.add_row(
        "Package manager",
        report.project.package_manager or "unknown",
    )
    table.add_row(
        "Findings",
        str(summary["finding_count"]),
    )

    console.print(table)


@backend_app.command("summary")
def summarize_backend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise backend summary."""
    report = BackendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            backend_report_summary(report),
            sort_keys=True,
        )
    )


@backend_app.command("report")
def report_backend(
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
    ] = Path("reports/latest/backend"),
) -> None:
    """Generate backend JSON and Markdown reports."""
    root = repository_root.resolve()
    report = BackendIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_backend_report_bundle(
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


@backend_app.command("validate")
def validate_backend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that backend analysis completes successfully."""
    report = BackendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Backend analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_cli.py" @'
import json
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.backend.cli import backend_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_backend(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )


def test_backend_cli_help() -> None:
    result = runner.invoke(backend_app, ["--help"])

    assert result.exit_code == 0
    assert "backend architecture" in result.stdout


def test_backend_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_backend(tmp_path)

    result = runner.invoke(
        backend_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"frameworks"' in result.stdout
    assert "express" in result.stdout
    assert "node" in result.stdout


def test_backend_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_backend(tmp_path)

    result = runner.invoke(
        backend_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/backend",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "backend"
        / "BACKEND_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "backend"
        / "BACKEND_ANALYSIS.md"
    ).is_file()


def test_backend_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        backend_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()
'@

Write-Utf8NoBom "scripts\validate-m4.2-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\backend\__init__.py",
    ".\forge\domain_intelligence\backend\errors.py",
    ".\forge\domain_intelligence\backend\identifiers.py",
    ".\forge\domain_intelligence\backend\models.py",
    ".\forge\domain_intelligence\backend\policies.py",
    ".\forge\domain_intelligence\backend\node.py",
    ".\forge\domain_intelligence\backend\fastapi.py",
    ".\forge\domain_intelligence\backend\django.py",
    ".\forge\domain_intelligence\backend\registry.py",
    ".\forge\domain_intelligence\backend\dependencies.py",
    ".\forge\domain_intelligence\backend\configuration.py",
    ".\forge\domain_intelligence\backend\services.py",
    ".\forge\domain_intelligence\backend\workers.py",
    ".\forge\domain_intelligence\backend\architecture.py",
    ".\forge\domain_intelligence\backend\reporting.py",
    ".\forge\domain_intelligence\backend\service.py",
    ".\forge\domain_intelligence\backend\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_backend_identifiers.py",
    ".\tests\test_domain_intelligence_backend_models.py",
    ".\tests\test_domain_intelligence_backend_policies.py",
    ".\tests\test_domain_intelligence_backend_node.py",
    ".\tests\test_domain_intelligence_backend_fastapi.py",
    ".\tests\test_domain_intelligence_backend_django.py",
    ".\tests\test_domain_intelligence_backend_registry.py",
    ".\tests\test_domain_intelligence_backend_dependencies.py",
    ".\tests\test_domain_intelligence_backend_configuration.py",
    ".\tests\test_domain_intelligence_backend_services.py",
    ".\tests\test_domain_intelligence_backend_workers.py",
    ".\tests\test_domain_intelligence_backend_architecture.py",
    ".\tests\test_domain_intelligence_backend_reporting.py",
    ".\tests\test_domain_intelligence_backend_service.py",
    ".\tests\test_domain_intelligence_backend_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\backend\ARCHITECTURE.md",
    ".\docs\domain_intelligence\backend\SPECIFICATION.md",
    ".\docs\domain_intelligence\backend\DATA_MODEL.md",
    ".\docs\domain_intelligence\backend\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\backend\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.2 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.2 architecture file: $Path"
    }
}

$BackendCli = Get-Content `
    ".\forge\domain_intelligence\backend\cli.py" `
    -Raw

if ($BackendCli -notmatch 'backend_app\s*=\s*typer\.Typer') {
    throw "Backend Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.backend\.cli import backend_app'
) {
    throw "Backend CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(backend_app,\s*name="backend"\)'
) {
    throw "Backend CLI registration is missing from forge\cli.py"
}

Write-Host "M4.2 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.2-completion.ps1" @'
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
    -File ".\scripts\validate-m4.2-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M4.2 architecture validation failed."
}

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['backend', '--help']); raise SystemExit(result.exit_code)" | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw "M4.2 CLI verification failed."
}

Write-Host "M4.2 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCli = Get-Content $ForgeCliPath -Raw

$ImportLine =
    'from forge.domain_intelligence.backend.cli import backend_app'

if ($ForgeCli -notmatch [regex]::Escape($ImportLine)) {
    $ImportAnchor =
        'from forge.domain_intelligence.frontend.cli import frontend_app'

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
    'app.add_typer(backend_app, name="backend")'

if (
    $ForgeCli -notmatch
    'app\.add_typer\(backend_app,\s*name="backend"\)'
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
Write-Host "M4.2 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_backend_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.2 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.2-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.2 architecture validation"

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['backend', '--help']); raise SystemExit(result.exit_code)" | Out-Null
Assert-CommandSuccess "M4.2 CLI verification"

Write-Host ""
Write-Host "M4.2 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short