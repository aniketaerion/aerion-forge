"""Mission Reporting input validation."""

from forge.engineering_memory.models import EngineeringMemoryStore
from forge.impact.models import ImpactAssessment
from forge.mission_reporting.errors import (
    MissionReportingDisabledError,
    MissionReportingValidationError,
)
from forge.mission_reporting.models import (
    MissionReportingConfiguration,
    MissionReportingValidationMessage,
    MissionReportingValidationResult,
    MissionReportingValidationSeverity,
)
from forge.planning.models import MissionPlan
from forge.tasks.models import TaskSet


class MissionReportingValidator:
    """Validate Mission Reporting inputs and lineage."""

    def __init__(
        self,
        configuration: MissionReportingConfiguration | None = None,
    ) -> None:
        self.configuration = (
            configuration if configuration is not None else MissionReportingConfiguration()
        )

    def validate(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        engineering_memory: EngineeringMemoryStore,
    ) -> MissionReportingValidationResult:
        """Return deterministic validation messages for report inputs."""

        if not self.configuration.enabled:
            raise MissionReportingDisabledError("Mission Reporting capability is disabled.")

        messages: list[MissionReportingValidationMessage] = []

        self._validate_mission_and_tasks(
            mission,
            task_set,
            messages,
        )
        self._validate_assessment(
            mission,
            task_set,
            assessment,
            messages,
        )
        self._validate_engineering_memory(
            mission,
            assessment,
            engineering_memory,
            messages,
        )

        ordered = tuple(
            sorted(
                messages,
                key=lambda message: (
                    message.severity.value,
                    message.code,
                    message.field or "",
                    message.message,
                ),
            )
        )
        valid = not any(
            message.severity is MissionReportingValidationSeverity.ERROR for message in ordered
        )

        return MissionReportingValidationResult(
            valid=valid,
            messages=ordered,
        )

    def validate_or_raise(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        engineering_memory: EngineeringMemoryStore,
    ) -> MissionReportingValidationResult:
        """Validate inputs and raise when any error is present."""

        result = self.validate(
            mission,
            task_set,
            assessment,
            engineering_memory,
        )

        if not result.valid:
            details = "; ".join(
                f"{message.code}: {message.message}"
                for message in result.messages
                if message.severity is MissionReportingValidationSeverity.ERROR
            )
            raise MissionReportingValidationError("Mission Reporting validation failed: " + details)

        return result

    def _validate_mission_and_tasks(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        messages: list[MissionReportingValidationMessage],
    ) -> None:
        if task_set.mission_id != mission.mission_id:
            messages.append(
                self._error(
                    "mission-id-mismatch",
                    "Task Set mission ID does not match Mission Plan.",
                    "task_set.mission_id",
                )
            )

        if task_set.mission_fingerprint != mission.mission_fingerprint:
            messages.append(
                self._error(
                    "mission-fingerprint-mismatch",
                    "Task Set mission fingerprint does not match Mission Plan.",
                    "task_set.mission_fingerprint",
                )
            )

        if not task_set.tasks:
            messages.append(
                self._error(
                    "empty-task-set",
                    "Mission Reporting requires at least one task.",
                    "task_set.tasks",
                )
            )

    def _validate_assessment(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        messages: list[MissionReportingValidationMessage],
    ) -> None:
        if assessment.mission_id != mission.mission_id:
            messages.append(
                self._error(
                    "assessment-mission-mismatch",
                    "Impact Assessment mission ID does not match Mission Plan.",
                    "assessment.mission_id",
                )
            )

        if assessment.task_set_fingerprint != task_set.task_set_fingerprint:
            messages.append(
                self._error(
                    "assessment-task-set-mismatch",
                    "Impact Assessment task-set fingerprint does not match Task Set.",
                    "assessment.task_set_fingerprint",
                )
            )

        task_ids = {task.task_id for task in task_set.tasks}
        assessment_task_ids = set(assessment.task_ids)

        if assessment_task_ids != task_ids:
            messages.append(
                self._lineage_message(
                    "assessment-task-lineage-mismatch",
                    "Impact Assessment task IDs do not exactly match the Task Set.",
                    "assessment.task_ids",
                )
            )

    def _validate_engineering_memory(
        self,
        mission: MissionPlan,
        assessment: ImpactAssessment,
        engineering_memory: EngineeringMemoryStore,
        messages: list[MissionReportingValidationMessage],
    ) -> None:
        if engineering_memory.generation is None:
            messages.append(
                self._error(
                    "missing-memory-generation",
                    "Engineering Memory generation is required.",
                    "engineering_memory.generation",
                )
            )
            return

        records = tuple(engineering_memory.records.values())

        if not records:
            messages.append(
                self._error(
                    "empty-engineering-memory",
                    "Engineering Memory contains no active records.",
                    "engineering_memory.records",
                )
            )
            return

        if not any(mission.mission_id in record.mission_ids for record in records):
            messages.append(
                self._lineage_message(
                    "missing-mission-memory",
                    "Engineering Memory does not contain Mission lineage.",
                    "engineering_memory.records",
                )
            )

        if not any(assessment.assessment_id in record.assessment_ids for record in records):
            messages.append(
                self._lineage_message(
                    "missing-assessment-memory",
                    "Engineering Memory does not contain Impact Assessment lineage.",
                    "engineering_memory.records",
                )
            )

    def _lineage_message(
        self,
        code: str,
        message: str,
        field: str,
    ) -> MissionReportingValidationMessage:
        severity = (
            MissionReportingValidationSeverity.ERROR
            if self.configuration.strict
            else MissionReportingValidationSeverity.WARNING
        )

        return MissionReportingValidationMessage(
            severity=severity,
            code=code,
            message=message,
            field=field,
        )

    def _error(
        self,
        code: str,
        message: str,
        field: str,
    ) -> MissionReportingValidationMessage:
        return MissionReportingValidationMessage(
            severity=MissionReportingValidationSeverity.ERROR,
            code=code,
            message=message,
            field=field,
        )
