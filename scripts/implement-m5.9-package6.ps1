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

$ExpectedBranch = "feature/m5.9-general-engineering-agent"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.9 Package 6 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$Prerequisites = @(
    ".\forge\general_engineering\execution_service.py",
    ".\forge\general_engineering\edit_synthesis_service.py",
    ".\forge\general_engineering\repository_grounding.py",
    ".\forge\general_engineering\protocols.py"
)
foreach ($Path in $Prerequisites) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.9 Package 6 prerequisite: $Path"
    }
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.9 Package 6."
}

Write-Utf8NoBom "forge\general_engineering\validation_commands.py" @'
"""Bounded validation-command resolution for M5.9 Package 6."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationCommand:
    capability: str
    argv: tuple[str, ...]


def resolve_validation_commands(
    repository_root: str | Path,
    capabilities: tuple[str, ...],
) -> tuple[ValidationCommand, ...]:
    """Resolve known validation capabilities without invoking a shell."""
    root = Path(repository_root).resolve()
    has_python_project = (root / "pyproject.toml").is_file()
    commands: list[ValidationCommand] = []

    for capability in capabilities:
        if capability == "repository_tests" and has_python_project:
            commands.append(
                ValidationCommand(
                    capability=capability,
                    argv=(
                        sys.executable,
                        "-m",
                        "pytest",
                        "-p",
                        "no:cacheprovider",
                    ),
                )
            )
        elif capability == "static_analysis" and has_python_project:
            commands.extend(
                (
                    ValidationCommand(
                        capability=capability,
                        argv=(sys.executable, "-m", "ruff", "check", "."),
                    ),
                    ValidationCommand(
                        capability=capability,
                        argv=(sys.executable, "-m", "mypy", "."),
                    ),
                )
            )
        elif capability == "focused_tests" and has_python_project:
            commands.append(
                ValidationCommand(
                    capability=capability,
                    argv=(
                        sys.executable,
                        "-m",
                        "pytest",
                        "-p",
                        "no:cacheprovider",
                    ),
                )
            )

    unique: list[ValidationCommand] = []
    seen: set[tuple[str, ...]] = set()
    for command in commands:
        if command.argv in seen:
            continue
        seen.add(command.argv)
        unique.append(command)
    return tuple(unique)
'@

Write-Utf8NoBom "forge\general_engineering\validation_executor.py" @'
"""Bounded validation execution for M5.9 Package 6."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from forge.general_engineering.identifiers import validation_outcome_identifier
from forge.general_engineering.models import ChangePlan, EngineeringRequest, ValidationOutcome
from forge.general_engineering.states import ValidationStatus
from forge.general_engineering.validation_commands import (
    ValidationCommand,
    resolve_validation_commands,
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[tuple[str, ...], Path, int], CommandResult]


def _default_runner(argv: tuple[str, ...], cwd: Path, timeout: int) -> CommandResult:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


