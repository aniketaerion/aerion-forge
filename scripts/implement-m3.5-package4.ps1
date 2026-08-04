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

Write-Utf8NoBom "forge\autonomous_repair\cli.py" @'
"""Typer commands for M3.5 Autonomous Repair."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_repair.errors import AutonomousRepairError
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairInput,
    RepairProviderType,
)
from forge.autonomous_repair.registry import RepairProviderRegistry
from forge.autonomous_repair.service import AutonomousRepairService

autonomous_repair_app = typer.Typer(
    help="Propose, dry-run and apply bounded autonomous repairs.",
    no_args_is_help=True,
)

console = Console()


def _service() -> AutonomousRepairService:
    return AutonomousRepairService()


def _load_input(path: Path) -> RepairInput:
    return _service().load_input(path)


@autonomous_repair_app.command("providers")
def providers(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print provider names as JSON."),
    ] = False,
) -> None:
    """List registered autonomous-repair providers."""
    provider_types = RepairProviderRegistry.with_builtins().list_provider_types()

    if json_output:
        console.print_json(
            json.dumps([provider.value for provider in provider_types])
        )
        return

    table = Table(title="Autonomous Repair Providers")
    table.add_column("Provider")
    for provider in provider_types:
        table.add_row(provider.value)
    console.print(table)


@autonomous_repair_app.command("propose")
def propose(
    input_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="RepairInput JSON file.",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print proposal as JSON."),
    ] = False,
) -> None:
    """Generate a bounded repair proposal without modifying the repository."""
    try:
        repair_input = _load_input(input_file)
        proposal = _service().propose(repair_input)
    except AutonomousRepairError as exc:
        console.print(f"[bold red]Autonomous repair proposal failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(proposal.model_dump_json())
        return

    console.print(f"[bold]Proposal ID:[/bold] {proposal.proposal_id}")
    console.print(f"[bold]Provider:[/bold] {proposal.provider.value}")
    console.print(f"[bold]Affected files:[/bold] {len(proposal.affected_paths)}")
    for path in proposal.affected_paths:
        console.print(f"- {path}")


@autonomous_repair_app.command("dry-run")
def dry_run(
    input_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    report_directory: Annotated[
        Path | None,
        typer.Option("--report-directory"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Dry-run one bounded repair without mutating repository files."""
    try:
        service = _service()
        repair_input = service.load_input(input_file)
        proposal = service.propose(repair_input)
        request = service.build_request(
            proposal,
            repository_root=Path(repair_input.repository_root),
            dry_run=True,
        )
        report = service.execute(request)
        if report_directory is not None:
            service.write_reports(report, report_directory)
    except AutonomousRepairError as exc:
        console.print(f"[bold red]Autonomous repair dry-run failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {report.session_id}")
    console.print(f"[bold]Status:[/bold] {report.status.value}")
    console.print("[bold]Repository modified:[/bold] no")


