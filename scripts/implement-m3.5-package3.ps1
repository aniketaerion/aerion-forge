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

Write-Utf8NoBom "forge\autonomous_repair\reporting.py" @'
"""Reporting for M3.5 Autonomous Repair."""

from __future__ import annotations

import json
from pathlib import Path

from forge.autonomous_repair.errors import RepairPersistenceError
from forge.autonomous_repair.models import RepairExecutionReport


def render_markdown(report: RepairExecutionReport) -> str:
    """Render a compact human-readable repair report."""
    lines = [
        "# Autonomous Repair Report",
        "",
        f"- Session ID: `{report.session_id}`",
        f"- Status: `{report.status.value}`",
        f"- Succeeded: `{'yes' if report.succeeded else 'no'}`",
        f"- Attempts: `{len(report.attempts)}`",
        "",
        "## Attempts",
        "",
    ]
    for attempt in report.attempts:
        lines.extend(
            [
                f"### Attempt {attempt.attempt_number}",
                "",
                f"- Proposal: `{attempt.proposal_id}`",
                f"- Status: `{attempt.status.value}`",
                f"- Errors: `{len(attempt.errors)}`",
                "",
            ]
        )
    if report.messages:
        lines.extend(["## Messages", ""])
        lines.extend(f"- {message}" for message in report.messages)
        lines.append("")
    return "\n".join(lines)


def write_report_bundle(
    report: RepairExecutionReport,
    destination: Path,
) -> dict[str, Path]:
    """Persist JSON and Markdown report evidence."""
    try:
        destination.mkdir(parents=True, exist_ok=True)
        json_path = destination / "AUTONOMOUS_REPAIR_SESSION.json"
        markdown_path = destination / "AUTONOMOUS_REPAIR_REPORT.md"
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(render_markdown(report), encoding="utf-8")
    except OSError as exc:
        raise RepairPersistenceError(
            f"unable to persist autonomous repair report: {exc}"
        ) from exc
    return {
        json_path.name: json_path,
        markdown_path.name: markdown_path,
    }
'@

