"""Impact Decision orchestration service."""

from pathlib import Path

from forge.impact.builder import ImpactAssessmentBuilder
from forge.impact.errors import (
    ImpactDecisionDisabledError,
    ImpactDecisionError,
    ImpactReportError,
)
from forge.impact.identifiers import build_generation_id
from forge.impact.models import (
    ImpactAssessment,
    ImpactDecisionConfiguration,
    ImpactDecisionGeneration,
    ImpactDecisionResult,
)
from forge.impact.renderer import ImpactRenderer
from forge.impact.store import ImpactRepository
from forge.planning.models import MissionPlan
from forge.tasks.models import TaskSet


class ImpactDecisionService:
    """Build, persist, report, and roll back impact decisions."""

    STORE_NAME = "impact-decisions.json"

    def __init__(
        self,
        memory_path: Path,
        reports_path: Path,
        configuration: ImpactDecisionConfiguration | None = None,
        *,
        builder: ImpactAssessmentBuilder | None = None,
        repository: ImpactRepository | None = None,
        renderer: ImpactRenderer | None = None,
    ) -> None:
        self.configuration = (
            configuration if configuration is not None else ImpactDecisionConfiguration()
        )
        self.memory_path = memory_path
        self.reports_path = reports_path
        self.builder = (
            builder if builder is not None else ImpactAssessmentBuilder(self.configuration)
        )
        self.repository = (
            repository
            if repository is not None
            else ImpactRepository(
                memory_path / self.STORE_NAME,
                history_limit=self.configuration.history_limit,
            )
        )
        self.renderer = renderer if renderer is not None else ImpactRenderer()

    def assess(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        *,
        persist: bool = True,
        write_reports: bool = True,
    ) -> ImpactDecisionResult:
        """Build one impact assessment transactionally."""

        if not self.configuration.enabled:
            raise ImpactDecisionDisabledError("Impact Decision capability is disabled.")

        assessment = self.builder.build(
            mission,
            task_set,
        )
        generation = self._generation(assessment)

        store_snapshot = self.repository.snapshot_bytes() if persist else None
        report_snapshots = (
            self._snapshot_reports(self.renderer.REPORT_NAMES) if write_reports else {}
        )

        report_paths: tuple[str, ...] = ()

        try:
            if persist:
                self.repository.save(
                    assessment,
                    generation,
                )

            if write_reports:
                reports = self.renderer.render(
                    assessment,
                    generation,
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
                except ImpactDecisionError as rollback_exc:
                    rollback_errors.append(f"store rollback failed: {rollback_exc}")

            if write_reports:
                try:
                    self._restore_reports(report_snapshots)
                except ImpactReportError as rollback_exc:
                    rollback_errors.append(f"report rollback failed: {rollback_exc}")

            if rollback_errors:
                raise ImpactDecisionError(
                    "Impact Decision operation failed and rollback "
                    "was incomplete: " + "; ".join(rollback_errors)
                ) from exc

            raise

        return ImpactDecisionResult(
            assessment=assessment,
            generation=generation,
            report_paths=report_paths,
        )

    def _generation(
        self,
        assessment: ImpactAssessment,
    ) -> ImpactDecisionGeneration:
        previous_generation_id: str | None = None

        store = self.repository.load()
        previous = store.generations.get(assessment.assessment_id)

        if previous is not None:
            previous_generation_id = previous.generation_id

        generation_id = build_generation_id(
            assessment_id=assessment.assessment_id,
            assessment_fingerprint=(assessment.assessment_fingerprint),
            previous_generation_id=previous_generation_id,
        )

        return ImpactDecisionGeneration(
            generation_id=generation_id,
            previous_generation_id=previous_generation_id,
            assessment_id=assessment.assessment_id,
            assessment_fingerprint=(assessment.assessment_fingerprint),
            mission_id=assessment.mission_id,
            task_set_fingerprint=(assessment.task_set_fingerprint),
            finding_count=len(assessment.findings),
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
                raise ImpactReportError(f"Unable to snapshot impact report: {name}") from exc

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
                raise ImpactReportError(f"Unable to restore impact report: {name}") from exc

        try:
            if self.reports_path.exists() and not any(self.reports_path.iterdir()):
                self.reports_path.rmdir()
        except OSError:
            pass