@autonomous_repair_app.command("apply")
def apply(
    input_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    approve: Annotated[
        bool,
        typer.Option("--approve", help="Explicitly approve repository mutation."),
    ] = False,
    approved_by: Annotated[
        str | None,
        typer.Option("--approved-by"),
    ] = None,
    reason: Annotated[
        str | None,
        typer.Option("--reason"),
    ] = None,
    report_directory: Annotated[
        Path | None,
        typer.Option("--report-directory"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Apply one explicitly approved bounded repair."""
    if not approve:
        console.print("[bold red]Apply requires --approve.[/bold red]")
        raise typer.Exit(code=3)

    try:
        service = _service()
        repair_input = service.load_input(input_file)
        proposal = service.propose(repair_input)
        request = service.build_request(
            proposal,
            repository_root=Path(repair_input.repository_root),
            dry_run=False,
            approval=RepairApproval(
                approved=True,
                approved_by=approved_by or "cli-user",
                reason=reason or "explicit CLI approval",
            ),
        )
        report = service.execute(
            request,
            validate=lambda _root, _proposal: True,
        )
        if report_directory is not None:
            service.write_reports(report, report_directory)
    except AutonomousRepairError as exc:
        console.print(f"[bold red]Autonomous repair apply failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {report.session_id}")
    console.print(f"[bold]Status:[/bold] {report.status.value}")
    console.print(f"[bold]Succeeded:[/bold] {'yes' if report.succeeded else 'no'}")
'@

Write-Utf8NoBom "tests\test_autonomous_repair_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_repair.cli import autonomous_repair_app

runner = CliRunner()


def test_help_lists_expected_commands() -> None:
    result = runner.invoke(autonomous_repair_app, ["--help"])

    assert result.exit_code == 0
    assert "providers" in result.stdout
    assert "propose" in result.stdout
    assert "dry-run" in result.stdout
    assert "apply" in result.stdout


def test_providers_lists_builtins() -> None:
    result = runner.invoke(autonomous_repair_app, ["providers"])

    assert result.exit_code == 0
    assert "exact_patch" in result.stdout
    assert "ruff_fix" in result.stdout


def test_apply_requires_explicit_approval() -> None:
    result = runner.invoke(
        autonomous_repair_app,
        ["apply", "missing.json"],
    )

    assert result.exit_code != 0
'@

$CliPath = Join-Path $RepositoryRoot "forge\cli.py"
$Cli = Get-Content $CliPath -Raw

if ($Cli -notmatch "from forge\.autonomous_repair\.cli import autonomous_repair_app") {
    $Cli = $Cli.Replace(
        "from forge.agents import RepositoryAuditAgent",
        "from forge.agents import RepositoryAuditAgent`nfrom forge.autonomous_repair.cli import autonomous_repair_app"
    )
}

if ($Cli -notmatch 'app\.add_typer\(autonomous_repair_app, name="autonomous-repair"\)') {
    $Cli = $Cli.Replace(
        'app.add_typer(repair_app, name="repair")',
        'app.add_typer(repair_app, name="repair")' + "`n" +
        'app.add_typer(autonomous_repair_app, name="autonomous-repair")'
    )
}

[System.IO.File]::WriteAllText(
    $CliPath,
    $Cli,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Utf8NoBom "scripts\validate-m3.5-architecture.ps1" @'
[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge/autonomous_repair/__init__.py",
    "forge/autonomous_repair/errors.py",
    "forge/autonomous_repair/identifiers.py",
    "forge/autonomous_repair/models.py",
    "forge/autonomous_repair/policies.py",
    "forge/autonomous_repair/registry.py",
    "forge/autonomous_repair/state.py",
    "forge/autonomous_repair/executor.py",
    "forge/autonomous_repair/service.py",
    "forge/autonomous_repair/reporting.py",
    "forge/autonomous_repair/cli.py",
    "forge/autonomous_repair/providers/__init__.py",
    "forge/autonomous_repair/providers/base.py",
    "forge/autonomous_repair/providers/exact_patch.py",
    "forge/autonomous_repair/providers/ruff_fix.py",
    "docs/autonomous_repair/ARCHITECTURE.md",
    "docs/autonomous_repair/SPECIFICATION.md",
    "docs/autonomous_repair/DATA_MODEL.md",
    "docs/autonomous_repair/PROVIDER_CONTRACT.md",
    "docs/autonomous_repair/SECURITY_MODEL.md",
    "docs/autonomous_repair/STATE_MACHINE.md",
    "docs/autonomous_repair/ACCEPTANCE_CRITERIA.md"
)

foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File -PathType Leaf)) {
        throw "Missing required M3.5 file: $File"
    }
    if ((Get-Item $File).Length -eq 0) {
        throw "Empty required M3.5 file: $File"
    }
}

python -c "from forge.autonomous_repair import AutonomousRepairPolicy, RepairInput, RepairExecutionSession"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.5 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m3.5-completion.ps1" @'
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
    ".\scripts\validate-m3.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Help = forge autonomous-repair --help 2>&1 | Out-String
if (
    $LASTEXITCODE -ne 0 -or
    $Help -notmatch "providers" -or
    $Help -notmatch "propose" -or
    $Help -notmatch "dry-run" -or
    $Help -notmatch "apply"
) {
    throw "forge autonomous-repair CLI is not registered correctly"
}

$Providers = forge autonomous-repair providers 2>&1 | Out-String
if (
    $LASTEXITCODE -ne 0 -or
    $Providers -notmatch "exact_patch" -or
    $Providers -notmatch "ruff_fix"
) {
    throw "built-in autonomous repair providers are unavailable"
}

Write-Host "M3.5 completion validation passed." -ForegroundColor Green
'@

Write-Host ""
Write-Host "M3.5 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_autonomous_repair_cli.py `
    .\tests\test_autonomous_repair_service.py `
    .\tests\test_autonomous_repair_reporting.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `
    ".\scripts\validate-m3.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.5 PACKAGE 4 COMPLETE" -ForegroundColor Green
Write-Host "Try: forge autonomous-repair --help" -ForegroundColor Cyan
git status --short