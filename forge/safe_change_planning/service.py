"""Safe Change Planning orchestration and persistence service."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from forge.safe_change_planning.builder import (
    SafeChangePlanningBuilder,
)
from forge.safe_change_planning.errors import (
    ChangePlanningPersistenceError,
    ChangePlanningValidationError,
    ChangePlanNotFoundError,
)
from forge.safe_change_planning.models import (
    ChangeAction,
    ChangePhase,
    ChangePlanningConfiguration,
    ChangeRequest,
    ChangeTarget,
    DependencyImpact,
    PlanningValidationResult,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
)
from forge.safe_change_planning.renderer import (
    SafeChangePlanningRenderer,
)
from forge.safe_change_planning.validator import (
    SafeChangePlanningValidator,
)

SAFE_CHANGE_MEMORY_FILE = "safe-change-plan.json"
SAFE_CHANGE_REQUEST_FILE = "safe-change-request.json"


class SafeChangePlanningService:
    """Coordinate safe planning without mutating target repositories."""

    def __init__(
        self,
        configuration: (ChangePlanningConfiguration | None) = None,
        *,
        builder: SafeChangePlanningBuilder | None = None,
        validator: (SafeChangePlanningValidator | None) = None,
        renderer: SafeChangePlanningRenderer | None = None,
    ) -> None:
        self.configuration = configuration or ChangePlanningConfiguration()
        self.builder = builder or SafeChangePlanningBuilder()
        self.validator = validator or SafeChangePlanningValidator()
        self.renderer = renderer or SafeChangePlanningRenderer()

    def create_request(
        self,
        *,
        mission_id: str,
        task_ids: Sequence[str],
        objective: str,
        constraints: Sequence[str] = (),
        requested_outcomes: Sequence[str] = (),
        source_fingerprints: (Mapping[str, str] | None) = None,
    ) -> ChangeRequest:
        """Create one deterministic planning request."""

        self.validator.ensure_enabled(self.configuration)

        return self.builder.build_request(
            mission_id=mission_id,
            task_ids=task_ids,
            objective=objective,
            constraints=constraints,
            requested_outcomes=requested_outcomes,
            source_fingerprints=source_fingerprints,
        )

    def validate_request(
        self,
        request: ChangeRequest,
        *,
        known_mission_id: str,
        known_task_ids: Sequence[str],
        required_source_fingerprints: Mapping[str, str],
    ) -> PlanningValidationResult:
        """Validate request scope and source lineage."""

        return self.validator.validate_request(
            request,
            self.configuration,
            known_mission_id=known_mission_id,
            known_task_ids=known_task_ids,
            required_source_fingerprints=(required_source_fingerprints),
        )

    def validate_request_or_raise(
        self,
        request: ChangeRequest,
        *,
        known_mission_id: str,
        known_task_ids: Sequence[str],
        required_source_fingerprints: Mapping[str, str],
    ) -> PlanningValidationResult:
        """Validate a request and raise on unsafe input."""

        return self.validator.validate_request_or_raise(
            request,
            self.configuration,
            known_mission_id=known_mission_id,
            known_task_ids=known_task_ids,
            required_source_fingerprints=(required_source_fingerprints),
        )

    def create_plan(
        self,
        *,
        request: ChangeRequest,
        targets: Sequence[ChangeTarget],
        actions: Sequence[ChangeAction],
        dependencies: Sequence[DependencyImpact] = (),
        verification_steps: Sequence[VerificationStep] = (),
        rollback_steps: Sequence[RollbackStep] = (),
        phases: Sequence[ChangePhase] = (),
        source_fingerprints: Mapping[str, str],
    ) -> SafeChangePlan:
        """Build and validate one deterministic plan."""

        self.validator.ensure_enabled(self.configuration)

        plan = self.builder.build_plan(
            request=request,
            targets=targets,
            actions=actions,
            dependencies=dependencies,
            verification_steps=verification_steps,
            rollback_steps=rollback_steps,
            phases=phases,
            source_fingerprints=source_fingerprints,
            configuration=self.configuration,
        )

        self.validator.validate_plan_or_raise(
            plan,
            self.configuration,
        )

        return plan

    def validate_plan(
        self,
        plan: SafeChangePlan,
    ) -> PlanningValidationResult:
        """Validate a completed Safe Change Plan."""

        return self.validator.validate_plan(
            plan,
            self.configuration,
        )

    def validate_plan_or_raise(
        self,
        plan: SafeChangePlan,
    ) -> PlanningValidationResult:
        """Validate a plan and raise on unsafe content."""

        return self.validator.validate_plan_or_raise(
            plan,
            self.configuration,
        )

    def render_reports(
        self,
        plan: SafeChangePlan,
    ) -> Mapping[str, str]:
        """Validate and render all planning reports."""

        self.validate_plan_or_raise(plan)

        return self.renderer.render_suite(plan)

    def write_reports(
        self,
        plan: SafeChangePlan,
        reports_path: Path,
    ) -> tuple[str, ...]:
        """Validate and atomically write report artifacts."""

        self.validate_plan_or_raise(plan)

        return self.renderer.write_suite(
            plan,
            reports_path,
        )

    def save_request(
        self,
        request: ChangeRequest,
        memory_path: Path,
    ) -> Path:
        """Atomically persist a planning request."""

        destination = memory_path / SAFE_CHANGE_REQUEST_FILE

        payload = (
            json.dumps(
                request.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )

        self._atomic_write(
            destination,
            payload,
        )

        return destination

    def load_request(
        self,
        memory_path: Path,
    ) -> ChangeRequest:
        """Load one persisted planning request."""

        path = memory_path / SAFE_CHANGE_REQUEST_FILE

        if not path.exists():
            raise ChangePlanNotFoundError(f"Safe Change Planning request does not exist: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return ChangeRequest.model_validate(payload)
        except (
            OSError,
            json.JSONDecodeError,
            ValidationError,
            TypeError,
        ) as exc:
            raise ChangePlanningPersistenceError(
                f"Safe Change Planning request is corrupted or unreadable: {path}"
            ) from exc

    def save_plan(
        self,
        plan: SafeChangePlan,
        memory_path: Path,
    ) -> Path:
        """Validate and atomically persist a plan."""

        self.validate_plan_or_raise(plan)

        destination = memory_path / SAFE_CHANGE_MEMORY_FILE

        payload = (
            json.dumps(
                plan.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )

        self._atomic_write(
            destination,
            payload,
        )

        return destination

    def load_plan(
        self,
        memory_path: Path,
    ) -> SafeChangePlan:
        """Load and validate the persisted plan."""

        path = memory_path / SAFE_CHANGE_MEMORY_FILE

        if not path.exists():
            raise ChangePlanNotFoundError(f"Safe Change Plan does not exist: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            plan = SafeChangePlan.model_validate(payload)
        except (
            OSError,
            json.JSONDecodeError,
            ValidationError,
            TypeError,
        ) as exc:
            raise ChangePlanningPersistenceError(
                f"Safe Change Plan is corrupted or unreadable: {path}"
            ) from exc

        try:
            self.validate_plan_or_raise(plan)
        except ChangePlanningValidationError as exc:
            raise ChangePlanningPersistenceError(
                "Persisted Safe Change Plan failed validation."
            ) from exc

        return plan

    def build_persist_and_report(
        self,
        *,
        request: ChangeRequest,
        targets: Sequence[ChangeTarget],
        actions: Sequence[ChangeAction],
        dependencies: Sequence[DependencyImpact],
        verification_steps: Sequence[VerificationStep],
        rollback_steps: Sequence[RollbackStep],
        phases: Sequence[ChangePhase],
        source_fingerprints: Mapping[str, str],
        memory_path: Path,
        reports_path: Path,
    ) -> SafeChangePlan:
        """Build, persist, and report a validated plan."""

        plan = self.create_plan(
            request=request,
            targets=targets,
            actions=actions,
            dependencies=dependencies,
            verification_steps=verification_steps,
            rollback_steps=rollback_steps,
            phases=phases,
            source_fingerprints=source_fingerprints,
        )

        self.save_request(
            request,
            memory_path,
        )
        self.save_plan(
            plan,
            memory_path,
        )
        self.write_reports(
            plan,
            reports_path,
        )

        return plan

    def _atomic_write(
        self,
        destination: Path,
        content: str,
    ) -> None:
        temporary = destination.with_name(f"{destination.name}.tmp")

        try:
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary.write_text(
                content,
                encoding="utf-8",
                newline="\n",
            )

            temporary.replace(destination)

        except OSError as exc:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass

            raise ChangePlanningPersistenceError(
                f"Could not atomically persist Safe Change Planning artifact: {destination}"
            ) from exc