class EngineeringValidationExecutor:
    """Execute only policy-resolved argv commands with shell disabled."""

    def __init__(
        self,
        *,
        runner: CommandRunner = _default_runner,
        timeout_seconds: int = 300,
    ) -> None:
        self.runner = runner
        self.timeout_seconds = timeout_seconds

    def validate(
        self,
        *,
        request: EngineeringRequest,
        plan: ChangePlan,
    ) -> ValidationOutcome:
        if plan.validation_plan.commands:
            return self._outcome(
                plan=plan,
                status=ValidationStatus.BLOCKED,
                summary=(
                    "Raw validation commands are not executable in M5.9 Package 6; "
                    "use approved validation capabilities."
                ),
                commands_run=(),
                failures=("raw validation commands are not allowlisted",),
            )

        commands = resolve_validation_commands(
            request.repository_root,
            plan.validation_plan.capabilities,
        )
        if not commands:
            return self._outcome(
                plan=plan,
                status=ValidationStatus.BLOCKED,
                summary="No bounded validation command could be resolved.",
                commands_run=(),
                failures=("no supported validation capability for repository",),
            )

        repository_root = Path(request.repository_root).resolve()
        commands_run: list[str] = []
        failures: list[str] = []

        for command in commands:
            rendered = " ".join(command.argv)
            commands_run.append(rendered)
            try:
                result = self.runner(
                    command.argv,
                    repository_root,
                    self.timeout_seconds,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                failures.append(f"{command.capability}: {exc}")
                continue

            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                if len(detail) > 4000:
                    detail = detail[-4000:]
                failures.append(
                    f"{command.capability} failed with exit code "
                    f"{result.returncode}: {detail}"
                )

        status = ValidationStatus.FAILED if failures else ValidationStatus.PASSED
        summary = (
            "Validation passed."
            if status is ValidationStatus.PASSED
            else f"Validation failed in {len(failures)} command(s)."
        )
        return self._outcome(
            plan=plan,
            status=status,
            summary=summary,
            commands_run=tuple(commands_run),
            failures=tuple(failures),
        )

    @staticmethod
    def _outcome(
        *,
        plan: ChangePlan,
        status: ValidationStatus,
        summary: str,
        commands_run: tuple[str, ...],
        failures: tuple[str, ...],
    ) -> ValidationOutcome:
        payload = {
            "validation_plan_id": plan.validation_plan.validation_plan_id,
            "status": status.value,
            "commands_run": commands_run,
            "failures": failures,
        }
        return ValidationOutcome(
            outcome_id=validation_outcome_identifier(payload),
            validation_plan_id=plan.validation_plan.validation_plan_id,
            status=status,
            summary=summary,
            commands_run=commands_run,
            failures=failures,
            evidence_ids=plan.evidence_ids,
        )


engineering_validation_executor = EngineeringValidationExecutor()
'@

Write-Utf8NoBom "forge\general_engineering\repair_policy.py" @'
"""Bounded repair authorization for M5.9 Package 6."""

from __future__ import annotations

from forge.general_engineering.errors import EngineeringRepairError
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringRequest,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.states import ValidationStatus


def validate_repair_proposal(
    *,
    request: EngineeringRequest,
    plan: ChangePlan,
    validation_outcome: ValidationOutcome,
    proposal: RepairProposal,
    attempt_number: int,
) -> None:
    if validation_outcome.status is not ValidationStatus.FAILED:
        raise EngineeringRepairError(
            "Repair is permitted only after failed validation."
        )
    if proposal.request_id != request.request_id:
        raise EngineeringRepairError("Repair proposal belongs to another request.")
    if proposal.validation_outcome_id != validation_outcome.outcome_id:
        raise EngineeringRepairError(
            "Repair proposal references another validation outcome."
        )
    if proposal.attempt_number != attempt_number:
        raise EngineeringRepairError("Repair attempt number mismatch.")
    if attempt_number > request.max_repair_attempts:
        raise EngineeringRepairError("Maximum repair attempts exceeded.")

    planned_paths = {item.path for item in plan.file_changes}
    repair_paths = set(proposal.target_paths)
    if not repair_paths.issubset(planned_paths):
        raise EngineeringRepairError(
            "Repair proposal expands beyond the approved change-plan scope."
        )
'@

Write-Utf8NoBom "forge\general_engineering\repair_plan.py" @'
"""Construct evidence-refreshed bounded repair plans."""

from __future__ import annotations

from forge.general_engineering.errors import EngineeringRepairError
from forge.general_engineering.identifiers import change_plan_identifier
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    RepairProposal,
)


