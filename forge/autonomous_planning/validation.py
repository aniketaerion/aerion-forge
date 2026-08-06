"""Validation rules for generated autonomous plans."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.cycle_detection import find_cycle
from forge.autonomous_planning.graph_builder import PlanningGraphBuilder
from forge.autonomous_planning.identifiers import (
    deterministic_identifier,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningValidationFinding,
    PlanningValidationResult,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    PlanningRisk,
    StepKind,
)


@dataclass(frozen=True, slots=True)
class AutonomousPlanValidator:
    """Validate plan safety, completeness, and graph integrity."""

    policy: AutonomousPlanningPolicy

    def validate(
        self,
        plan: PlanningPlan,
    ) -> PlanningValidationResult:
        findings: list[PlanningValidationFinding] = []

        if len(plan.steps) > self.policy.limits.maximum_steps:
            findings.append(
                self._finding(
                    code="MAXIMUM_STEPS_EXCEEDED",
                    message="Plan exceeds the configured step limit.",
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )

        if (
            len(plan.dependencies)
            > self.policy.limits.maximum_dependencies
        ):
            findings.append(
                self._finding(
                    code="MAXIMUM_DEPENDENCIES_EXCEEDED",
                    message=(
                        "Plan exceeds the configured dependency limit."
                    ),
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )

        names = [step.name for step in plan.steps]

        if (
            self.policy.quality.require_unique_step_names
            and len(names) != len(set(names))
        ):
            findings.append(
                self._finding(
                    code="DUPLICATE_STEP_NAMES",
                    message="Planning step names must be unique.",
                    severity=PlanningRisk.MEDIUM,
                    blocking=True,
                )
            )

        if (
            self.policy.safety.require_validation_step
            and not any(
                step.kind is StepKind.VALIDATION
                for step in plan.steps
            )
        ):
            findings.append(
                self._finding(
                    code="VALIDATION_STEP_MISSING",
                    message=(
                        "Plan requires at least one validation step."
                    ),
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )

        for step in plan.steps:
            if (
                len(step.description)
                < self.policy.quality.minimum_step_description_length
            ):
                findings.append(
                    self._finding(
                        code="STEP_DESCRIPTION_TOO_SHORT",
                        message=(
                            "Planning step description is too short."
                        ),
                        severity=PlanningRisk.MEDIUM,
                        blocking=True,
                        step_id=step.step_id,
                    )
                )

            if (
                step.destructive
                and not self.policy.safety.allow_destructive_steps
            ):
                findings.append(
                    self._finding(
                        code="DESTRUCTIVE_STEP_FORBIDDEN",
                        message=(
                            "Destructive planning steps are forbidden "
                            "by policy."
                        ),
                        severity=PlanningRisk.CRITICAL,
                        blocking=True,
                        step_id=step.step_id,
                    )
                )

            if (
                step.risk
                in {PlanningRisk.HIGH, PlanningRisk.CRITICAL}
                and self.policy.safety.require_approval_for_high_risk
                and step.approval_requirement
                is ApprovalRequirement.NONE
            ):
                findings.append(
                    self._finding(
                        code="HIGH_RISK_APPROVAL_MISSING",
                        message=(
                            "High-risk planning step requires approval."
                        ),
                        severity=PlanningRisk.HIGH,
                        blocking=True,
                        step_id=step.step_id,
                    )
                )

        try:
            graph_result = PlanningGraphBuilder(
                policy=self.policy
            ).build(plan)
            cycle = find_cycle(graph_result.graph)
        except Exception as exc:
            findings.append(
                self._finding(
                    code="GRAPH_BUILD_FAILED",
                    message=str(exc),
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )
        else:
            if cycle is not None:
                findings.append(
                    self._finding(
                        code="DEPENDENCY_CYCLE",
                        message=(
                            "Planning graph contains cycle: "
                            + " -> ".join(cycle)
                        ),
                        severity=PlanningRisk.HIGH,
                        blocking=True,
                    )
                )

        ordered = tuple(
            sorted(
                findings,
                key=lambda item: (
                    not item.blocking,
                    item.severity.value,
                    item.code,
                    item.step_id or "",
                ),
            )
        )
        valid = not any(
            finding.blocking
            for finding in ordered
        )

        return PlanningValidationResult(
            plan_id=plan.plan_id,
            valid=valid,
            findings=ordered,
        )

    @staticmethod
    def _finding(
        *,
        code: str,
        message: str,
        severity: PlanningRisk,
        blocking: bool,
        step_id: str | None = None,
    ) -> PlanningValidationFinding:
        payload = {
            "code": code,
            "message": message,
            "severity": severity.value,
            "blocking": blocking,
            "step_id": step_id,
        }
        return PlanningValidationFinding(
            finding_id=deterministic_identifier(
                "planning-finding",
                payload,
            ),
            severity=severity,
            code=code,
            message=message,
            step_id=step_id,
            blocking=blocking,
        )