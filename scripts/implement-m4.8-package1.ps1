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

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\architecture.py" @'
"""Architecture validation for M4.8 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def architecture_check() -> PhaseValidationCheck:
    payload = {
        "name": "Architecture validation",
        "kind": PhaseValidationKind.ARCHITECTURE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Architecture validation",
        kind=PhaseValidationKind.ARCHITECTURE,
        description=(
            "Verify that required architecture documents and "
            "implementation packages exist."
        ),
    )


def validate_architecture(
    repository_root: Path,
    phase: str,
) -> PhaseValidationResult:
    check = architecture_check()
    phase_key = phase.lower().replace("phase", "").strip()
    required = (
        repository_root
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
        / "ARCHITECTURE.md"
    )

    exists = required.is_file()
    status = (
        PhaseValidationStatus.PASS
        if exists
        else PhaseValidationStatus.FAIL
    )
    message = (
        f"Phase {phase_key} architecture baseline is available."
        if exists
        else f"Phase {phase_key} architecture baseline is missing."
    )
    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "path": required.as_posix(),
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=message,
        evidence={"path": required.as_posix()},
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\acceptance.py" @'
"""Acceptance-criteria validation for M4.8 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def acceptance_check() -> PhaseValidationCheck:
    payload = {
        "name": "Acceptance criteria validation",
        "kind": PhaseValidationKind.ACCEPTANCE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Acceptance criteria validation",
        kind=PhaseValidationKind.ACCEPTANCE,
        description=(
            "Verify that milestone acceptance criteria exist and "
            "contain actionable entries."
        ),
    )


def validate_acceptance_criteria(
    repository_root: Path,
) -> PhaseValidationResult:
    check = acceptance_check()
    path = (
        repository_root
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
        / "ACCEPTANCE_CRITERIA.md"
    )

    content = (
        path.read_text(encoding="utf-8")
        if path.is_file()
        else ""
    )
    actionable_lines = tuple(
        line
        for line in content.splitlines()
        if line.strip().startswith("- ")
    )
    passed = bool(actionable_lines)
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )
    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "item_count": len(actionable_lines),
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Acceptance criteria are defined."
            if passed
            else "Acceptance criteria are missing or empty."
        ),
        evidence={
            "path": path.as_posix(),
            "item_count": str(len(actionable_lines)),
        },
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\registry.py" @'
"""Validation-check registry for M4.8 Package 1."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from forge.domain_intelligence.phase_validation.acceptance import (
    acceptance_check,
    validate_acceptance_criteria,
)
from forge.domain_intelligence.phase_validation.architecture import (
    architecture_check,
    validate_architecture,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationResult,
)

ValidationRunner = Callable[
    [Path, str],
    PhaseValidationResult,
]


def _run_acceptance(
    repository_root: Path,
    phase: str,
) -> PhaseValidationResult:
    del phase
    return validate_acceptance_criteria(repository_root)


class PhaseValidationRegistry:
    """Deterministic registry of phase validation checks."""

    def __init__(self) -> None:
        self._entries: dict[
            str,
            tuple[PhaseValidationCheck, ValidationRunner],
        ] = {}

    @classmethod
    def default(cls) -> "PhaseValidationRegistry":
        registry = cls()
        registry.register(
            architecture_check(),
            validate_architecture,
        )
        registry.register(
            acceptance_check(),
            _run_acceptance,
        )
        return registry

    def register(
        self,
        check: PhaseValidationCheck,
        runner: ValidationRunner,
    ) -> None:
        self._entries[check.check_id] = (check, runner)

    def checks(self) -> tuple[PhaseValidationCheck, ...]:
        return tuple(
            entry[0]
            for _, entry in sorted(
                self._entries.items(),
                key=lambda item: (
                    item[1][0].kind.value,
                    item[1][0].name,
                ),
            )
        )

    def execute(
        self,
        repository_root: Path,
        phase: str,
    ) -> tuple[PhaseValidationResult, ...]:
        return tuple(
            runner(repository_root, phase)
            for _, runner in (
                entry
                for _, entry in sorted(
                    self._entries.items(),
                    key=lambda item: (
                        item[1][0].kind.value,
                        item[1][0].name,
                    ),
                )
            )
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\service.py" @'
"""Phase-validation service for M4.8 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_report_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationReport,
    PhaseValidationRequest,
)
from forge.domain_intelligence.phase_validation.policies import (
    PhaseValidationPolicy,
    resolve_phase_repository_root,
    validate_phase_request,
)
from forge.domain_intelligence.phase_validation.registry import (
    PhaseValidationRegistry,
)


