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

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\cli.py" @'
"""CLI for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)
from forge.domain_intelligence.phase_validation.reporting import (
    phase_validation_report_summary,
    write_phase_validation_report_bundle,
)
from forge.domain_intelligence.phase_validation.service import (
    PhaseValidationService,
)

phase_validation_app = typer.Typer(
    help=(
        "Validate architecture, acceptance criteria, coverage, "
        "compatibility, release readiness, and phase completion."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    phase: str,
    milestone: str | None,
    require_clean_worktree: bool,
    require_release_tag: bool,
    minimum_test_count: int,
    minimum_coverage_percent: float,
) -> PhaseValidationRequest:
    return PhaseValidationRequest(
        repository_root=str(repository_root.resolve()),
        phase=phase,
        milestone=milestone,
        require_clean_worktree=require_clean_worktree,
        require_release_tag=require_release_tag,
        minimum_test_count=minimum_test_count,
        minimum_coverage_percent=minimum_coverage_percent,
    )


@phase_validation_app.command("validate")
def validate_phase(
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            help="Git repository root.",
        ),
    ] = Path("."),
    phase: Annotated[
        str,
        typer.Option(
            "--phase",
            help="Phase identifier, for example 4.",
        ),
    ] = "4",
    milestone: Annotated[
        str | None,
        typer.Option(
            "--milestone",
            help="Optional milestone identifier, for example M4.8.",
        ),
    ] = None,
    require_clean_worktree: Annotated[
        bool,
        typer.Option(
            "--require-clean-worktree/--allow-dirty-worktree",
            help="Require a clean Git working tree.",
        ),
    ] = True,
    require_release_tag: Annotated[
        bool,
        typer.Option(
            "--require-release-tag/--allow-missing-release-tag",
            help="Require a release tag.",
        ),
    ] = False,
    minimum_test_count: Annotated[
        int,
        typer.Option(
            "--minimum-test-count",
            min=0,
            help="Minimum collected test count.",
        ),
    ] = 1,
    minimum_coverage_percent: Annotated[
        float,
        typer.Option(
            "--minimum-coverage-percent",
            min=0.0,
            max=100.0,
            help="Minimum required code coverage percentage.",
        ),
    ] = 0.0,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete JSON report.",
        ),
    ] = False,
) -> None:
    """Run phase-validation intelligence."""
    report = PhaseValidationService().validate(
        _request(
            repository_root,
            phase,
            milestone,
            require_clean_worktree,
            require_release_tag,
            minimum_test_count,
            minimum_coverage_percent,
        )
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = phase_validation_report_summary(report)

    table = Table(title="Phase Validation Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Phase", str(summary["phase"]))
    table.add_row(
        "Milestone",
        str(summary["milestone"] or "-"),
    )
    table.add_row(
        "Result",
        "PASS" if summary["passed"] else "FAIL",
    )
    table.add_row("Checks", str(summary["check_count"]))
    table.add_row("Results", str(summary["result_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    table.add_row(
        "Required passed",
        (
            f"{summary['passed_required_check_count']}/"
            f"{summary['required_check_count']}"
        ),
    )

    console.print(table)


@phase_validation_app.command("summary")
def summarize_phase(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    phase: Annotated[
        str,
        typer.Option("--phase"),
    ] = "4",
    milestone: Annotated[
        str | None,
        typer.Option("--milestone"),
    ] = None,
) -> None:
    """Print a concise phase-validation summary."""
    report = PhaseValidationService().validate(
        _request(
            repository_root,
            phase,
            milestone,
            True,
            False,
            1,
            0.0,
        )
    )

    console.print_json(
        json.dumps(
            phase_validation_report_summary(report),
            sort_keys=True,
        )
    )


@phase_validation_app.command("report")
def report_phase(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    phase: Annotated[
        str,
        typer.Option("--phase"),
    ] = "4",
    milestone: Annotated[
        str | None,
        typer.Option("--milestone"),
    ] = None,
    destination: Annotated[
        Path,
        typer.Option(
            "--destination",
            help="Repository-relative report destination.",
        ),
    ] = Path("reports/latest/phase-validation"),
) -> None:
    """Generate phase-validation JSON and Markdown reports."""
    root = repository_root.resolve()
    report = PhaseValidationService().validate(
        _request(
            root,
            phase,
            milestone,
            True,
            False,
            1,
            0.0,
        )
    )
    written = write_phase_validation_report_bundle(
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
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_cli.py" @'
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.phase_validation.cli import (
    phase_validation_app,
)

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    path = (
        tmp_path
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
    )
    path.mkdir(parents=True)
    (path / "ARCHITECTURE.md").write_text(
        "# Architecture",
        encoding="utf-8",
    )
    (path / "ACCEPTANCE_CRITERIA.md").write_text(
        "# Acceptance\n\n- Architecture exists.\n",
        encoding="utf-8",
    )


def test_phase_validation_validate_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        phase_validation_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
            "--phase",
            "4",
            "--milestone",
            "M4.8",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Phase Validation Intelligence" in normalized
    assert "PASS" in normalized


def test_phase_validation_summary_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        phase_validation_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
            "--phase",
            "4",
        ],
    )

    assert result.exit_code == 0
    assert '"check_count"' in result.stdout
    assert '"passed"' in result.stdout


def test_phase_validation_report_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        phase_validation_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--phase",
            "4",
            "--destination",
            "reports/phase-validation",
        ],
    )

    assert result.exit_code == 0

    report_root = tmp_path / "reports" / "phase-validation"

    assert (
        report_root / "PHASE_VALIDATION_REPORT.json"
    ).is_file()
    assert (
        report_root / "PHASE_VALIDATION_SUMMARY.json"
    ).is_file()
    assert (
        report_root / "PHASE_VALIDATION_REPORT.md"
    ).is_file()
'@

Write-Utf8NoBom "scripts\validate-m4.8-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\phase_validation\__init__.py",
    "forge\domain_intelligence\phase_validation\acceptance.py",
    "forge\domain_intelligence\phase_validation\architecture.py",
    "forge\domain_intelligence\phase_validation\cli.py",
    "forge\domain_intelligence\phase_validation\compatibility.py",
    "forge\domain_intelligence\phase_validation\coverage.py",
    "forge\domain_intelligence\phase_validation\errors.py",
    "forge\domain_intelligence\phase_validation\identifiers.py",
    "forge\domain_intelligence\phase_validation\models.py",
    "forge\domain_intelligence\phase_validation\policies.py",
    "forge\domain_intelligence\phase_validation\registry.py",
    "forge\domain_intelligence\phase_validation\release.py",
    "forge\domain_intelligence\phase_validation\reporting.py",
    "forge\domain_intelligence\phase_validation\service.py",
    "docs\domain_intelligence\phase_validation\ARCHITECTURE.md",
    "docs\domain_intelligence\phase_validation\SPECIFICATION.md",
    "docs\domain_intelligence\phase_validation\DATA_MODEL.md",
    "docs\domain_intelligence\phase_validation\SECURITY_MODEL.md",
    "docs\domain_intelligence\phase_validation\ACCEPTANCE_CRITERIA.md"
)

$Missing = @(
    $RequiredFiles |
        Where-Object { -not (Test-Path $_) }
)

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }

    throw "M4.8 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'phase_validation_app') {
    throw "M4.8 phase-validation CLI is not registered."
}

if ($CliContent -notmatch 'name="phase-validation"') {
    throw "M4.8 phase-validation command is not registered."
}

$ServiceContent = Get-Content `
    ".\forge\domain_intelligence\phase_validation\service.py" `
    -Raw

foreach ($RequiredSymbol in @(
    "PhaseValidationService",
    "PhaseValidationRegistry",
    "phase_validation_report_identifier"
)) {
    if ($ServiceContent -notmatch [regex]::Escape($RequiredSymbol)) {
        throw "M4.8 service is missing $RequiredSymbol."
    }
}

Write-Host "M4.8 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m4.8-completion.ps1" @'
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
    .\tests\test_domain_intelligence_phase_validation_identifiers.py `
    .\tests\test_domain_intelligence_phase_validation_models.py `
    .\tests\test_domain_intelligence_phase_validation_policies.py `
    .\tests\test_domain_intelligence_phase_validation_architecture.py `
    .\tests\test_domain_intelligence_phase_validation_acceptance.py `
    .\tests\test_domain_intelligence_phase_validation_registry.py `
    .\tests\test_domain_intelligence_phase_validation_service.py `
    .\tests\test_domain_intelligence_phase_validation_coverage.py `
    .\tests\test_domain_intelligence_phase_validation_compatibility.py `
    .\tests\test_domain_intelligence_phase_validation_release.py `
    .\tests\test_domain_intelligence_phase_validation_reporting.py `
    .\tests\test_domain_intelligence_phase_validation_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.8 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.8-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.8 architecture validation"

Write-Host "M4.8 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCliContent = Get-Content $ForgeCliPath -Raw

if (
    $ForgeCliContent -notmatch
    'from forge\.domain_intelligence\.phase_validation\.cli import'
) {
    $CandidateAnchors = @(
        'from forge.domain_intelligence.knowledge_loader.cli import knowledge_loader_app',
        'from forge.domain_intelligence.embedded.cli import embedded_app',
        'from forge.domain_intelligence.business_domain.cli import business_domain_app'
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
        "$ImportAnchor`nfrom forge.domain_intelligence.phase_validation.cli import phase_validation_app"
    )
}

$Registration = 'app.add_typer(phase_validation_app, name="phase-validation")'

if (
    $ForgeCliContent -notmatch
    'app\.add_typer\(phase_validation_app,\s*name="phase-validation"\)'
) {
    $RegistrationAnchors = @(
        'app.add_typer(knowledge_loader_app, name="knowledge-loader")',
        'app.add_typer(embedded_app, name="embedded")',
        'app.add_typer(business_domain_app, name="business-domain")'
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
Write-Host "M4.8 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_phase_validation_cli.py `
    .\tests\test_domain_intelligence_phase_validation_reporting.py `
    .\tests\test_domain_intelligence_phase_validation_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.8 Package 4 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.8-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.8 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.8-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.8 completion validation"

Write-Host ""
Write-Host "M4.8 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short