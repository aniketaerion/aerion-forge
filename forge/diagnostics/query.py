"""Read-only typed diagnostic query API."""

from forge.diagnostics.errors import DiagnosticNotFoundError
from forge.diagnostics.models import (
    CorrectiveAction,
    DiagnosticCategory,
    DiagnosticChangeSet,
    DiagnosticDefinition,
    DiagnosticGeneration,
    DiagnosticResult,
    DiagnosticSnapshot,
    DiagnosticStatistics,
    DiagnosticSummary,
    HealthStatus,
)
from forge.diagnostics.registry import DIAGNOSTIC_REGISTRY


class DiagnosticQuery:
    def __init__(self, snapshot: DiagnosticSnapshot) -> None:
        self._snapshot = snapshot.model_copy(deep=True)

    def get_check(self, check_id: str) -> DiagnosticDefinition:
        return DIAGNOSTIC_REGISTRY.get_check(check_id).model_copy(deep=True)

    def list_checks(self) -> tuple[DiagnosticDefinition, ...]:
        return tuple(item.model_copy(deep=True) for item in DIAGNOSTIC_REGISTRY.list_checks())

    def list_results(self) -> tuple[DiagnosticResult, ...]:
        return tuple(item.model_copy(deep=True) for item in self._snapshot.results)

    def get_result(self, check_id: str) -> DiagnosticResult:
        for item in self._snapshot.results:
            if item.check_id == check_id:
                return item.model_copy(deep=True)
        raise DiagnosticNotFoundError(f"Diagnostic result not found: {check_id}")

    def list_results_by_status(self, status: HealthStatus) -> tuple[DiagnosticResult, ...]:
        return tuple(item for item in self.list_results() if item.status is status)

    def list_results_by_category(
        self, category: DiagnosticCategory
    ) -> tuple[DiagnosticResult, ...]:
        return tuple(item for item in self.list_results() if item.category is category)

    def list_blocking_results(self) -> tuple[DiagnosticResult, ...]:
        return tuple(item for item in self.list_results() if item.blocking)

    def list_actionable_results(self) -> tuple[DiagnosticResult, ...]:
        return tuple(item for item in self.list_results() if item.corrective_actions)

    def get_corrective_actions(self, check_id: str) -> tuple[CorrectiveAction, ...]:
        return self.get_result(check_id).corrective_actions

    def get_overall_status(self) -> HealthStatus:
        return self._snapshot.summary.overall_status

    def get_summary(self) -> DiagnosticSummary:
        return self._snapshot.summary.model_copy(deep=True)

    def get_statistics(self) -> DiagnosticStatistics:
        return self._snapshot.statistics.model_copy(deep=True)

    def get_diagnostic_fingerprint(self) -> str:
        return self._snapshot.diagnostic_fingerprint

    def get_generation(self) -> DiagnosticGeneration:
        return self._snapshot.generation.model_copy(deep=True)

    def get_changes(self) -> DiagnosticChangeSet:
        return self._snapshot.changes.model_copy(deep=True)

    def is_runtime_healthy(self) -> bool:
        return self.get_overall_status() is HealthStatus.HEALTHY

    def is_target_ready(self) -> bool:
        return self.get_overall_status() is HealthStatus.HEALTHY