def build_repair_change_plan(
    *,
    original_plan: ChangePlan,
    refreshed_context: EngineeringContext,
    proposal: RepairProposal,
) -> ChangePlan:
    relevant = {item.path: item for item in refreshed_context.relevant_files}
    original = {item.path: item for item in original_plan.file_changes}
    selected = []

    for path in proposal.target_paths:
        if path not in original:
            raise EngineeringRepairError(
                f"Repair target is outside original plan: {path}"
            )
        grounded = relevant.get(path)
        if grounded is None:
            raise EngineeringRepairError(
                f"Repair target is no longer repository-grounded: {path}"
            )
        selected.append(
            original[path].model_copy(
                update={
                    "evidence_ids": grounded.evidence_ids,
                    "rationale": (
                        f"Repair attempt {proposal.attempt_number}: "
                        f"{proposal.diagnosis}"
                    ),
                }
            )
        )

    evidence_ids = tuple(
        sorted(
            {
                evidence_id
                for item in selected
                for evidence_id in item.evidence_ids
            }
        )
    )
    payload = {
        "original_plan_id": original_plan.plan_id,
        "repair_id": proposal.repair_id,
        "attempt_number": proposal.attempt_number,
        "paths": proposal.target_paths,
        "evidence_ids": evidence_ids,
    }

    return original_plan.model_copy(
        update={
            "plan_id": change_plan_identifier(payload),
            "file_changes": tuple(selected),
            "evidence_ids": evidence_ids,
            "expected_effect": (
                f"Repair validation failure: {proposal.diagnosis}"
            ),
        }
    )
'@

Write-Utf8NoBom "forge\general_engineering\repair_service.py" @'
"""One approved bounded repair attempt for M5.9 Package 6."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.edit_synthesis_service import (
    EngineeringEditSynthesisService,
)
from forge.general_engineering.execution_service import EngineeringExecutionService
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.protocols import EngineeringProvider
from forge.general_engineering.repair_plan import build_repair_change_plan
from forge.general_engineering.repair_policy import validate_repair_proposal
from forge.general_engineering.repository_grounding import RepositoryGroundingService
from forge.general_engineering.validation_executor import EngineeringValidationExecutor


@dataclass(frozen=True)
class RepairAttemptResult:
    proposal: RepairProposal
    repair_plan: ChangePlan
    validation_outcome: ValidationOutcome


class EngineeringRepairService:
    """Perform one explicitly approved repair within the original plan scope."""

    def __init__(
        self,
        *,
        grounding: RepositoryGroundingService | None = None,
        synthesis: EngineeringEditSynthesisService | None = None,
        execution: EngineeringExecutionService | None = None,
        validation: EngineeringValidationExecutor | None = None,
    ) -> None:
        self.grounding = grounding or RepositoryGroundingService()
        self.synthesis = synthesis or EngineeringEditSynthesisService()
        self.execution = execution or EngineeringExecutionService()
        self.validation = validation or EngineeringValidationExecutor()

    def repair_once(
        self,
        *,
        provider: EngineeringProvider,
        request: EngineeringRequest,
        original_plan: ChangePlan,
        previous_context: EngineeringContext,
        validation_outcome: ValidationOutcome,
        attempt_number: int,
        approved: bool,
    ) -> RepairAttemptResult:
        if not approved:
            raise PermissionError("Repair execution requires explicit approval.")

        proposal = provider.propose_repair(
            request=request,
            context=previous_context,
            plan=original_plan,
            validation_outcome=validation_outcome,
            attempt_number=attempt_number,
        )
        validate_repair_proposal(
            request=request,
            plan=original_plan,
            validation_outcome=validation_outcome,
            proposal=proposal,
            attempt_number=attempt_number,
        )

        refreshed_context = self.grounding.ground(request).context
        repair_plan = build_repair_change_plan(
            original_plan=original_plan,
            refreshed_context=refreshed_context,
            proposal=proposal,
        )
        synthesis = self.synthesis.synthesize(
            provider=provider,
            request=request,
            context=refreshed_context,
            plan=repair_plan,
        )
        self.execution.execute(
            request=request,
            plan=repair_plan,
            change_set=synthesis.change_set,
            approved=True,
            dry_run=False,
        )
        outcome = self.validation.validate(
            request=request,
            plan=original_plan,
        )
        return RepairAttemptResult(
            proposal=proposal,
            repair_plan=repair_plan,
            validation_outcome=outcome,
        )
'@

Write-Utf8NoBom "forge\general_engineering\validation_repair_loop.py" @'
"""Bounded validation-and-repair orchestration for M5.9 Package 6."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.protocols import EngineeringProvider
from forge.general_engineering.repair_service import EngineeringRepairService
from forge.general_engineering.states import ValidationStatus
from forge.general_engineering.validation_executor import EngineeringValidationExecutor


