"""Mission Reporting orchestration service."""

from pathlib import Path

from forge.engineering_memory.models import EngineeringMemoryStore
from forge.impact.models import ImpactAssessment
from forge.mission_reporting.builder import MissionReportBuilder
from forge.mission_reporting.models import (
    MissionReportingConfiguration,
    MissionReportingResult,
)
from forge.mission_reporting.renderer import MissionReportRenderer
from forge.planning.models import MissionPlan
from forge.tasks.models import TaskSet


class MissionReportingService:
    """Build and optionally write deterministic Mission Reports."""

    def __init__(
        self,
        reports_path: Path,
        configuration: MissionReportingConfiguration | None = None,
        *,
        builder: MissionReportBuilder | None = None,
        renderer: MissionReportRenderer | None = None,
    ) -> None:
        self.configuration = (
            configuration if configuration is not None else MissionReportingConfiguration()
        )
        self.reports_path = reports_path
        self.builder = builder if builder is not None else MissionReportBuilder(self.configuration)
        self.renderer = renderer if renderer is not None else MissionReportRenderer()

    def build(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        engineering_memory: EngineeringMemoryStore,
        *,
        write_reports: bool = True,
    ) -> MissionReportingResult:
        """Build a Mission Report and optionally write report files."""

        report = self.builder.build(
            mission,
            task_set,
            assessment,
            engineering_memory,
        )

        report_paths: tuple[str, ...] = ()

        if write_reports:
            rendered = self.renderer.render(report)
            written = self.renderer.write(
                self.reports_path,
                rendered,
            )
            report_paths = tuple(str(path) for path in written)

        return MissionReportingResult(
            report=report,
            report_paths=report_paths,
        )
