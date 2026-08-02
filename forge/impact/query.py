"""Read-only deterministic Impact Decision queries."""

from forge.impact.errors import ImpactDecisionNotFoundError
from forge.impact.models import (
    DecisionStatus,
    ImpactAssessment,
    ImpactDecisionGeneration,
    ImpactDecisionStore,
    ImpactSeverity,
)


class ImpactQuery:
    """Read-only deterministic queries over an impact store."""

    def __init__(
        self,
        store: ImpactDecisionStore,
    ) -> None:
        self._store = store.model_copy(deep=True)

    def get_assessment(
        self,
        assessment_id: str,
    ) -> ImpactAssessment:
        """Return one assessment by ID."""

        try:
            assessment = self._store.assessments[assessment_id]
        except KeyError as exc:
            raise ImpactDecisionNotFoundError(
                f"Impact assessment not found: {assessment_id}"
            ) from exc

        return assessment.model_copy(deep=True)

    def list_assessments(
        self,
    ) -> tuple[ImpactAssessment, ...]:
        """Return all assessments in deterministic order."""

        return tuple(
            self.get_assessment(assessment_id) for assessment_id in sorted(self._store.assessments)
        )

    def list_by_mission(
        self,
        mission_id: str,
    ) -> tuple[ImpactAssessment, ...]:
        """Return assessments belonging to one mission."""

        return tuple(
            assessment
            for assessment in self.list_assessments()
            if assessment.mission_id == mission_id
        )

    def list_by_status(
        self,
        status: DecisionStatus,
    ) -> tuple[ImpactAssessment, ...]:
        """Return assessments with one decision status."""

        return tuple(
            assessment for assessment in self.list_assessments() if assessment.status is status
        )

    def list_by_severity(
        self,
        severity: ImpactSeverity,
    ) -> tuple[ImpactAssessment, ...]:
        """Return assessments with one impact severity."""

        return tuple(
            assessment
            for assessment in self.list_assessments()
            if assessment.overall_severity is severity
        )

    def list_blocked(
        self,
    ) -> tuple[ImpactAssessment, ...]:
        """Return blocked assessments."""

        return self.list_by_status(DecisionStatus.BLOCKED)

    def list_requiring_approval(
        self,
    ) -> tuple[ImpactAssessment, ...]:
        """Return assessments requiring human approval."""

        return self.list_by_status(DecisionStatus.APPROVAL_REQUIRED)

    def get_generation(
        self,
        assessment_id: str,
    ) -> ImpactDecisionGeneration:
        """Return active generation metadata."""

        try:
            generation = self._store.generations[assessment_id]
        except KeyError as exc:
            raise ImpactDecisionNotFoundError(
                f"Impact generation not found: {assessment_id}"
            ) from exc

        return generation.model_copy(deep=True)

    def get_history(
        self,
        assessment_id: str,
    ) -> tuple[ImpactAssessment, ...]:
        """Return historical assessment versions."""

        return tuple(
            assessment.model_copy(deep=True)
            for assessment in self._store.history.get(
                assessment_id,
                [],
            )
        )

    def statistics(self) -> dict[str, int]:
        """Return deterministic aggregate store statistics."""

        assessments = self.list_assessments()

        return {
            "total": len(assessments),
            "blocked": sum(
                assessment.status is DecisionStatus.BLOCKED for assessment in assessments
            ),
            "approval_required": sum(
                assessment.status is DecisionStatus.APPROVAL_REQUIRED for assessment in assessments
            ),
            "high": sum(
                assessment.overall_severity is ImpactSeverity.HIGH for assessment in assessments
            ),
            "critical": sum(
                assessment.overall_severity is ImpactSeverity.CRITICAL for assessment in assessments
            ),
        }
