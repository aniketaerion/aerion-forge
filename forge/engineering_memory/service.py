"""Engineering Memory orchestration service."""

from pathlib import Path

from forge.engineering_memory.builder import (
    EngineeringMemoryBuilder,
)
from forge.engineering_memory.errors import (
    EngineeringMemoryDisabledError,
    EngineeringMemoryError,
    EngineeringMemoryReportError,
)
from forge.engineering_memory.identifiers import (
    build_generation_id,
    build_store_fingerprint,
)
from forge.engineering_memory.models import (
    EngineeringMemoryConfiguration,
    EngineeringMemoryGeneration,
    EngineeringMemoryResult,
    EngineeringMemoryStatistics,
    MemoryRecord,
    MemoryRetentionPolicy,
)
from forge.engineering_memory.renderer import (
    EngineeringMemoryRenderer,
)
from forge.engineering_memory.store import (
    EngineeringMemoryRepository,
)
from forge.impact.models import ImpactAssessment
from forge.planning.models import MissionPlan
from forge.tasks.models import TaskSet


class EngineeringMemoryService:
    """Build, persist, report and roll back Engineering Memory."""

    STORE_NAME = "engineering-memory.json"

    def __init__(
        self,
        memory_path: Path,
        reports_path: Path,
        configuration: (EngineeringMemoryConfiguration | None) = None,
        *,
        builder: EngineeringMemoryBuilder | None = None,
        repository: EngineeringMemoryRepository | None = None,
        renderer: EngineeringMemoryRenderer | None = None,
    ) -> None:
        self.configuration = (
            configuration if configuration is not None else EngineeringMemoryConfiguration()
        )
        self.memory_path = memory_path
        self.reports_path = reports_path
        self.builder = (
            builder if builder is not None else EngineeringMemoryBuilder(self.configuration)
        )
        self.repository = (
            repository
            if repository is not None
            else EngineeringMemoryRepository(
                memory_path / self.STORE_NAME,
                history_limit=(self.configuration.history_limit),
            )
        )
        self.renderer = renderer if renderer is not None else EngineeringMemoryRenderer()

    def build(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        *,
        persist: bool = True,
        write_reports: bool = True,
    ) -> EngineeringMemoryResult:
        """Build Engineering Memory transactionally."""

        if not self.configuration.enabled:
            raise EngineeringMemoryDisabledError("Engineering Memory capability is disabled.")

        records = self.builder.build(
            mission,
            task_set,
            assessment,
        )
        statistics = self._statistics(records)
        generation = self._generation(records)

        store_snapshot = self.repository.snapshot_bytes() if persist else None
        report_snapshots = (
            self._snapshot_reports(self.renderer.REPORT_NAMES) if write_reports else {}
        )

        report_paths: tuple[str, ...] = ()

        try:
            if persist:
                self.repository.save(
                    records,
                    generation,
                )

            if write_reports:
                reports = self.renderer.render(
                    records,
                    generation,
                    statistics,
                )
                report_paths = self.renderer.write(
                    self.reports_path,
                    reports,
                )

        except Exception as exc:
            rollback_errors: list[str] = []

            if persist:
                try:
                    self.repository.restore_bytes(store_snapshot)
                except EngineeringMemoryError as rollback_exc:
                    rollback_errors.append(f"store rollback failed: {rollback_exc}")

            if write_reports:
                try:
                    self._restore_reports(report_snapshots)
                except EngineeringMemoryReportError as rollback_exc:
                    rollback_errors.append(f"report rollback failed: {rollback_exc}")

            if rollback_errors:
                raise EngineeringMemoryError(
                    "Engineering Memory operation failed "
                    "and rollback was incomplete: " + "; ".join(rollback_errors)
                ) from exc

            raise

        return EngineeringMemoryResult(
            records=records,
            generation=generation,
            statistics=statistics,
            report_paths=report_paths,
        )

    def _generation(
        self,
        records: tuple[MemoryRecord, ...],
    ) -> EngineeringMemoryGeneration:
        active = {record.memory_id: record for record in records}
        store_fingerprint = build_store_fingerprint(active)

        previous_generation_id: str | None = None
        previous = self.repository.load().generation

        if previous is not None:
            previous_generation_id = previous.generation_id

        return EngineeringMemoryGeneration(
            generation_id=build_generation_id(
                store_fingerprint=store_fingerprint,
                previous_generation_id=(previous_generation_id),
            ),
            previous_generation_id=(previous_generation_id),
            store_fingerprint=store_fingerprint,
            record_count=len(records),
            relationship_count=sum(len(record.relationships) for record in records),
            evidence_count=sum(len(record.evidence) for record in records),
        )

    def _statistics(
        self,
        records: tuple[MemoryRecord, ...],
    ) -> EngineeringMemoryStatistics:
        return EngineeringMemoryStatistics(
            record_count=len(records),
            relationship_count=sum(len(record.relationships) for record in records),
            evidence_count=sum(len(record.evidence) for record in records),
            mission_count=len(
                {mission_id for record in records for mission_id in record.mission_ids}
            ),
            task_count=len({task_id for record in records for task_id in record.task_ids}),
            assessment_count=len(
                {assessment_id for record in records for assessment_id in record.assessment_ids}
            ),
            capability_count=len(
                {capability_id for record in records for capability_id in record.capability_ids}
            ),
            permanent_record_count=sum(
                record.retention_policy is MemoryRetentionPolicy.PERMANENT for record in records
            ),
        )

    def _snapshot_reports(
        self,
        report_names: tuple[str, ...],
    ) -> dict[str, bytes | None]:
        snapshots: dict[str, bytes | None] = {}

        for name in report_names:
            path = self.reports_path / name

            try:
                snapshots[name] = path.read_bytes() if path.exists() else None
            except OSError as exc:
                raise EngineeringMemoryReportError(
                    f"Unable to snapshot Engineering Memory report: {name}"
                ) from exc

        return snapshots

    def _restore_reports(
        self,
        snapshots: dict[str, bytes | None],
    ) -> None:
        self.reports_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        for name, content in snapshots.items():
            path = self.reports_path / name

            try:
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
            except OSError as exc:
                raise EngineeringMemoryReportError(
                    f"Unable to restore Engineering Memory report: {name}"
                ) from exc

        try:
            if self.reports_path.exists() and not any(self.reports_path.iterdir()):
                self.reports_path.rmdir()
        except OSError:
            pass
