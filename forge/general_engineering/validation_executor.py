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
                    f"{command.capability} failed with exit code {result.returncode}: {detail}"
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
