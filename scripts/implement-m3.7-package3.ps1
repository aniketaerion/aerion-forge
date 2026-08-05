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

Write-Utf8NoBom "forge\build_verification\store.py" @'
"""Persistence for M3.7 Build Verification."""

from __future__ import annotations

import json
from pathlib import Path

from forge.build_verification.errors import (
    BuildVerificationNotFoundError,
    BuildVerificationPersistenceError,
)
from forge.build_verification.models import (
    BuildVerificationEvidence,
    ReleaseGateDecision,
)


class BuildVerificationStore:
    """Persist verification evidence and release decisions atomically."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _evidence_path(self, evidence_id: str) -> Path:
        return self.root / "evidence" / f"{evidence_id}.json"

    def _decision_path(self, decision_id: str) -> Path:
        return self.root / "decisions" / f"{decision_id}.json"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as exc:
            raise BuildVerificationPersistenceError(
                f"unable to persist build verification artifact: {path}"
            ) from exc

    def save_evidence(
        self,
        evidence: BuildVerificationEvidence,
    ) -> Path:
        """Persist one verification evidence document."""
        path = self._evidence_path(evidence.evidence_id)
        self._write_json(path, evidence.model_dump(mode="json"))
        return path

    def save_decision(
        self,
        decision: ReleaseGateDecision,
    ) -> Path:
        """Persist one release-gate decision document."""
        path = self._decision_path(decision.decision_id)
        self._write_json(path, decision.model_dump(mode="json"))
        return path

    def load_evidence(
        self,
        evidence_id: str,
    ) -> BuildVerificationEvidence:
        """Load one persisted verification evidence document."""
        path = self._evidence_path(evidence_id)

        if not path.is_file():
            raise BuildVerificationNotFoundError(
                f"verification evidence not found: {evidence_id}"
            )

        try:
            return BuildVerificationEvidence.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except OSError as exc:
            raise BuildVerificationPersistenceError(
                f"unable to load verification evidence: {evidence_id}"
            ) from exc

    def load_decision(
        self,
        decision_id: str,
    ) -> ReleaseGateDecision:
        """Load one persisted release-gate decision."""
        path = self._decision_path(decision_id)

        if not path.is_file():
            raise BuildVerificationNotFoundError(
                f"release decision not found: {decision_id}"
            )

        try:
            return ReleaseGateDecision.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except OSError as exc:
            raise BuildVerificationPersistenceError(
                f"unable to load release decision: {decision_id}"
            ) from exc

    def list_evidence_ids(self) -> tuple[str, ...]:
        """Return persisted evidence identifiers deterministically."""
        directory = self.root / "evidence"

        if not directory.is_dir():
            return ()

        return tuple(
            sorted(path.stem for path in directory.glob("*.json"))
        )
'@

Write-Utf8NoBom "forge\build_verification\reporting.py" @'
"""Reporting for M3.7 Build Verification."""

from __future__ import annotations

import json
from pathlib import Path

from forge.build_verification.errors import BuildVerificationReportError
from forge.build_verification.models import (
    BuildVerificationEvidence,
    ReleaseGateDecision,
)


def render_markdown(
    evidence: BuildVerificationEvidence,
    decision: ReleaseGateDecision,
) -> str:
    """Render a concise release-verification report."""
    lines = [
        "# Build Verification Report",
        "",
        f"- Evidence ID: `{evidence.evidence_id}`",
        f"- Request ID: `{evidence.request.request_id}`",
        f"- Source revision: `{evidence.request.source_revision}`",
        f"- Verification status: `{evidence.status.value}`",
        f"- Release decision: `{decision.decision.value}`",
        f"- Repository fingerprint: `{evidence.repository_fingerprint}`",
        "",
        "## Verification Steps",
        "",
    ]

    for result in evidence.step_results:
        lines.extend(
            [
                f"### {result.step_id}",
                "",
                f"- Status: `{result.status.value}`",
                f"- Exit code: `{result.exit_code}`",
                f"- Duration: `{result.duration_seconds:.3f}s`",
                f"- Findings: `{len(result.findings)}`",
                "",
            ]
        )

    lines.extend(["## Decision Reasons", ""])
    lines.extend(f"- {reason}" for reason in decision.reasons)
    lines.append("")

    if decision.blocking_findings:
        lines.extend(["## Blocking Findings", ""])
        lines.extend(
            f"- `{finding_id}`"
            for finding_id in decision.blocking_findings
        )
        lines.append("")

    return "\n".join(lines)


def write_report_bundle(
    evidence: BuildVerificationEvidence,
    decision: ReleaseGateDecision,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON and Markdown release-verification reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        evidence_path = destination / "BUILD_VERIFICATION_EVIDENCE.json"
        decision_path = destination / "RELEASE_GATE_DECISION.json"
        markdown_path = destination / "BUILD_VERIFICATION_REPORT.md"

        evidence_path.write_text(
            json.dumps(
                evidence.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        decision_path.write_text(
            json.dumps(
                decision.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(
            render_markdown(evidence, decision),
            encoding="utf-8",
        )
    except OSError as exc:
        raise BuildVerificationReportError(
            f"unable to write build verification report bundle: {exc}"
        ) from exc

    return {
        evidence_path.name: evidence_path,
        decision_path.name: decision_path,
        markdown_path.name: markdown_path,
    }
'@

Write-Utf8NoBom "forge\build_verification\service.py" @'
"""Application service for M3.7 Build Verification."""

from __future__ import annotations

import subprocess
from pathlib import Path

from forge.build_verification.identifiers import (
    verification_request_identifier,
    verification_step_identifier,
)
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    ReleaseGateDecision,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.pipeline import BuildVerificationPipeline
from forge.build_verification.policies import (
    resolve_repository_root,
    validate_target_paths,
)
from forge.build_verification.reporting import write_report_bundle
from forge.build_verification.store import BuildVerificationStore


class BuildVerificationService:
    """Coordinate request creation, execution, persistence, and reporting."""

    def __init__(
        self,
        policy: BuildVerificationPolicy | None = None,
    ) -> None:
        self.policy = policy or BuildVerificationPolicy()
        self.pipeline = BuildVerificationPipeline(self.policy)

    @staticmethod
    def source_revision(repository_root: Path) -> str:
        """Return the current Git revision."""
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )

        if completed.returncode != 0:
            raise ValueError("unable to resolve repository source revision")

        return completed.stdout.strip()

    def create_request(
        self,
        repository_root: str | Path,
        *,
        objective: str,
        tools: tuple[VerificationTool, ...],
        target_paths: tuple[str, ...] = (),
    ) -> BuildVerificationRequest:
        """Create a deterministic verification request."""
        root = resolve_repository_root(repository_root)
        normalized_paths = validate_target_paths(root, target_paths)
        revision = self.source_revision(root)

        steps = tuple(
            VerificationStep(
                step_id=verification_step_identifier(
                    {
                        "tool": tool.value,
                        "position": index,
                        "target_paths": normalized_paths,
                    }
                ),
                tool=tool,
                name=tool.value.replace("_", " ").title(),
                arguments=normalized_paths or (".",),
            )
            for index, tool in enumerate(tools, start=1)
        )

        request_id = verification_request_identifier(
            {
                "repository_root": str(root),
                "source_revision": revision,
                "objective": objective,
                "tools": [tool.value for tool in tools],
                "target_paths": normalized_paths,
            }
        )

        return BuildVerificationRequest(
            request_id=request_id,
            repository_root=str(root),
            source_revision=revision,
            objective=objective,
            steps=steps,
            target_paths=normalized_paths,
        )

    def verify(
        self,
        request: BuildVerificationRequest,
        *,
        store: BuildVerificationStore | None = None,
        report_directory: Path | None = None,
    ) -> ReleaseGateDecision:
        """Execute verification and optionally persist all artifacts."""
        evidence, decision = self.pipeline.execute(request)

        if store is not None:
            store.save_evidence(evidence)
            store.save_decision(decision)

        if report_directory is not None:
            write_report_bundle(
                evidence,
                decision,
                report_directory,
            )

        return decision
'@

Write-Utf8NoBom "tests\test_build_verification_store.py" @'
from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)
from forge.build_verification.store import BuildVerificationStore


def evidence_for(tmp_path: Path):
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(step,),
        target_paths=("sample.py",),
    )
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime.now(UTC),
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)
    return build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )


def test_store_round_trip(tmp_path: Path) -> None:
    evidence = evidence_for(tmp_path)
    decision = decide_release(
        evidence,
        BuildVerificationPolicy(),
    )
    store = BuildVerificationStore(tmp_path / "memory")

    store.save_evidence(evidence)
    store.save_decision(decision)

    assert store.load_evidence(evidence.evidence_id) == evidence
    assert store.load_decision(decision.decision_id) == decision


def test_store_lists_evidence_deterministically(tmp_path: Path) -> None:
    evidence = evidence_for(tmp_path)
    store = BuildVerificationStore(tmp_path / "memory")
    store.save_evidence(evidence)

    assert store.list_evidence_ids() == (evidence.evidence_id,)
'@

Write-Utf8NoBom "tests\test_build_verification_reporting.py" @'
from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)
from forge.build_verification.reporting import (
    render_markdown,
    write_report_bundle,
)


def report_inputs(tmp_path: Path):
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(step,),
        target_paths=("sample.py",),
    )
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime.now(UTC),
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)
    evidence = build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )
    return evidence, decide_release(
        evidence,
        BuildVerificationPolicy(),
    )


def test_markdown_contains_release_decision(tmp_path: Path) -> None:
    evidence, decision = report_inputs(tmp_path)
    rendered = render_markdown(evidence, decision)

    assert "Build Verification Report" in rendered
    assert decision.decision.value in rendered


def test_report_bundle_writes_all_artifacts(tmp_path: Path) -> None:
    evidence, decision = report_inputs(tmp_path)
    written = write_report_bundle(
        evidence,
        decision,
        tmp_path / "reports",
    )

    assert set(written) == {
        "BUILD_VERIFICATION_EVIDENCE.json",
        "RELEASE_GATE_DECISION.json",
        "BUILD_VERIFICATION_REPORT.md",
    }
'@

Write-Utf8NoBom "tests\test_build_verification_service.py" @'
from pathlib import Path

from forge.build_verification.models import (
    ReleaseDecision,
    VerificationTool,
)
from forge.build_verification.service import BuildVerificationService
from forge.build_verification.store import BuildVerificationStore


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


def test_service_creates_deterministic_request(tmp_path: Path) -> None:
    initialize_git_repository(tmp_path)
    service = BuildVerificationService()

    first = service.create_request(
        tmp_path,
        objective="verify",
        tools=(VerificationTool.RUFF,),
        target_paths=("sample.py",),
    )
    second = service.create_request(
        tmp_path,
        objective="verify",
        tools=(VerificationTool.RUFF,),
        target_paths=("sample.py",),
    )

    assert first.request_id == second.request_id


def test_service_verifies_and_persists(tmp_path: Path) -> None:
    initialize_git_repository(tmp_path)
    service = BuildVerificationService()
    request = service.create_request(
        tmp_path,
        objective="verify",
        tools=(VerificationTool.RUFF,),
        target_paths=("sample.py",),
    )
    store = BuildVerificationStore(tmp_path / "memory")

    decision = service.verify(
        request,
        store=store,
        report_directory=tmp_path / "reports",
    )

    assert decision.decision is ReleaseDecision.APPROVED
    assert len(store.list_evidence_ids()) == 1
    assert (tmp_path / "reports" / "BUILD_VERIFICATION_REPORT.md").is_file()
'@

Write-Host ""
Write-Host "M3.7 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_build_verification_service.py `
    .\tests\test_build_verification_store.py `
    .\tests\test_build_verification_reporting.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.7 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.7 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short