Write-Utf8NoBom "forge\autonomous_repair\service.py" @'
"""Service orchestration for M3.5 Autonomous Repair."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from forge.autonomous_repair.errors import (
    RepairInputValidationError,
    RepairPersistenceError,
)
from forge.autonomous_repair.executor import (
    AutonomousRepairExecutor,
    ValidationCallback,
    repository_fingerprint,
)
from forge.autonomous_repair.identifiers import (
    execution_request_identifier,
    execution_session_identifier,
)
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionReport,
    RepairExecutionRequest,
    RepairExecutionSession,
    RepairExecutionStatus,
    RepairInput,
    RepairProposal,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.autonomous_repair.registry import RepairProviderRegistry
from forge.autonomous_repair.reporting import write_report_bundle


class AutonomousRepairService:
    """Create proposals, execute repairs and persist evidence."""

    def __init__(
        self,
        *,
        policy: AutonomousRepairPolicy | None = None,
        registry: RepairProviderRegistry | None = None,
        executor: AutonomousRepairExecutor | None = None,
    ) -> None:
        self.policy = policy or AutonomousRepairPolicy()
        self.registry = registry or RepairProviderRegistry.with_builtins()
        self.executor = executor or AutonomousRepairExecutor(self.policy)

    def load_input(self, path: Path) -> RepairInput:
        """Load immutable repair input from JSON."""
        try:
            return RepairInput.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except (OSError, ValidationError) as exc:
            raise RepairInputValidationError(
                f"unable to load repair input {path}: {exc}"
            ) from exc

    def propose(self, repair_input: RepairInput) -> RepairProposal:
        """Resolve provider and build one bounded proposal."""
        root = self.policy.resolve_repository(Path(repair_input.repository_root))
        self.policy.validate_provider(repair_input.provider)
        provider = self.registry.get(repair_input.provider)
        if not provider.supports(repair_input):
            raise RepairInputValidationError(
                f"provider does not support input: {repair_input.provider}"
            )
        return provider.propose(root, repair_input, self.policy)

    def create_session(
        self,
        repair_input: RepairInput,
    ) -> RepairExecutionSession:
        """Create one bounded execution session."""
        session_id = execution_session_identifier(
            {
                "input_id": repair_input.input_id,
                "candidate_id": repair_input.candidate_id,
                "provider": repair_input.provider.value,
                "repository_fingerprint": repair_input.repository_fingerprint,
            }
        )
        return RepairExecutionSession(
            session_id=session_id,
            input=repair_input,
            max_attempts=self.policy.max_attempts,
            status=RepairExecutionStatus.CREATED,
        )

    def build_request(
        self,
        proposal: RepairProposal,
        *,
        repository_root: Path,
        dry_run: bool,
        approval: RepairApproval | None = None,
    ) -> RepairExecutionRequest:
        """Build a dry-run or approved execution request."""
        fingerprint = repository_fingerprint(
            repository_root,
            proposal.affected_paths,
        )
        request_id = execution_request_identifier(
            {
                "proposal_id": proposal.proposal_id,
                "repository_fingerprint": fingerprint,
                "dry_run": dry_run,
                "approved": bool(approval and approval.approved),
            }
        )
        return RepairExecutionRequest(
            request_id=request_id,
            proposal=proposal,
            repository_root=str(repository_root.resolve()),
            repository_fingerprint=fingerprint,
            dry_run=dry_run,
            approval=approval or RepairApproval(),
        )

    def execute(
        self,
        request: RepairExecutionRequest,
        *,
        attempt_number: int = 1,
        validate: ValidationCallback | None = None,
    ) -> RepairExecutionReport:
        """Execute one bounded repair and return final evidence."""
        attempt = self.executor.execute(
            request,
            attempt_number=attempt_number,
            validate=validate,
        )
        succeeded = attempt.status is RepairExecutionStatus.SUCCEEDED
        return RepairExecutionReport(
            session_id=execution_session_identifier(
                {
                    "proposal_id": request.proposal.proposal_id,
                    "request_id": request.request_id,
                }
            ),
            status=attempt.status,
            succeeded=succeeded,
            attempts=(attempt,),
            final_repository_fingerprint=repository_fingerprint(
                Path(request.repository_root),
                request.proposal.affected_paths,
            ),
            messages=(
                "Dry-run completed without mutation."
                if request.dry_run
                else "Approved repair applied and validated.",
            ),
        )

    def save_input(self, repair_input: RepairInput, destination: Path) -> Path:
        """Persist repair input as JSON."""
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(
                    repair_input.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise RepairPersistenceError(
                f"unable to save repair input {destination}: {exc}"
            ) from exc
        return destination

    @staticmethod
    def write_reports(
        report: RepairExecutionReport,
        destination: Path,
    ) -> dict[str, Path]:
        """Persist a repair report bundle."""
        return write_report_bundle(report, destination)
'@

Write-Utf8NoBom "tests\test_autonomous_repair_reporting.py" @'
import json
from pathlib import Path

from forge.autonomous_repair.models import (
    RepairExecutionAttempt,
    RepairExecutionReport,
    RepairExecutionStatus,
)
from forge.autonomous_repair.reporting import render_markdown, write_report_bundle


def report() -> RepairExecutionReport:
    attempt = RepairExecutionAttempt(
        attempt_number=1,
        proposal_id="proposal-1",
        status=RepairExecutionStatus.DRY_RUN_COMPLETE,
    )
    return RepairExecutionReport(
        session_id="session-1",
        status=RepairExecutionStatus.DRY_RUN_COMPLETE,
        succeeded=False,
        attempts=(attempt,),
        messages=("dry run",),
    )


def test_markdown_contains_session_and_attempt() -> None:
    rendered = render_markdown(report())

    assert "session-1" in rendered
    assert "Attempt 1" in rendered


def test_report_bundle_writes_json_and_markdown(tmp_path: Path) -> None:
    written = write_report_bundle(report(), tmp_path)

    assert set(written) == {
        "AUTONOMOUS_REPAIR_REPORT.md",
        "AUTONOMOUS_REPAIR_SESSION.json",
    }
    payload = json.loads(
        (tmp_path / "AUTONOMOUS_REPAIR_SESSION.json").read_text(encoding="utf-8")
    )
    assert payload["session_id"] == "session-1"
'@

Write-Utf8NoBom "tests\test_autonomous_repair_service.py" @'
from pathlib import Path

from forge.autonomous_repair.executor import repository_fingerprint
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionStatus,
    RepairInput,
    RepairProviderType,
)
from forge.autonomous_repair.service import AutonomousRepairService


def repair_input(tmp_path: Path) -> RepairInput:
    return RepairInput(
        input_id="input-1",
        candidate_id="candidate-1",
        repository_root=str(tmp_path),
        provider=RepairProviderType.EXACT_PATCH,
        finding_ids=("f1",),
        target_paths=("sample.py",),
        repository_fingerprint=repository_fingerprint(
            tmp_path,
            ("sample.py",),
        ),
        objective="replace TODO",
    )


def test_service_proposes_and_dry_runs(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")

    service = AutonomousRepairService()
    proposal = service.propose(repair_input(tmp_path))
    request = service.build_request(
        proposal,
        repository_root=tmp_path,
        dry_run=True,
    )
    report = service.execute(request)

    assert report.status is RepairExecutionStatus.DRY_RUN_COMPLETE
    assert report.succeeded is False
    assert target.read_bytes() == b"TODO"


def test_service_applies_approved_repair(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")

    service = AutonomousRepairService()
    proposal = service.propose(repair_input(tmp_path))
    request = service.build_request(
        proposal,
        repository_root=tmp_path,
        dry_run=False,
        approval=RepairApproval(
            approved=True,
            approved_by="test-user",
            reason="approved test",
        ),
    )
    report = service.execute(
        request,
        validate=lambda _root, _proposal: True,
    )

    assert report.succeeded is True
    assert target.read_bytes() == b"DONE"


def test_service_persists_reports(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")

    service = AutonomousRepairService()
    proposal = service.propose(repair_input(tmp_path))
    request = service.build_request(
        proposal,
        repository_root=tmp_path,
        dry_run=True,
    )
    report = service.execute(request)
    written = service.write_reports(report, tmp_path / "reports")

    assert "AUTONOMOUS_REPAIR_SESSION.json" in written
    assert "AUTONOMOUS_REPAIR_REPORT.md" in written
'@

Write-Host ""
Write-Host "M3.5 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_autonomous_repair_service.py `
    .\tests\test_autonomous_repair_reporting.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.5 PACKAGE 3 COMPLETE" -ForegroundColor Green
git status --short