@dataclass(frozen=True)
class ValidationRepairResult:
    final_outcome: ValidationOutcome
    repairs: tuple[RepairProposal, ...]
    completed: bool
    exhausted: bool


class ValidationRepairLoop:
    """Validate, repair only when approved, and stop at the request limit."""

    def __init__(
        self,
        *,
        validation: EngineeringValidationExecutor | None = None,
        repair: EngineeringRepairService | None = None,
    ) -> None:
        self.validation = validation or EngineeringValidationExecutor()
        self.repair = repair or EngineeringRepairService(validation=self.validation)

    def run(
        self,
        *,
        provider: EngineeringProvider,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
        approve_repairs: bool,
    ) -> ValidationRepairResult:
        outcome = self.validation.validate(request=request, plan=plan)
        repairs: list[RepairProposal] = []

        if outcome.status is ValidationStatus.PASSED:
            return ValidationRepairResult(
                final_outcome=outcome,
                repairs=(),
                completed=True,
                exhausted=False,
            )

        if outcome.status is not ValidationStatus.FAILED or not approve_repairs:
            return ValidationRepairResult(
                final_outcome=outcome,
                repairs=(),
                completed=False,
                exhausted=False,
            )

        for attempt_number in range(1, request.max_repair_attempts + 1):
            attempted = self.repair.repair_once(
                provider=provider,
                request=request,
                original_plan=plan,
                previous_context=context,
                validation_outcome=outcome,
                attempt_number=attempt_number,
                approved=True,
            )
            repairs.append(attempted.proposal)
            outcome = attempted.validation_outcome
            if outcome.status is ValidationStatus.PASSED:
                return ValidationRepairResult(
                    final_outcome=outcome,
                    repairs=tuple(repairs),
                    completed=True,
                    exhausted=False,
                )
            if outcome.status is not ValidationStatus.FAILED:
                return ValidationRepairResult(
                    final_outcome=outcome,
                    repairs=tuple(repairs),
                    completed=False,
                    exhausted=False,
                )

        return ValidationRepairResult(
            final_outcome=outcome,
            repairs=tuple(repairs),
            completed=False,
            exhausted=True,
        )


validation_repair_loop = ValidationRepairLoop()
'@

Write-Utf8NoBom "tests\test_general_engineering_validation_commands.py" @'
from pathlib import Path

from forge.general_engineering.validation_commands import resolve_validation_commands