class PhaseValidationService:
    """Execute deterministic phase validation checks."""

    def __init__(
        self,
        *,
        policy: PhaseValidationPolicy | None = None,
        registry: PhaseValidationRegistry | None = None,
    ) -> None:
        self._policy = policy or PhaseValidationPolicy()
        self._registry = (
            registry or PhaseValidationRegistry.default()
        )

    def validate(
        self,
        request: PhaseValidationRequest,
    ) -> PhaseValidationReport:
        validate_phase_request(request, self._policy)
        repository_root = resolve_phase_repository_root(
            request.repository_root,
            self._policy,
        )

        checks = self._registry.checks()
        results = self._registry.execute(
            repository_root,
            request.phase,
        )

        payload = {
            "phase": request.phase,
            "milestone": request.milestone,
            "check_ids": tuple(
                check.check_id for check in checks
            ),
            "result_ids": tuple(
                result.result_id for result in results
            ),
        }

        return PhaseValidationReport(
            report_id=phase_validation_report_identifier(payload),
            phase=request.phase,
            milestone=request.milestone,
            checks=checks,
            results=results,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_architecture.py" @'
from pathlib import Path

from forge.domain_intelligence.phase_validation.architecture import (
    architecture_check,
    validate_architecture,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationKind,
    PhaseValidationStatus,
)


def test_architecture_check_contract() -> None:
    check = architecture_check()

    assert check.kind is PhaseValidationKind.ARCHITECTURE
    assert check.required


def test_validate_architecture_passes(
    tmp_path: Path,
) -> None:
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

    result = validate_architecture(tmp_path, "4")

    assert result.status is PhaseValidationStatus.PASS
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_acceptance.py" @'
from pathlib import Path

from forge.domain_intelligence.phase_validation.acceptance import (
    validate_acceptance_criteria,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)


def test_validate_acceptance_criteria_passes(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
    )
    path.mkdir(parents=True)
    (path / "ACCEPTANCE_CRITERIA.md").write_text(
        "# Acceptance\n\n- Tests pass.\n",
        encoding="utf-8",
    )

    result = validate_acceptance_criteria(tmp_path)

    assert result.status is PhaseValidationStatus.PASS
    assert result.evidence["item_count"] == "1"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_registry.py" @'
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationKind,
)
from forge.domain_intelligence.phase_validation.registry import (
    PhaseValidationRegistry,
)


def test_default_phase_validation_registry() -> None:
    registry = PhaseValidationRegistry.default()

    assert {
        check.kind for check in registry.checks()
    } == {
        PhaseValidationKind.ACCEPTANCE,
        PhaseValidationKind.ARCHITECTURE,
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_service.py" @'
from pathlib import Path

from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)
from forge.domain_intelligence.phase_validation.service import (
    PhaseValidationService,
)


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


def test_phase_validation_service(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = PhaseValidationService().validate(
        PhaseValidationRequest(
            repository_root=str(tmp_path),
            phase="4",
        )
    )

    assert len(report.checks) == 2
    assert len(report.results) == 2
    assert report.passed
'@

Write-Host ""
Write-Host "M4.8 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_phase_validation_architecture.py `
    .\tests\test_domain_intelligence_phase_validation_acceptance.py `
    .\tests\test_domain_intelligence_phase_validation_registry.py `
    .\tests\test_domain_intelligence_phase_validation_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.8 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.8 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
