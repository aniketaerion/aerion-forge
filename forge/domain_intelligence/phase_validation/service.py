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

        executable_kinds = (
            "acceptance",
            "architecture",
        )

        checks = self._registry.checks(
            kinds=executable_kinds,
        )
        results = self._registry.execute(
            repository_root,
            request.phase,
            kinds=executable_kinds,
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