def test_python_capabilities_resolve_without_shell(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    commands = resolve_validation_commands(
        tmp_path,
        ("repository_tests", "static_analysis", "focused_tests"),
    )
    rendered = tuple(item.argv[2:] for item in commands)
    assert ("pytest", "-p", "no:cacheprovider") in rendered
    assert ("ruff", "check", ".") in rendered
    assert ("mypy", ".") in rendered
'@

Write-Utf8NoBom "tests\test_general_engineering_validation_executor.py" @'
from pathlib import Path

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    FileChangePlan,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import EditOperationType, EngineeringRisk, ValidationStatus
from forge.general_engineering.validation_executor import CommandResult, EngineeringValidationExecutor


def _plan(request_id: str) -> ChangePlan:
    requirement = ChangeRequirement(requirement_id="r1", description="change")
    return ChangePlan(
        plan_id="p1",
        request_id=request_id,
        objective="change",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("e1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="change",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="v1",
            capabilities=("repository_tests",),
        ),
        expected_effect="change",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("e1",),
    )


def test_validation_executor_records_failure(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    request = build_engineering_request(objective="change", repository_root=tmp_path)

    def runner(argv: tuple[str, ...], cwd: Path, timeout: int) -> CommandResult:
        assert cwd == tmp_path.resolve()
        assert timeout == 30
        return CommandResult(returncode=1, stdout="failed", stderr="")

    outcome = EngineeringValidationExecutor(runner=runner, timeout_seconds=30).validate(
        request=request,
        plan=_plan(request.request_id),
    )
    assert outcome.status is ValidationStatus.FAILED
    assert outcome.failures
'@

Write-Utf8NoBom "tests\test_general_engineering_repair_policy.py" @'
from pathlib import Path

import pytest

from forge.general_engineering.errors import EngineeringRepairError
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    FileChangePlan,
    RepairProposal,
    ValidationOutcome,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.repair_policy import validate_repair_proposal
from forge.general_engineering.states import EditOperationType, EngineeringRisk, ValidationStatus


def test_repair_cannot_expand_plan_scope(tmp_path: Path) -> None:
    request = build_engineering_request(objective="change", repository_root=tmp_path)
    requirement = ChangeRequirement(requirement_id="r1", description="change")
    plan = ChangePlan(
        plan_id="p1",
        request_id=request.request_id,
        objective="change",
        requirements=(requirement,),
        file_changes=(FileChangePlan(path="src/a.py", rationale="g", evidence_ids=("e",), intended_operations=(EditOperationType.REPLACE,), expected_effect="c"),),
        validation_plan=ValidationPlan(validation_plan_id="v1", capabilities=("repository_tests",)),
        expected_effect="change",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("e",),
    )
    outcome = ValidationOutcome(outcome_id="o1", validation_plan_id="v1", status=ValidationStatus.FAILED, summary="failed", failures=("x",))
    proposal = RepairProposal(repair_id="rp1", request_id=request.request_id, attempt_number=1, diagnosis="fix", target_paths=("src/b.py",), validation_outcome_id="o1")

    with pytest.raises(EngineeringRepairError, match="expands"):
        validate_repair_proposal(request=request, plan=plan, validation_outcome=outcome, proposal=proposal, attempt_number=1)
'@

Write-Utf8NoBom "tests\test_general_engineering_repair_plan.py" @'
from pathlib import Path

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EngineeringContext,
    FileChangePlan,
    RelevantFile,
    RepairProposal,
    RepositoryEvidence,
    ValidationPlan,
)
from forge.general_engineering.repair_plan import build_repair_change_plan
from forge.general_engineering.states import EditOperationType, EngineeringRisk, EvidenceType


def test_repair_plan_refreshes_evidence(tmp_path: Path) -> None:
    requirement = ChangeRequirement(requirement_id="r1", description="change")
    original = ChangePlan(plan_id="p1", request_id="req", objective="change", requirements=(requirement,), file_changes=(FileChangePlan(path="src/a.py", rationale="old", evidence_ids=("old",), intended_operations=(EditOperationType.REPLACE,), expected_effect="c"),), validation_plan=ValidationPlan(validation_plan_id="v1", capabilities=("repository_tests",)), expected_effect="c", aggregate_risk=EngineeringRisk.LOW, evidence_ids=("old",))
    context = EngineeringContext(request_id="req", relevant_files=(RelevantFile(path="src/a.py", evidence_ids=("new",), rationale="fresh"),), evidence=(RepositoryEvidence(evidence_id="new", path="src/a.py", evidence_type=EvidenceType.FILE, rationale="fresh", relevance=1.0, fingerprint="fp"),))
    proposal = RepairProposal(repair_id="rp1", request_id="req", attempt_number=1, diagnosis="repair", target_paths=("src/a.py",), validation_outcome_id="o1")

    repaired = build_repair_change_plan(original_plan=original, refreshed_context=context, proposal=proposal)
    assert repaired.plan_id != original.plan_id
    assert repaired.evidence_ids == ("new",)
'@

Write-Utf8NoBom "tests\test_general_engineering_validation_repair_loop.py" @'
from pathlib import Path

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EngineeringContext,
    FileChangePlan,
    RelevantFile,
    RepositoryEvidence,
    ValidationOutcome,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import EditOperationType, EngineeringRisk, EvidenceType, ValidationStatus
from forge.general_engineering.validation_repair_loop import ValidationRepairLoop


class PassingValidation:
    def validate(self, *, request, plan) -> ValidationOutcome:
        return ValidationOutcome(outcome_id="ok", validation_plan_id=plan.validation_plan.validation_plan_id, status=ValidationStatus.PASSED, summary="passed")


class ProviderStub:
    pass


def test_loop_stops_immediately_when_validation_passes(tmp_path: Path) -> None:
    request = build_engineering_request(objective="change", repository_root=tmp_path)
    requirement = ChangeRequirement(requirement_id="r1", description="change")
    plan = ChangePlan(plan_id="p1", request_id=request.request_id, objective="change", requirements=(requirement,), file_changes=(FileChangePlan(path="src/a.py", rationale="g", evidence_ids=("e",), intended_operations=(EditOperationType.REPLACE,), expected_effect="c"),), validation_plan=ValidationPlan(validation_plan_id="v1", capabilities=("repository_tests",)), expected_effect="c", aggregate_risk=EngineeringRisk.LOW, evidence_ids=("e",))
    context = EngineeringContext(request_id=request.request_id, relevant_files=(RelevantFile(path="src/a.py", evidence_ids=("e",), rationale="g"),), evidence=(RepositoryEvidence(evidence_id="e", path="src/a.py", evidence_type=EvidenceType.FILE, rationale="g", relevance=1.0),))

    result = ValidationRepairLoop(validation=PassingValidation()).run(provider=ProviderStub(), request=request, context=context, plan=plan, approve_repairs=False)  # type: ignore[arg-type]
    assert result.completed is True
    assert result.repairs == ()
'@

Write-Utf8NoBom "scripts\validate-m5.9-package6.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @("feature/m5.9-general-engineering-agent", "main")
$CurrentBranch = git branch --show-current
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 6 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\validation_commands.py",
    ".\forge\general_engineering\validation_executor.py",
    ".\forge\general_engineering\repair_policy.py",
    ".\forge\general_engineering\repair_plan.py",
    ".\forge\general_engineering\repair_service.py",
    ".\forge\general_engineering\validation_repair_loop.py",
    ".\tests\test_general_engineering_validation_commands.py",
    ".\tests\test_general_engineering_validation_executor.py",
    ".\tests\test_general_engineering_repair_policy.py",
    ".\tests\test_general_engineering_repair_plan.py",
    ".\tests\test_general_engineering_validation_repair_loop.py"
)
foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) { throw "Missing Package 6 file: $Path" }
    if ((Get-Item $Path).Length -eq 0) { throw "Empty Package 6 file: $Path" }
}

