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

Write-Utf8NoBom "forge\build_verification\cli.py" @'
"""Typer commands for M3.7 Build Verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.build_verification.errors import BuildVerificationError
from forge.build_verification.models import VerificationTool
from forge.build_verification.service import BuildVerificationService
from forge.build_verification.store import BuildVerificationStore

build_verification_app = typer.Typer(
    help="Run bounded build verification and produce release-gate evidence.",
    no_args_is_help=True,
)

console = Console()


def _parse_tools(values: list[str]) -> tuple[VerificationTool, ...]:
    try:
        return tuple(VerificationTool(value) for value in values)
    except ValueError as exc:
        raise typer.BadParameter(
            f"unsupported verification tool: {exc}"
        ) from exc


@build_verification_app.command("run")
def run_verification(
    objective: Annotated[
        str,
        typer.Option("--objective", help="Verification objective."),
    ],
    tool: Annotated[
        list[str],
        typer.Option(
            "--tool",
            help="Verification tool. Repeat as required.",
        ),
    ],
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Repository-relative target path. Repeat as required.",
        ),
    ] = None,
    report_directory: Annotated[
        Path,
        typer.Option(
            "--report-directory",
            help="Directory for JSON and Markdown reports.",
        ),
    ] = Path("reports/latest/build_verification"),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the release decision as JSON."),
    ] = False,
) -> None:
    """Create and execute one bounded verification request."""
    root = Path.cwd().resolve()
    service = BuildVerificationService()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )

    try:
        request = service.create_request(
            root,
            objective=objective,
            tools=_parse_tools(tool),
            target_paths=tuple(path or ()),
        )
        decision = service.verify(
            request,
            store=store,
            report_directory=root / report_directory,
        )
    except (BuildVerificationError, OSError, ValueError) as exc:
        console.print(
            f"[bold red]Build verification failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(decision.model_dump_json())
        return

    console.print(
        f"[bold]Decision:[/bold] {decision.decision.value}"
    )
    console.print(
        f"[bold]Decision ID:[/bold] {decision.decision_id}"
    )
    console.print(
        f"[bold]Evidence ID:[/bold] {decision.evidence_id}"
    )

    for reason in decision.reasons:
        console.print(f"- {reason}")


@build_verification_app.command("show-evidence")
def show_evidence(
    evidence_id: Annotated[
        str,
        typer.Argument(help="Verification evidence identifier."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print evidence as JSON."),
    ] = False,
) -> None:
    """Show persisted verification evidence."""
    root = Path.cwd().resolve()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )

    try:
        evidence = store.load_evidence(evidence_id)
    except (BuildVerificationError, OSError, ValueError) as exc:
        console.print(
            f"[bold red]Evidence load failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=2) from exc

    if json_output:
        console.print_json(evidence.model_dump_json())
        return

    console.print(f"[bold]Evidence ID:[/bold] {evidence.evidence_id}")
    console.print(f"[bold]Status:[/bold] {evidence.status.value}")
    console.print(
        f"[bold]Revision:[/bold] {evidence.request.source_revision}"
    )
    console.print(
        f"[bold]Fingerprint:[/bold] {evidence.repository_fingerprint}"
    )

    table = Table(title="Verification Steps")
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("Exit Code")
    table.add_column("Duration")

    for result in evidence.step_results:
        table.add_row(
            result.step_id,
            result.status.value,
            "-" if result.exit_code is None else str(result.exit_code),
            f"{result.duration_seconds:.3f}s",
        )

    console.print(table)


@build_verification_app.command("show-decision")
def show_decision(
    decision_id: Annotated[
        str,
        typer.Argument(help="Release decision identifier."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print decision as JSON."),
    ] = False,
) -> None:
    """Show one persisted release-gate decision."""
    root = Path.cwd().resolve()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )

    try:
        decision = store.load_decision(decision_id)
    except (BuildVerificationError, OSError, ValueError) as exc:
        console.print(
            f"[bold red]Decision load failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=2) from exc

    if json_output:
        console.print_json(decision.model_dump_json())
        return

    console.print(
        f"[bold]Decision:[/bold] {decision.decision.value}"
    )
    console.print(
        f"[bold]Decision ID:[/bold] {decision.decision_id}"
    )
    console.print(
        f"[bold]Evidence ID:[/bold] {decision.evidence_id}"
    )

    for reason in decision.reasons:
        console.print(f"- {reason}")


@build_verification_app.command("list")
def list_evidence(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print evidence IDs as JSON."),
    ] = False,
) -> None:
    """List persisted verification evidence."""
    root = Path.cwd().resolve()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )
    evidence_ids = store.list_evidence_ids()

    if json_output:
        console.print_json(json.dumps(list(evidence_ids)))
        return

    table = Table(title="Build Verification Evidence")
    table.add_column("Evidence ID")

    for evidence_id in evidence_ids:
        table.add_row(evidence_id)

    console.print(table)
'@

Write-Utf8NoBom "tests\test_build_verification_cli.py" @'
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from forge.build_verification.cli import build_verification_app

runner = CliRunner()


def initialize_git_repository(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(
        ("git", "init"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.email", "test@example.com"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.name", "Test User"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    subprocess.run(
        ("git", "add", "sample.py"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "commit", "-m", "initial"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def test_cli_help() -> None:
    result = runner.invoke(build_verification_app, ["--help"])

    assert result.exit_code == 0
    assert "bounded build verification" in result.stdout


def test_cli_list_empty(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        build_verification_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0
    assert "[]" in result.stdout


def test_cli_run_approves_valid_python_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    initialize_git_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        build_verification_app,
        [
            "run",
            "--objective",
            "verify sample",
            "--tool",
            "ruff",
            "--path",
            "sample.py",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"decision":"approved"' in result.stdout.replace(" ", "")
'@

Write-Utf8NoBom "scripts\validate-m3.7-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProduction = @(
    ".\forge\build_verification\__init__.py",
    ".\forge\build_verification\errors.py",
    ".\forge\build_verification\identifiers.py",
    ".\forge\build_verification\models.py",
    ".\forge\build_verification\policies.py",
    ".\forge\build_verification\providers\__init__.py",
    ".\forge\build_verification\providers\base.py",
    ".\forge\build_verification\providers\python.py",
    ".\forge\build_verification\providers\node.py",
    ".\forge\build_verification\registry.py",
    ".\forge\build_verification\runner.py",
    ".\forge\build_verification\pipeline.py",
    ".\forge\build_verification\evidence.py",
    ".\forge\build_verification\decision.py",
    ".\forge\build_verification\service.py",
    ".\forge\build_verification\store.py",
    ".\forge\build_verification\reporting.py",
    ".\forge\build_verification\cli.py"
)

$RequiredTests = @(
    ".\tests\test_build_verification_identifiers.py",
    ".\tests\test_build_verification_models.py",
    ".\tests\test_build_verification_policies.py",
    ".\tests\test_build_verification_registry.py",
    ".\tests\test_build_verification_python_provider.py",
    ".\tests\test_build_verification_node_provider.py",
    ".\tests\test_build_verification_runner.py",
    ".\tests\test_build_verification_pipeline.py",
    ".\tests\test_build_verification_evidence.py",
    ".\tests\test_build_verification_decision.py",
    ".\tests\test_build_verification_service.py",
    ".\tests\test_build_verification_store.py",
    ".\tests\test_build_verification_reporting.py",
    ".\tests\test_build_verification_cli.py"
)

$RequiredDocs = @(
    ".\docs\build_verification\ARCHITECTURE.md",
    ".\docs\build_verification\SPECIFICATION.md",
    ".\docs\build_verification\DATA_MODEL.md",
    ".\docs\build_verification\SECURITY_MODEL.md",
    ".\docs\build_verification\RELEASE_GATE.md",
    ".\docs\build_verification\STATE_MACHINE.md",
    ".\docs\build_verification\ACCEPTANCE_CRITERIA.md"
)

foreach ($Path in $RequiredProduction + $RequiredTests + $RequiredDocs) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M3.7 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M3.7 architecture file: $Path"
    }
}

$Cli = Get-Content ".\forge\cli.py" -Raw

if ($Cli -notmatch 'build_verification_app') {
    throw "M3.7 CLI is not registered in forge\cli.py"
}

Write-Host "M3.7 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m3.7-completion.ps1" @'
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
    -File ".\scripts\validate-m3.7-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M3.7 architecture validation failed."
}

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['verify-build', '--help']); raise SystemExit(result.exit_code)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "M3.7 CLI verification failed."
}

Write-Host "M3.7 completion validation passed." -ForegroundColor Green
'@

$ForgeCliPath = ".\forge\cli.py"
$ForgeCli = Get-Content $ForgeCliPath -Raw

if (
    $ForgeCli -notmatch
    'from forge\.build_verification\.cli import build_verification_app'
) {
    $ImportAnchor = 'from forge.autonomous_repair.cli import autonomous_repair_app'

    if (-not $ForgeCli.Contains($ImportAnchor)) {
        throw "Could not find forge.cli import insertion anchor."
    }

    $ForgeCli = $ForgeCli.Replace(
        $ImportAnchor,
        $ImportAnchor + "`nfrom forge.build_verification.cli import build_verification_app"
    )
}

if (
    $ForgeCli -notmatch
    'app\.add_typer\(build_verification_app,\s*name="verify-build"\)'
) {
    $RegistrationAnchor = 'app.add_typer(autonomous_repair_app, name="autonomous-repair")'

    if (-not $ForgeCli.Contains($RegistrationAnchor)) {
        throw "Could not find forge.cli registration insertion anchor."
    }

    $ForgeCli = $ForgeCli.Replace(
        $RegistrationAnchor,
        $RegistrationAnchor + "`napp.add_typer(build_verification_app, name=`"verify-build`")"
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ForgeCliPath),
    $ForgeCli,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green
Write-Host ""
Write-Host "M3.7 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_build_verification_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.7 CLI tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m3.7-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M3.7 architecture validation"

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['verify-build', '--help']); raise SystemExit(result.exit_code)" | Out-Null
Assert-CommandSuccess "M3.7 CLI verification"

Write-Host ""
Write-Host "M3.7 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short