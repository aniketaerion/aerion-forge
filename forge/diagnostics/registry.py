"""Immutable, explicit diagnostic catalogue and implementation map."""

from collections.abc import Callable

from forge.diagnostics.definitions import diagnostic_definitions
from forge.diagnostics.errors import DiagnosticNotFoundError
from forge.diagnostics.models import DiagnosticDefinition, DiagnosticResult

CheckImplementation = Callable[[DiagnosticDefinition, object], DiagnosticResult]


class DiagnosticRegistry:
    def __init__(self) -> None:
        self._definitions = {item.check_id: item for item in diagnostic_definitions()}

    def list_checks(self) -> tuple[DiagnosticDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def get_check(self, check_id: str) -> DiagnosticDefinition:
        try:
            return self._definitions[check_id]
        except KeyError as exc:
            raise DiagnosticNotFoundError(f"Unknown diagnostic check: {check_id}") from exc


DIAGNOSTIC_REGISTRY = DiagnosticRegistry()
