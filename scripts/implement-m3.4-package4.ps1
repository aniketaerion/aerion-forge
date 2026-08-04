[CmdletBinding()]
param([string]$RepositoryRoot = "D:\Software Dev\Aerion Forge")
$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param([string]$Path,[string]$Content)
    $FullPath = Join-Path $RepositoryRoot $Path
    New-Item -ItemType Directory -Path (Split-Path $FullPath -Parent) -Force | Out-Null
    [System.IO.File]::WriteAllText($FullPath,$Content,[System.Text.UTF8Encoding]::new($false))
    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\validation_repair\cli.py" @'
"""Typer commands for M3.4 Validation and Repair."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.validation_repair.errors import ValidationRepairError
from forge.validation_repair.models import ValidationCommand, ValidationTool
from forge.validation_repair.service import ValidationRepairService

repair_app = typer.Typer(
    help="Run validation and prepare bounded repair sessions.",
    no_args_is_help=True,
)

console = Console()


def _commands(timeout: int) -> tuple[ValidationCommand, ...]:
    return (
        ValidationCommand(
            command_id="ruff",
            tool=ValidationTool.RUFF,
            arguments=(".",),
            timeout_seconds=timeout,
        ),
        ValidationCommand(
            command_id="mypy",
            tool=ValidationTool.MYPY,
            arguments=(".",),
            timeout_seconds=timeout,
        ),
        ValidationCommand(
            command_id="pytest",
            tool=ValidationTool.PYTEST,
            arguments=("-p", "no:cacheprovider"),
            timeout_seconds=timeout,
        ),
    )


@repair_app.command("validate")
def validate(
    repository: Annotated[Path, typer.Option("--repository")] = Path("."),
    timeout: Annotated[int, typer.Option("--timeout", min=1)] = 300,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run Ruff, MyPy and Pytest through the bounded runner."""
    service = ValidationRepairService()
    try:
        runs = service.validate(repository, _commands(timeout))
    except ValidationRepairError as exc:
        console.print(f"[bold red]Validation failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(
            json.dumps([run.model_dump(mode="json") for run in runs], sort_keys=True)
        )
        return

    table = Table(title="Validation Results")
    table.add_column("Tool")
    table.add_column("Status")
    table.add_column("Exit")
    table.add_column("Findings")
    for run in runs:
        table.add_row(
            run.command.tool.value,
            run.status.value,
            str(run.exit_code),
            str(len(run.findings)),
        )
    console.print(table)


@repair_app.command("plan")
def plan(
    repository: Annotated[Path, typer.Option("--repository")] = Path("."),
    timeout: Annotated[int, typer.Option("--timeout", min=1)] = 300,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run validation and create bounded repair candidates."""
    service = ValidationRepairService()
    try:
        runs = service.validate(repository, _commands(timeout))
        candidates = service.plan(runs)
        session = service.create_session(repository, candidates)
        report = service.build_report(session, runs)
    except ValidationRepairError as exc:
        console.print(f"[bold red]Repair planning failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {report.session_id}")
    console.print(f"[bold]Candidates:[/bold] {len(report.attempts)}")
    console.print(f"[bold]Validation clean:[/bold] {'yes' if report.succeeded else 'no'}")
'@

Write-Utf8NoBom "tests\test_validation_repair_cli.py" @'
from typer.testing import CliRunner

from forge.validation_repair.cli import repair_app

runner = CliRunner()


def test_repair_help_lists_commands() -> None:
    result = runner.invoke(repair_app, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout
    assert "plan" in result.stdout
'@

$CliPath = Join-Path $RepositoryRoot "forge\cli.py"
$Cli = Get-Content $CliPath -Raw

if ($Cli -notmatch "from forge\.validation_repair\.cli import repair_app") {
    $Cli = $Cli.Replace(
        "from forge.workspace.cli import workspace_app",
        "from forge.validation_repair.cli import repair_app`nfrom forge.workspace.cli import workspace_app"
    )
}

if ($Cli -notmatch 'app\.add_typer\(repair_app, name="repair"\)') {
    $Cli = $Cli.Replace(
        'app.add_typer(safe_change_app, name="safe-change")',
        'app.add_typer(safe_change_app, name="safe-change")' + "`n" +
        'app.add_typer(repair_app, name="repair")'
    )
}

[System.IO.File]::WriteAllText(
    $CliPath,
    $Cli,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Utf8NoBom "scripts\validate-m3.4-architecture.ps1" @'
[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge/validation_repair/__init__.py",
    "forge/validation_repair/errors.py",
    "forge/validation_repair/identifiers.py",
    "forge/validation_repair/models.py",
    "forge/validation_repair/policies.py",
    "forge/validation_repair/parser.py",
    "forge/validation_repair/runner.py",
    "forge/validation_repair/planner.py",
    "forge/validation_repair/service.py",
    "forge/validation_repair/cli.py",
    "docs/validation_repair/ARCHITECTURE.md",
    "docs/validation_repair/SPECIFICATION.md",
    "docs/validation_repair/DATA_MODEL.md",
    "docs/validation_repair/OPERATIONS.md",
    "docs/validation_repair/ACCEPTANCE_CRITERIA.md"
)

foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File -PathType Leaf)) {
        throw "Missing required M3.4 file: $File"
    }
    if ((Get-Item $File).Length -eq 0) {
        throw "Empty required M3.4 file: $File"
    }
}

python -c "from forge.validation_repair import ValidationRepairPolicy, ValidationCommand, RepairSession"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.4 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m3.4-completion.ps1" @'
[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `
    ".\scripts\validate-m3.4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Help = forge repair --help 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $Help -notmatch "validate" -or $Help -notmatch "plan") {
    throw "forge repair CLI is not registered correctly"
}

Write-Host "M3.4 completion validation passed." -ForegroundColor Green
'@

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest .\tests\test_validation_repair_cli.py .\tests\test_validation_repair_planner.py .\tests\test_validation_repair_service.py -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File ".\scripts\validate-m3.4-architecture.ps1" -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.4 PACKAGE 4 COMPLETE" -ForegroundColor Green
Write-Host "Try: forge repair --help" -ForegroundColor Cyan
git status --short