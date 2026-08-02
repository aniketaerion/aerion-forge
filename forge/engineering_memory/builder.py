"""Deterministic Engineering Memory construction."""

from forge.engineering_memory.errors import (
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.identifiers import (
    build_evidence_id,
    build_memory_fingerprint,
    build_memory_id,
    build_relationship_id,
)
from forge.engineering_memory.models import (
    EngineeringMemoryConfiguration,
    MemoryConfidence,
    MemoryEvidence,
    MemoryEvidenceType,
    MemoryRecord,
    MemoryRelationship,
    MemoryRelationshipType,
    MemoryRetentionPolicy,
    MemoryType,
)
from forge.engineering_memory.policies import normalize_tags
from forge.engineering_memory.validator import (
    EngineeringMemoryValidator,
)
from forge.impact.models import ImpactAssessment
from forge.planning.models import MissionPlan
from forge.tasks.models import TaskSet


class EngineeringMemoryBuilder:
    """Build verified memory records from persisted Forge artifacts."""

    def __init__(
        self,
        configuration: EngineeringMemoryConfiguration | None = None,
    ) -> None:
        self.configuration = (
            configuration if configuration is not None else EngineeringMemoryConfiguration()
        )
        self.validator = EngineeringMemoryValidator(self.configuration)

    def build(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
    ) -> tuple[MemoryRecord, ...]:
        """Build the canonical memory lineage for one mission."""

        self._validate_inputs(
            mission,
            task_set,
            assessment,
        )

        mission_memory_id = build_memory_id(
            memory_type=MemoryType.MISSION,
            title=mission.objective.statement,
            source_fingerprints={
                "mission": mission.mission_fingerprint,
            },
        )

        task_memory_id = build_memory_id(
            memory_type=MemoryType.TASK,
            title=(f"Task Set for {mission.objective.statement}"),
            source_fingerprints={
                "mission": mission.mission_fingerprint,
                "task_set": task_set.task_set_fingerprint,
            },
        )

        decision_memory_id = build_memory_id(
            memory_type=MemoryType.DECISION,
            title=(f"Impact Decision for {mission.objective.statement}"),
            source_fingerprints={
                "mission": mission.mission_fingerprint,
                "task_set": task_set.task_set_fingerprint,
                "assessment": (assessment.assessment_fingerprint),
            },
        )

        mission_record = self._mission_record(
            mission,
            memory_id=mission_memory_id,
        )

        task_record = self._task_record(
            mission,
            task_set,
            memory_id=task_memory_id,
            mission_memory_id=mission_memory_id,
        )

        decision_record = self._decision_record(
            mission,
            task_set,
            assessment,
            memory_id=decision_memory_id,
            task_memory_id=task_memory_id,
        )

        records = tuple(
            sorted(
                (
                    mission_record,
                    task_record,
                    decision_record,
                ),
                key=lambda record: record.memory_id,
            )
        )

        for record in records:
            self.validator.validate_record_or_raise(record)

        return records

    def _validate_inputs(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
    ) -> None:
        if mission.mission_id != task_set.mission_id:
            raise EngineeringMemoryValidationError("Mission ID does not match the Task Set.")

        if mission.mission_fingerprint != task_set.mission_fingerprint:
            raise EngineeringMemoryValidationError(
                "Mission fingerprint does not match the Task Set."
            )

        if mission.mission_id != assessment.mission_id:
            raise EngineeringMemoryValidationError(
                "Mission ID does not match the Impact Assessment."
            )

        if task_set.task_set_fingerprint != assessment.task_set_fingerprint:
            raise EngineeringMemoryValidationError(
                "Task Set fingerprint does not match the Impact Assessment."
            )

        task_ids = tuple(sorted(task.task_id for task in task_set.tasks))

        if task_ids != tuple(sorted(assessment.task_ids)):
            raise EngineeringMemoryValidationError(
                "Impact Assessment task IDs do not match the persisted Task Set."
            )

        if not task_set.tasks:
            raise EngineeringMemoryValidationError("Engineering Memory requires at least one task.")

    def _mission_record(
        self,
        mission: MissionPlan,
        *,
        memory_id: str,
    ) -> MemoryRecord:
        evidence = MemoryEvidence(
            evidence_id=build_evidence_id(
                evidence_type=MemoryEvidenceType.MISSION_PLAN,
                reference="memory/missions.json",
                fingerprint=mission.mission_fingerprint,
            ),
            evidence_type=MemoryEvidenceType.MISSION_PLAN,
            reference="memory/missions.json",
            fingerprint=mission.mission_fingerprint,
            description=("Persisted Mission Plan used as verified evidence."),
        )

        draft = MemoryRecord(
            memory_id=memory_id,
            memory_fingerprint="0" * 64,
            memory_type=MemoryType.MISSION,
            title=mission.objective.statement,
            summary=(f"Verified Engineering Memory for persisted mission {mission.mission_id}."),
            rationale=("Created directly from the deterministic Mission Planning artifact."),
            mission_ids=(mission.mission_id,),
            capability_ids=("mission-planning",),
            milestones=("2.1",),
            source_artifacts=("memory/missions.json",),
            evidence=(evidence,),
            tags=normalize_tags(
                (
                    "mission",
                    "phase 2",
                    "engineering intelligence",
                )
            ),
            confidence=MemoryConfidence.VERIFIED,
            retention_policy=(MemoryRetentionPolicy.PROJECT_LIFETIME),
            created_from_fingerprints={
                "mission": mission.mission_fingerprint,
            },
        )

        return self._finalize(draft)

    def _task_record(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        *,
        memory_id: str,
        mission_memory_id: str,
    ) -> MemoryRecord:
        evidence = MemoryEvidence(
            evidence_id=build_evidence_id(
                evidence_type=MemoryEvidenceType.TASK_SET,
                reference="memory/tasks.json",
                fingerprint=task_set.task_set_fingerprint,
            ),
            evidence_type=MemoryEvidenceType.TASK_SET,
            reference="memory/tasks.json",
            fingerprint=task_set.task_set_fingerprint,
            description=("Persisted Task Set used as verified evidence."),
        )

        relationship = MemoryRelationship(
            relationship_id=build_relationship_id(
                relationship_type=(MemoryRelationshipType.DERIVED_FROM),
                source_memory_id=memory_id,
                target_memory_id=mission_memory_id,
                rationale=("The Task Set was deterministically derived from the Mission Plan."),
            ),
            relationship_type=(MemoryRelationshipType.DERIVED_FROM),
            source_memory_id=memory_id,
            target_memory_id=mission_memory_id,
            rationale=("The Task Set was deterministically derived from the Mission Plan."),
        )

        draft = MemoryRecord(
            memory_id=memory_id,
            memory_fingerprint="0" * 64,
            memory_type=MemoryType.TASK,
            title=(f"Task Set for {mission.objective.statement}"),
            summary=(f"Verified Task Set containing {len(task_set.tasks)} engineering tasks."),
            rationale=("Created from the persisted deterministic Task Management artifact."),
            mission_ids=(mission.mission_id,),
            task_ids=tuple(task.task_id for task in task_set.tasks),
            capability_ids=("task-management",),
            milestones=("2.2",),
            source_artifacts=("memory/tasks.json",),
            evidence=(evidence,),
            relationships=(relationship,),
            tags=normalize_tags(
                (
                    "tasks",
                    "phase 2",
                    "engineering intelligence",
                )
            ),
            confidence=MemoryConfidence.VERIFIED,
            retention_policy=(MemoryRetentionPolicy.PROJECT_LIFETIME),
            created_from_fingerprints={
                "mission": mission.mission_fingerprint,
                "task_set": task_set.task_set_fingerprint,
            },
        )

        return self._finalize(draft)

    def _decision_record(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        *,
        memory_id: str,
        task_memory_id: str,
    ) -> MemoryRecord:
        evidence = MemoryEvidence(
            evidence_id=build_evidence_id(
                evidence_type=(MemoryEvidenceType.IMPACT_ASSESSMENT),
                reference="memory/impact-decisions.json",
                fingerprint=(assessment.assessment_fingerprint),
            ),
            evidence_type=(MemoryEvidenceType.IMPACT_ASSESSMENT),
            reference="memory/impact-decisions.json",
            fingerprint=assessment.assessment_fingerprint,
            description=("Persisted Impact Assessment used as verified decision evidence."),
        )

        relationship = MemoryRelationship(
            relationship_id=build_relationship_id(
                relationship_type=(MemoryRelationshipType.DERIVED_FROM),
                source_memory_id=memory_id,
                target_memory_id=task_memory_id,
                rationale=("The Impact Decision was derived from the persisted Task Set."),
            ),
            relationship_type=(MemoryRelationshipType.DERIVED_FROM),
            source_memory_id=memory_id,
            target_memory_id=task_memory_id,
            rationale=("The Impact Decision was derived from the persisted Task Set."),
        )

        draft = MemoryRecord(
            memory_id=memory_id,
            memory_fingerprint="0" * 64,
            memory_type=MemoryType.DECISION,
            title=(f"Impact Decision for {mission.objective.statement}"),
            summary=(
                "Impact decision status "
                f"{assessment.status.value} with "
                f"{assessment.overall_severity.value} severity."
            ),
            rationale=assessment.recommendation.rationale,
            mission_ids=(mission.mission_id,),
            task_ids=tuple(task.task_id for task in task_set.tasks),
            assessment_ids=(assessment.assessment_id,),
            capability_ids=("impact-decision-engine",),
            milestones=("2.3",),
            source_artifacts=("memory/impact-decisions.json",),
            evidence=(evidence,),
            relationships=(relationship,),
            tags=normalize_tags(
                (
                    "impact decision",
                    assessment.status.value,
                    assessment.overall_severity.value,
                    "phase 2",
                )
            ),
            confidence=MemoryConfidence.VERIFIED,
            retention_policy=MemoryRetentionPolicy.PERMANENT,
            created_from_fingerprints={
                "mission": mission.mission_fingerprint,
                "task_set": task_set.task_set_fingerprint,
                "assessment": (assessment.assessment_fingerprint),
            },
        )

        return self._finalize(draft)

    def _finalize(
        self,
        draft: MemoryRecord,
    ) -> MemoryRecord:
        return draft.model_copy(update={"memory_fingerprint": (build_memory_fingerprint(draft))})
