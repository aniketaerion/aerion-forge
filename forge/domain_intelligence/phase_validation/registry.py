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
from forge.domain_intelligence.phase_validation.compatibility import (
    compatibility_check,
)
from forge.domain_intelligence.phase_validation.coverage import (
    coverage_check,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationResult,
)
from forge.domain_intelligence.phase_validation.release import (
    release_check,
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
        registry.register_placeholder(coverage_check())
        registry.register_placeholder(compatibility_check())
        registry.register_placeholder(release_check())
        return registry

    def register(
        self,
        check: PhaseValidationCheck,
        runner: ValidationRunner,
    ) -> None:
        self._entries[check.check_id] = (check, runner)

    def register_placeholder(
        self,
        check: PhaseValidationCheck,
    ) -> None:
        def _unsupported(
            repository_root: Path,
            phase: str,
        ) -> PhaseValidationResult:
            del repository_root, phase
            raise RuntimeError(
                f"Validation runner not configured: {check.name}"
            )

        self._entries[check.check_id] = (
            check,
            _unsupported,
        )

    def checks(
        self,
        *,
        kinds: tuple[str, ...] = (),
    ) -> tuple[PhaseValidationCheck, ...]:
        requested = set(kinds)

        return tuple(
            check
            for check, _ in (
                entry
                for _, entry in sorted(
                    self._entries.items(),
                    key=lambda item: (
                        item[1][0].kind.value,
                        item[1][0].name,
                    ),
                )
            )
            if not requested or check.kind.value in requested
        )

    def execute(
        self,
        repository_root: Path,
        phase: str,
        *,
        kinds: tuple[str, ...] = (),
    ) -> tuple[PhaseValidationResult, ...]:
        requested = set(kinds)

        return tuple(
            runner(repository_root, phase)
            for check, runner in (
                entry
                for _, entry in sorted(
                    self._entries.items(),
                    key=lambda item: (
                        item[1][0].kind.value,
                        item[1][0].name,
                    ),
                )
            )
            if not requested or check.kind.value in requested
        )