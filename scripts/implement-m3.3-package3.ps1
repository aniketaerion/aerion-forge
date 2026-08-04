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

Write-Utf8NoBom "forge\safe_code_editing\service.py" @'
"""Service orchestration for Safe Code Editing v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from forge.safe_code_editing.errors import SafeCodeEditingError
from forge.safe_code_editing.models import (
    EditTransactionResult,
    SafeEditReport,
    SafeEditRequest,
)
from forge.safe_code_editing.policies import SafeEditPolicy
from forge.safe_code_editing.transaction import execute_transaction


class SafeEditRequestLoadError(SafeCodeEditingError):
    """Raised when a persisted edit request cannot be loaded."""


class SafeCodeEditingService:
    """Load, validate and execute bounded safe-edit requests."""

    def __init__(self, policy: SafeEditPolicy | None = None) -> None:
        self.policy = policy or SafeEditPolicy()

    def load_request(self, path: Path) -> SafeEditRequest:
        """Load one immutable request from JSON."""
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8-sig"))
            return SafeEditRequest.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise SafeEditRequestLoadError(
                f"unable to load Safe Edit request {path}: {exc}"
            ) from exc

    def execute(self, request: SafeEditRequest) -> SafeEditReport:
        """Execute dry-run or approved apply mode and return audit evidence."""
        repository_root = Path(request.repository_root).expanduser().resolve()
        transaction: EditTransactionResult = execute_transaction(
            repository_root,
            request.file_plans,
            self.policy,
            dry_run=request.dry_run,
            approved=request.approved,
        )
        return SafeEditReport(
            request_id=request.request_id,
            transaction_id=transaction.transaction_id,
            dry_run=request.dry_run,
            approved=request.approved,
            file_results=transaction.file_results,
            validation_messages=transaction.errors,
        )

    def execute_file(
        self,
        path: Path,
        *,
        apply: bool = False,
        approved: bool = False,
    ) -> SafeEditReport:
        """Load a request file and execute with explicit CLI mode overrides."""
        request = self.load_request(path)
        effective = request.model_copy(
            update={
                "dry_run": not apply,
                "approved": approved if apply else False,
            }
        )
        return self.execute(effective)

    @staticmethod
    def write_report(report: SafeEditReport, destination: Path) -> Path:
        """Persist a structured JSON report."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        return destination
'@

