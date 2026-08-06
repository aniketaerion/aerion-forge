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
    def default(cls) -> PhaseValidationRegistry:
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