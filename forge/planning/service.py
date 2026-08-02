"""Mission-planning orchestration without target execution."""

from pathlib import Path

from forge.planning.context import load_context
from forge.planning.errors import (
    MissionPlanningDisabledError,
    MissionValidationError,
)
from forge.planning.models import (
    MissionChangeType,
    MissionPlan,
    MissionPlanChange,
    MissionPlanChangeSet,
    MissionPlanGeneration,
    MissionPlanningConfiguration,
    MissionPlanResult,
)
from forge.planning.normalizer import normalize_request
from forge.planning.planner import build_plan
from forge.planning.renderer import MissionRenderer
from forge.planning.store import MissionPlanRepository
from forge.planning.validator import validate_plan


class MissionPlanningService:
    """Create, validate, persist and report mission plans."""

    def __init__(
        self,
        memory_path: Path,
        reports_path: Path,
        configuration: MissionPlanningConfiguration | None = None,
        renderer: MissionRenderer | None = None,
    ) -> None:
        self.memory_path = memory_path
        self.reports_path = reports_path
        self.configuration = (
            configuration
            if configuration is not None
            else MissionPlanningConfiguration()
        )
        self.repository = MissionPlanRepository(
            memory_path / "missions.json",
            history_limit=self.configuration.history_limit,
        )
        self.renderer = (
            renderer
            if renderer is not None
            else MissionRenderer()
        )

    def plan(
        self,
        raw_request: str,
        target: str | None = None,
        *,
        strict: bool = False,
        persist: bool = True,
        cwd: Path | None = None,
    ) -> MissionPlanResult:
        if not self.configuration.enabled:
            raise MissionPlanningDisabledError(
                "Mission planning is disabled."
            )

        active_configuration = self.configuration.model_copy(
            update={
                "strict": (
                    strict
                    or self.configuration.strict
                ),
                "require_current_graph": (
                    strict
                    or self.configuration.require_current_graph
                ),
            }
        )

        request = normalize_request(raw_request)

        context = load_context(
            self.memory_path,
            target,
            cwd or Path.cwd(),
        )

        plan = build_plan(
            request,
            context,
            active_configuration,
        )

        validation = validate_plan(plan)

        if not validation.valid:
            detail = "; ".join(
                message.message
                for message in validation.messages
            )
            raise MissionValidationError(detail)

        previous = self._previous_plan(
            plan,
            persist=persist,
        )
        changes = self._changes(
            plan,
            previous,
        )
        generation = self._generation(
            plan,
            previous,
        )

        report_paths: tuple[str, ...] = ()

        if persist:
            reports = self.renderer.render(
                plan,
                changes,
            )

            store_snapshot = self.repository.snapshot_bytes()
            report_snapshot = self._snapshot_reports(
                tuple(reports)
            )

            try:
                self.repository.save(plan)
                report_paths = self.renderer.write(
                    self.reports_path,
                    reports,
                )
            except Exception:
                self.repository.restore_bytes(
                    store_snapshot
                )
                self._restore_reports(
                    report_snapshot
                )
                raise

        return MissionPlanResult(
            plan=plan,
            generation=generation,
            changes=changes,
            report_paths=report_paths,
        )

    def _previous_plan(
        self,
        plan: MissionPlan,
        *,
        persist: bool,
    ) -> MissionPlan | None:
        if not persist:
            return None

        store = self.repository.load()
        previous = store.missions.get(plan.mission_id)

        return (
            previous.model_copy(deep=True)
            if previous is not None
            else None
        )

    def _changes(
        self,
        plan: MissionPlan,
        previous: MissionPlan | None,
    ) -> MissionPlanChangeSet:
        if previous is None:
            change_type = MissionChangeType.CREATED
        elif (
            previous.mission_fingerprint
            == plan.mission_fingerprint
        ):
            change_type = MissionChangeType.UNCHANGED
        else:
            change_type = MissionChangeType.UPDATED

        return MissionPlanChangeSet(
            mission_id=plan.mission_id,
            changes=(
                MissionPlanChange(
                    field="mission",
                    change_type=change_type,
                ),
            ),
        )

    def _generation(
        self,
        plan: MissionPlan,
        previous: MissionPlan | None,
    ) -> MissionPlanGeneration:
        previous_generation_id = None

        if (
            previous is not None
            and previous.mission_fingerprint
            != plan.mission_fingerprint
        ):
            previous_generation_id = (
                "mission-plan-"
                f"{previous.mission_fingerprint[:20]}"
            )

        fingerprints = plan.source_fingerprints

        return MissionPlanGeneration(
            generation_id=(
                "mission-plan-"
                f"{plan.mission_fingerprint[:20]}"
            ),
            previous_generation_id=previous_generation_id,
            mission_id=plan.mission_id,
            mission_fingerprint=plan.mission_fingerprint,
            target_identity=plan.target_identity,
            workspace_identity=plan.workspace_identity,
            discovery_identity=fingerprints.get(
                "discovery",
                "missing",
            ),
            index_fingerprint=fingerprints.get(
                "index",
                "missing",
            ),
            graph_fingerprint=fingerprints.get(
                "graph",
                "missing",
            ),
            configuration_fingerprint=fingerprints.get(
                "configuration",
                "missing",
            ),
            capability_fingerprint=fingerprints.get(
                "capabilities",
                "missing",
            ),
            diagnostic_fingerprint=fingerprints.get(
                "diagnostics",
                "missing",
            ),
            mission_status=plan.status,
            planning_confidence=plan.planning_confidence,
            risk_level=plan.risk_level,
            affected_area_count=(
                plan.statistics.affected_area_count
            ),
            workstream_count=(
                plan.statistics.workstream_count
            ),
            assumption_count=(
                plan.statistics.assumption_count
            ),
            question_count=(
                plan.statistics.question_count
            ),
            blocking_prerequisite_count=(
                plan.statistics.blocking_prerequisite_count
            ),
        )

    def _snapshot_reports(
        self,
        report_names: tuple[str, ...],
    ) -> dict[str, bytes | None]:
        snapshots: dict[str, bytes | None] = {}

        for name in report_names:
            path = self.reports_path / name
            snapshots[name] = (
                path.read_bytes()
                if path.exists()
                else None
            )

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

            if content is None:
                path.unlink(missing_ok=True)
                continue

            temporary = path.with_suffix(
                path.suffix + ".rollback"
            )
            temporary.write_bytes(content)
            temporary.replace(path)