Write-Utf8NoBom "forge\safe_code_editing\cli.py" @'
"""Typer commands for Safe Code Editing v1."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.safe_code_editing.errors import SafeCodeEditingError
from forge.safe_code_editing.service import SafeCodeEditingService

edit_app = typer.Typer(
    help="Dry-run or apply deterministic Safe Code Editing requests.",
    no_args_is_help=True,
)

console = Console()


def _service() -> SafeCodeEditingService:
    return SafeCodeEditingService()


def _exit_code(exc: SafeCodeEditingError) -> int:
    name = type(exc).__name__
    if "Approval" in name:
        return 3
    if "Path" in name or "Binary" in name or "Encoding" in name:
        return 4
    if "Fingerprint" in name or "ExpectedText" in name or "Overlapping" in name:
        return 5
    if "Write" in name or "Rollback" in name:
        return 6
    return 1


@edit_app.command("run")
def run(
    request_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="SafeEditRequest JSON file.",
        ),
    ],
    apply: Annotated[
        bool,
        typer.Option(
            "--apply",
            help="Apply the transaction. Without this flag, execution is a dry run.",
        ),
    ] = False,
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Explicitly approve apply mode.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the structured report as JSON.",
        ),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Optional JSON report destination.",
        ),
    ] = None,
) -> None:
    """Execute one bounded Safe Edit request."""
    try:
        result = _service().execute_file(
            request_file,
            apply=apply,
            approved=approve,
        )
        if report is not None:
            _service().write_report(result, report)
    except SafeCodeEditingError as exc:
        console.print(f"[bold red]Safe Code Editing failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(result.model_dump_json())
        return

    console.print(f"[bold]Request ID:[/bold] {result.request_id}")
    console.print(f"[bold]Transaction ID:[/bold] {result.transaction_id}")
    console.print(f"[bold]Mode:[/bold] {'apply' if result.approved else 'dry-run'}")

    table = Table(title="Safe Code Editing Results")
    table.add_column("Path")
    table.add_column("Changed")
    table.add_column("Result fingerprint")
    for file_result in result.file_results:
        table.add_row(
            file_result.relative_path,
            "yes" if file_result.changed else "no",
            file_result.resulting_fingerprint,
        )
    console.print(table)

    for file_result in result.file_results:
        if file_result.unified_diff:
            console.print(file_result.unified_diff)
'@

Write-Utf8NoBom "tests\test_safe_code_editing_service.py" @'
import json
from pathlib import Path

import pytest

from forge.safe_code_editing.errors import ApprovalRequiredError
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
    SafeEditRequest,
)
from forge.safe_code_editing.service import (
    SafeCodeEditingService,
    SafeEditRequestLoadError,
)


def request_for(root: Path, *, dry_run: bool = True, approved: bool = False) -> SafeEditRequest:
    original = "old\n"
    operation = EditOperation(
        operation_id="replace-one",
        operation_type=EditOperationType.REPLACE,
        relative_path="one.txt",
        start_offset=0,
        end_offset=len(original),
        expected_text=original,
        replacement_text="new\n",
        source_fingerprint=source_fingerprint(original),
    )
    plan = FileEditPlan(
        relative_path="one.txt",
        source_fingerprint=source_fingerprint(original),
        operations=(operation,),
    )
    return SafeEditRequest(
        request_id="editreq_one",
        change_plan_id="plan_one",
        repository_root=str(root),
        file_plans=(plan,),
        dry_run=dry_run,
        approved=approved,
    )


def test_service_dry_run_preserves_file(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")

    report = SafeCodeEditingService().execute(request_for(tmp_path))

    assert report.dry_run is True
    assert report.file_results[0].changed is True
    assert target.read_bytes() == b"old\n"


def test_service_apply_changes_file(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")

    report = SafeCodeEditingService().execute(
        request_for(tmp_path, dry_run=False, approved=True)
    )

    assert report.approved is True
    assert target.read_bytes() == b"new\n"


def test_execute_file_overrides_to_dry_run(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")
    request_path = tmp_path / "request.json"
    request_path.write_text(
        request_for(tmp_path, dry_run=False, approved=True).model_dump_json(),
        encoding="utf-8",
    )

    report = SafeCodeEditingService().execute_file(request_path)

    assert report.dry_run is True
    assert target.read_bytes() == b"old\n"


def test_execute_file_requires_approval_for_apply(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")
    request_path = tmp_path / "request.json"
    request_path.write_text(request_for(tmp_path).model_dump_json(), encoding="utf-8")

    with pytest.raises(ApprovalRequiredError):
        SafeCodeEditingService().execute_file(request_path, apply=True, approved=False)


def test_invalid_request_file_is_rejected(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps({"invalid": True}), encoding="utf-8")

    with pytest.raises(SafeEditRequestLoadError):
        SafeCodeEditingService().load_request(request_path)


def test_service_writes_json_report(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")
    report = SafeCodeEditingService().execute(request_for(tmp_path))
    destination = tmp_path / "reports" / "safe-edit.json"

    written = SafeCodeEditingService.write_report(report, destination)

    assert written == destination
    assert json.loads(destination.read_text(encoding="utf-8"))["request_id"] == "editreq_one"
'@

# Update package exports.
$InitPath = Join-Path $RepositoryRoot "forge\safe_code_editing\__init__.py"
$Init = Get-Content $InitPath -Raw
if ($Init -notmatch "SafeCodeEditingService") {
    $Init = $Init.Replace(
        "from forge.safe_code_editing.policies import SafeEditPolicy",
        "from forge.safe_code_editing.policies import SafeEditPolicy`nfrom forge.safe_code_editing.service import SafeCodeEditingService, SafeEditRequestLoadError"
    )
    $Init = $Init.Replace(
        '    "SafeEditPolicy",',
        '    "SafeCodeEditingService",`n    "SafeEditPolicy",`n    "SafeEditRequestLoadError",'
    )
    [System.IO.File]::WriteAllText(
        $InitPath,
        $Init,
        [System.Text.UTF8Encoding]::new($false)
    )
    Write-Host "UPDATED forge\safe_code_editing\__init__.py" -ForegroundColor Green
}

# Register edit_app in top-level Forge CLI.
$CliPath = Join-Path $RepositoryRoot "forge\cli.py"
$Cli = Get-Content $CliPath -Raw
if ($Cli -notmatch "from forge\.safe_code_editing\.cli import edit_app") {
    $Cli = $Cli.Replace(
        "from forge.safe_change_planning.cli import safe_change_app",
        "from forge.safe_change_planning.cli import safe_change_app`nfrom forge.safe_code_editing.cli import edit_app"
    )
}
if ($Cli -notmatch 'app\.add_typer\(edit_app, name="edit"\)') {
    $Cli = $Cli.Replace(
        'app.add_typer(safe_change_app, name="safe-change")',
        'app.add_typer(safe_change_app, name="safe-change")' + "`n" +
        'app.add_typer(edit_app, name="edit")'
    )
}
[System.IO.File]::WriteAllText(
    $CliPath,
    $Cli,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Utf8NoBom "scripts\validate-m3.3-architecture.ps1" @'
[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge/safe_code_editing/__init__.py",
    "forge/safe_code_editing/errors.py",
    "forge/safe_code_editing/identifiers.py",
    "forge/safe_code_editing/models.py",
    "forge/safe_code_editing/policies.py",
    "forge/safe_code_editing/loader.py",
    "forge/safe_code_editing/operations.py",
    "forge/safe_code_editing/transaction.py",
    "forge/safe_code_editing/service.py",
    "forge/safe_code_editing/cli.py",
    "docs/safe_code_editing/ARCHITECTURE.md",
    "docs/safe_code_editing/SPECIFICATION.md",
    "docs/safe_code_editing/DATA_MODEL.md",
    "docs/safe_code_editing/SECURITY_AND_TRANSACTION_MODEL.md",
    "docs/safe_code_editing/ACCEPTANCE_CRITERIA.md"
)

foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File -PathType Leaf)) {
        throw "Missing required M3.3 file: $File"
    }
    if ((Get-Item $File).Length -eq 0) {
        throw "Empty required M3.3 file: $File"
    }
}

python -c "from forge.safe_code_editing import SafeCodeEditingService, SafeEditPolicy, SafeEditRequest"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.3 architecture validation passed." -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m3.3-completion.ps1" @'
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
    ".\scripts\validate-m3.3-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Help = forge edit --help 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $Help -notmatch "run") {
    throw "forge edit CLI is not registered correctly"
}

Write-Host "M3.3 completion validation passed." -ForegroundColor Green
'@

Write-Host ""
Write-Host "Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_safe_code_editing_service.py `
    .\tests\test_safe_code_editing_transaction.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `
    ".\scripts\validate-m3.3-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.3 PACKAGE 3 COMPLETE" -ForegroundColor Green
Write-Host "Try: forge edit --help" -ForegroundColor Cyan
git status --short