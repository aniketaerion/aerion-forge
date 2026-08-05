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

Write-Utf8NoBom "forge\domain_intelligence\frontend\cli.py" @'
"""CLI for M4.1 Frontend Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.frontend.reporting import (
    report_summary,
    write_report_bundle,
)
from forge.domain_intelligence.frontend.service import (
    FrontendIntelligenceService,
)
from forge.domain_intelligence.models import FrontendAnalysisRequest

frontend_app = typer.Typer(
    help="Analyze frontend architecture and generate reports.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> FrontendAnalysisRequest:
    return FrontendAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@frontend_app.command("analyze")
def analyze_frontend(
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
            help="Repository-relative frontend project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print complete JSON report."),
    ] = False,
) -> None:
    """Analyze a frontend project."""
    report = FrontendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = report_summary(report)

    table = Table(title="Frontend Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
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


@frontend_app.command("summary")
def summarize_frontend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise JSON summary."""
    report = FrontendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )
    console.print_json(
        json.dumps(
            report_summary(report),
            sort_keys=True,
        )
    )


@frontend_app.command("report")
def report_frontend(
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
    ] = Path("reports/latest/frontend"),
) -> None:
    """Generate JSON and Markdown report files."""
    root = repository_root.resolve()
    report = FrontendIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_report_bundle(
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


@frontend_app.command("validate")
def validate_frontend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that frontend analysis completes successfully."""
    report = FrontendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Frontend analysis validation passed.[/green]"
    )
    console.print(
        f"Report ID: {report.report_id}"
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_cli.py" @'
import json
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.frontend.cli import frontend_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_frontend(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                },
                "devDependencies": {
                    "vite": "^7.0.0",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )


def test_frontend_cli_help() -> None:
    result = runner.invoke(frontend_app, ["--help"])

    assert result.exit_code == 0
    assert "frontend architecture" in result.stdout


def test_frontend_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_frontend(tmp_path)

    result = runner.invoke(
        frontend_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"frameworks"' in result.stdout
    assert "react" in result.stdout
    assert "vite" in result.stdout


def test_frontend_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_frontend(tmp_path)

    result = runner.invoke(
        frontend_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/frontend",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "frontend"
        / "FRONTEND_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "frontend"
        / "FRONTEND_ANALYSIS.md"
    ).is_file()


def test_frontend_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        frontend_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()
'@

Write-Utf8NoBom "scripts\validate-m4.1-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\errors.py",
    ".\forge\domain_intelligence\identifiers.py",
    ".\forge\domain_intelligence\models.py",
    ".\forge\domain_intelligence\policies.py",
    ".\forge\domain_intelligence\frontend\__init__.py",
    ".\forge\domain_intelligence\frontend\react.py",
    ".\forge\domain_intelligence\frontend\vite.py",
    ".\forge\domain_intelligence\frontend\nextjs.py",
    ".\forge\domain_intelligence\frontend\registry.py",
    ".\forge\domain_intelligence\frontend\components.py",
    ".\forge\domain_intelligence\frontend\routing.py",
    ".\forge\domain_intelligence\frontend\hooks.py",
    ".\forge\domain_intelligence\frontend\state_management.py",
    ".\forge\domain_intelligence\frontend\styling.py",
    ".\forge\domain_intelligence\frontend\service.py",
    ".\forge\domain_intelligence\frontend\reporting.py",
    ".\forge\domain_intelligence\frontend\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_identifiers.py",
    ".\tests\test_domain_intelligence_models.py",
    ".\tests\test_domain_intelligence_policies.py",
    ".\tests\test_domain_intelligence_frontend_react.py",
    ".\tests\test_domain_intelligence_frontend_vite.py",
    ".\tests\test_domain_intelligence_frontend_nextjs.py",
    ".\tests\test_domain_intelligence_frontend_registry.py",
    ".\tests\test_domain_intelligence_frontend_components.py",
    ".\tests\test_domain_intelligence_frontend_routing.py",
    ".\tests\test_domain_intelligence_frontend_hooks.py",
    ".\tests\test_domain_intelligence_frontend_state_management.py",
    ".\tests\test_domain_intelligence_frontend_styling.py",
    ".\tests\test_domain_intelligence_frontend_service.py",
    ".\tests\test_domain_intelligence_frontend_reporting.py",
    ".\tests\test_domain_intelligence_frontend_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\ARCHITECTURE.md",
    ".\docs\domain_intelligence\SPECIFICATION.md",
    ".\docs\domain_intelligence\DATA_MODEL.md",
    ".\docs\domain_intelligence\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\ACCEPTANCE_CRITERIA.md",
    ".\docs\domain_intelligence\frontend\ARCHITECTURE.md",
    ".\docs\domain_intelligence\frontend\SPECIFICATION.md",
    ".\docs\domain_intelligence\frontend\DATA_MODEL.md",
    ".\docs\domain_intelligence\frontend\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\frontend\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.1 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.1 architecture file: $Path"
    }
}

$FrontendCli = Get-Content `
    ".\forge\domain_intelligence\frontend\cli.py" `
    -Raw

if ($FrontendCli -notmatch 'frontend_app\s*=\s*typer\.Typer') {
    throw "Frontend Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.frontend\.cli import frontend_app'
) {
    throw "Frontend CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(frontend_app,\s*name="frontend"\)'
) {
    throw "Frontend CLI registration is missing from forge\cli.py"
}

Write-Host "M4.1 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.1-completion.ps1" @'
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
    -File ".\scripts\validate-m4.1-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M4.1 architecture validation failed."
}

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['frontend', '--help']); raise SystemExit(result.exit_code)" | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw "M4.1 CLI verification failed."
}

Write-Host "M4.1 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCli = Get-Content $ForgeCliPath -Raw

$ImportLine =
    'from forge.domain_intelligence.frontend.cli import frontend_app'

if ($ForgeCli -notmatch [regex]::Escape($ImportLine)) {
    $ImportAnchor = 'from forge import __version__'

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
    'app.add_typer(frontend_app, name="frontend")'

if (
    $ForgeCli -notmatch
    'app\.add_typer\(frontend_app,\s*name="frontend"\)'
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
        $AppPattern =
            '(?ms)^app\s*=\s*typer\.Typer\(.*?^\)\s*$'

        $AppMatch = [regex]::Match($ForgeCli, $AppPattern)

        if (-not $AppMatch.Success) {
            throw "Could not find forge.cli Typer app declaration."
        }

        $InsertAt = $AppMatch.Index + $AppMatch.Length
        $ForgeCli = $ForgeCli.Insert(
            $InsertAt,
            "`n`n" + $RegistrationLine
        )
    }
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ForgeCliPath),
    $ForgeCli,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green
Write-Host ""
Write-Host "M4.1 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_frontend_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.1 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.1-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.1 architecture validation"

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['frontend', '--help']); raise SystemExit(result.exit_code)" | Out-Null
Assert-CommandSuccess "M4.1 CLI verification"

Write-Host ""
Write-Host "M4.1 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short