$ValidationExecutor = Get-Content ".\forge\general_engineering\validation_executor.py" -Raw
if ($ValidationExecutor -match "shell=True|os\.system|Popen\(") {
    throw "Package 6 validation execution is not sufficiently bounded."
}
if ($ValidationExecutor -notmatch "shell=False") {
    throw "Package 6 validation subprocesses must explicitly disable shell execution."
}

$RepairService = Get-Content ".\forge\general_engineering\repair_service.py" -Raw
if ($RepairService -notmatch "EngineeringExecutionService") {
    throw "Package 6 repairs must flow through governed Package 5 execution."
}
if ($RepairService -notmatch "approved") {
    throw "Package 6 repair execution must require explicit approval."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 6 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Validation/repair modules: 6"
Write-Host "Focused test files: 5"
Write-Host "Validation shell execution: DISABLED"
Write-Host "Repair mutation path: Package 5 governed execution ONLY"
'@

Write-Host ""
Write-Host "M5.9 Package 6 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff"
python -m mypy .
Assert-CommandSuccess "MyPy"
python -m pytest `
    .\tests\test_general_engineering_validation_commands.py `
    .\tests\test_general_engineering_validation_executor.py `
    .\tests\test_general_engineering_repair_policy.py `
    .\tests\test_general_engineering_repair_plan.py `
    .\tests\test_general_engineering_validation_repair_loop.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.9 Package 6 focused tests"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.9-package6.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.9 Package 6 validation"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository regression"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "M5.9 PACKAGE 6 VALIDATION & REPAIR COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "Repair attempts are bounded by EngineeringRequest.max_repair_attempts." -ForegroundColor Yellow
Write-Host "Repair execution requires explicit approval and uses Package 5 only." -ForegroundColor Yellow
Write-Host ""
git status --short
