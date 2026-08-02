"""Safe Change Planning validation services."""

from collections.abc import Iterable, Mapping, Sequence

from forge.safe_change_planning.errors import (
    ChangePlanningConfigurationError,
    ChangePlanningValidationError,
)
from forge.safe_change_planning.models import (
    ChangePlanningConfiguration,
    ChangeRequest,
    DependencyImpact,
    FindingSeverity,
    PlanningValidationFinding,
    PlanningValidationResult,
    RiskLevel,
    SafeChangePlan,
)
from forge.safe_change_planning.policies import (
    enforce_risk_controls,
    enforce_unknown_dependency_policy,
)


class SafeChangePlanningValidator:
    """Validate Safe Change Planning inputs and plans."""

    def validate_configuration(
        self,
        configuration: ChangePlanningConfiguration,
    ) -> PlanningValidationResult:
        findings: list[PlanningValidationFinding] = []

        if not configuration.enabled:
            findings.append(
                self._error(
                    "planning-disabled",
                    "Safe Change Planning is disabled.",
                )
            )

        if configuration.max_actions < configuration.max_targets:
            findings.append(
                self._warning(
                    "action-limit-below-target-limit",
                    ("The maximum action count is lower than the maximum target count."),
                )
            )

        return self._result(findings)

    def validate_request(
        self,
        request: ChangeRequest,
        configuration: ChangePlanningConfiguration,
        *,
        known_mission_id: str,
        known_task_ids: Sequence[str],
        required_source_fingerprints: Mapping[str, str],
    ) -> PlanningValidationResult:
        findings: list[PlanningValidationFinding] = []

        configuration_result = self.validate_configuration(configuration)
        findings.extend(configuration_result.findings)

        if request.mission_id != known_mission_id:
            findings.append(
                self._error(
                    "mission-id-mismatch",
                    ("The change request mission ID does not match the known Mission Plan."),
                    source_ids=(request.mission_id,),
                )
            )

        known_tasks = {task_id.strip() for task_id in known_task_ids if task_id.strip()}
        requested_tasks = set(request.task_ids)

        if not requested_tasks:
            findings.append(
                self._error(
                    "empty-task-scope",
                    ("The change request must reference at least one engineering task."),
                )
            )

        unknown_tasks = requested_tasks - known_tasks

        if unknown_tasks:
            severity = (
                FindingSeverity.ERROR
                if configuration.strict_validation
                else FindingSeverity.WARNING
            )

            findings.append(
                PlanningValidationFinding(
                    code="unknown-task-ids",
                    message=("The change request references unknown task identifiers."),
                    severity=severity,
                    source_ids=tuple(sorted(unknown_tasks)),
                )
            )

        if not request.objective.strip():
            findings.append(
                self._error(
                    "empty-objective",
                    "The change objective cannot be blank.",
                )
            )

        for key, expected in sorted(required_source_fingerprints.items()):
            actual = request.source_fingerprints.get(key)

            if actual is None:
                severity = (
                    FindingSeverity.ERROR
                    if configuration.strict_validation
                    else FindingSeverity.WARNING
                )

                findings.append(
                    PlanningValidationFinding(
                        code="missing-source-fingerprint",
                        message=(f"Required source fingerprint '{key}' is missing."),
                        severity=severity,
                        source_ids=(key,),
                    )
                )
                continue

            if actual != expected:
                findings.append(
                    self._error(
                        "source-fingerprint-mismatch",
                        (f"Source fingerprint '{key}' does not match the expected artifact."),
                        source_ids=(key,),
                    )
                )

        return self._result(findings)

    def validate_plan(
        self,
        plan: SafeChangePlan,
        configuration: ChangePlanningConfiguration,
    ) -> PlanningValidationResult:
        findings: list[PlanningValidationFinding] = []

        configuration_result = self.validate_configuration(configuration)
        findings.extend(configuration_result.findings)

        if len(plan.targets) > configuration.max_targets:
            findings.append(
                self._error(
                    "target-limit-exceeded",
                    ("The Safe Change Plan exceeds the configured maximum target count."),
                )
            )

        if len(plan.actions) > configuration.max_actions:
            findings.append(
                self._error(
                    "action-limit-exceeded",
                    ("The Safe Change Plan exceeds the configured maximum action count."),
                )
            )

        findings.extend(
            self._validate_dependencies(
                plan.dependencies,
                configuration,
            )
        )
        findings.extend(self._validate_target_references(plan))
        findings.extend(self._validate_action_dependencies(plan))
        findings.extend(
            self._validate_verification_coverage(
                plan,
                configuration,
            )
        )
        findings.extend(
            self._validate_rollback_coverage(
                plan,
                configuration,
            )
        )
        findings.extend(self._validate_phase_sequence(plan))
        findings.extend(
            self._validate_risk_controls(
                plan,
                configuration,
            )
        )
        findings.extend(
            self._validate_lineage(
                plan,
                configuration,
            )
        )

        return self._result(findings)

    def validate_request_or_raise(
        self,
        request: ChangeRequest,
        configuration: ChangePlanningConfiguration,
        *,
        known_mission_id: str,
        known_task_ids: Sequence[str],
        required_source_fingerprints: Mapping[str, str],
    ) -> PlanningValidationResult:
        result = self.validate_request(
            request,
            configuration,
            known_mission_id=known_mission_id,
            known_task_ids=known_task_ids,
            required_source_fingerprints=(required_source_fingerprints),
        )

        return self.validate_or_raise(result)

    def validate_plan_or_raise(
        self,
        plan: SafeChangePlan,
        configuration: ChangePlanningConfiguration,
    ) -> PlanningValidationResult:
        result = self.validate_plan(
            plan,
            configuration,
        )

        return self.validate_or_raise(result)

    def validate_or_raise(
        self,
        result: PlanningValidationResult,
    ) -> PlanningValidationResult:
        if not result.valid:
            messages = "; ".join(finding.message for finding in result.findings if finding.is_error)

            raise ChangePlanningValidationError(
                messages or "Safe Change Planning validation failed."
            )

        return result

    def ensure_enabled(
        self,
        configuration: ChangePlanningConfiguration,
    ) -> None:
        if not configuration.enabled:
            raise ChangePlanningConfigurationError("Safe Change Planning is disabled.")

    def _validate_dependencies(
        self,
        dependencies: Sequence[DependencyImpact],
        configuration: ChangePlanningConfiguration,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        duplicate_ids = self._duplicates(dependency.dependency_id for dependency in dependencies)

        if duplicate_ids:
            findings.append(
                self._error(
                    "duplicate-dependency-ids",
                    ("The plan contains duplicate dependency identifiers."),
                    source_ids=duplicate_ids,
                )
            )

        excessive_depth = tuple(
            dependency.dependency_id
            for dependency in dependencies
            if (dependency.depth > configuration.max_dependency_depth)
        )

        if excessive_depth:
            findings.append(
                self._error(
                    "dependency-depth-exceeded",
                    ("One or more dependencies exceed the configured maximum depth."),
                    source_ids=excessive_depth,
                )
            )

        unknown = tuple(
            dependency.dependency_id for dependency in dependencies if not dependency.known
        )

        if unknown:
            severity = (
                FindingSeverity.WARNING
                if configuration.allow_unknown_dependencies
                else FindingSeverity.ERROR
            )

            findings.append(
                PlanningValidationFinding(
                    code="unknown-dependencies",
                    message=("The plan contains unresolved dependencies."),
                    severity=severity,
                    source_ids=unknown,
                )
            )

        return tuple(findings)

    def _validate_target_references(
        self,
        plan: SafeChangePlan,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        target_ids = {target.target_id for target in plan.targets}

        duplicate_target_ids = self._duplicates(target.target_id for target in plan.targets)

        if duplicate_target_ids:
            findings.append(
                self._error(
                    "duplicate-target-ids",
                    "The plan contains duplicate target identifiers.",
                    source_ids=duplicate_target_ids,
                )
            )

        unknown_action_targets = tuple(
            action.action_id for action in plan.actions if action.target_id not in target_ids
        )

        if unknown_action_targets:
            findings.append(
                self._error(
                    "unknown-action-target",
                    ("One or more actions reference an unknown change target."),
                    source_ids=unknown_action_targets,
                )
            )

        unknown_dependency_targets = tuple(
            dependency.dependency_id
            for dependency in plan.dependencies
            if (
                dependency.source_target_id not in target_ids
                or dependency.affected_target_id not in target_ids
            )
        )

        if unknown_dependency_targets:
            findings.append(
                self._error(
                    "unknown-dependency-target",
                    ("One or more dependencies reference an unknown change target."),
                    source_ids=unknown_dependency_targets,
                )
            )

        return tuple(findings)

    def _validate_action_dependencies(
        self,
        plan: SafeChangePlan,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        action_ids = {action.action_id for action in plan.actions}

        duplicate_action_ids = self._duplicates(action.action_id for action in plan.actions)

        if duplicate_action_ids:
            findings.append(
                self._error(
                    "duplicate-action-ids",
                    "The plan contains duplicate action identifiers.",
                    source_ids=duplicate_action_ids,
                )
            )

        unknown_prerequisites = tuple(
            action.action_id
            for action in plan.actions
            if not set(action.prerequisites).issubset(action_ids)
        )

        if unknown_prerequisites:
            findings.append(
                self._error(
                    "unknown-action-prerequisite",
                    ("One or more actions reference an unknown prerequisite action."),
                    source_ids=unknown_prerequisites,
                )
            )

        self_references = tuple(
            action.action_id for action in plan.actions if action.action_id in action.prerequisites
        )

        if self_references:
            findings.append(
                self._error(
                    "self-referencing-action",
                    ("An action cannot depend on itself."),
                    source_ids=self_references,
                )
            )

        return tuple(findings)

    def _validate_verification_coverage(
        self,
        plan: SafeChangePlan,
        configuration: ChangePlanningConfiguration,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        verification_ids = {step.step_id for step in plan.verification_steps}

        duplicate_ids = self._duplicates(step.step_id for step in plan.verification_steps)

        if duplicate_ids:
            findings.append(
                self._error(
                    "duplicate-verification-ids",
                    ("The plan contains duplicate verification step identifiers."),
                    source_ids=duplicate_ids,
                )
            )

        missing_verification = tuple(
            action.action_id
            for action in plan.actions
            if (
                action.mutating
                and configuration.require_verification_for_mutations
                and not action.verification_step_ids
            )
        )

        if missing_verification:
            findings.append(
                self._error(
                    "missing-action-verification",
                    ("Every mutating action requires at least one verification step."),
                    source_ids=missing_verification,
                )
            )

        unknown_steps = tuple(
            action.action_id
            for action in plan.actions
            if not set(action.verification_step_ids).issubset(verification_ids)
        )

        if unknown_steps:
            findings.append(
                self._error(
                    "unknown-verification-step",
                    ("One or more actions reference an unknown verification step."),
                    source_ids=unknown_steps,
                )
            )

        return tuple(findings)

    def _validate_rollback_coverage(
        self,
        plan: SafeChangePlan,
        configuration: ChangePlanningConfiguration,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        rollback_ids = {step.step_id for step in plan.rollback_steps}

        duplicate_ids = self._duplicates(step.step_id for step in plan.rollback_steps)

        if duplicate_ids:
            findings.append(
                self._error(
                    "duplicate-rollback-ids",
                    ("The plan contains duplicate rollback step identifiers."),
                    source_ids=duplicate_ids,
                )
            )

        missing_destructive_rollback = tuple(
            action.action_id
            for action in plan.actions
            if action.destructive and not action.rollback_step_ids
        )

        if missing_destructive_rollback:
            findings.append(
                self._error(
                    "missing-destructive-rollback",
                    ("Every destructive action requires a rollback or compensation step."),
                    source_ids=missing_destructive_rollback,
                )
            )

        unknown_steps = tuple(
            action.action_id
            for action in plan.actions
            if not set(action.rollback_step_ids).issubset(rollback_ids)
        )

        if unknown_steps:
            findings.append(
                self._error(
                    "unknown-rollback-step",
                    ("One or more actions reference an unknown rollback step."),
                    source_ids=unknown_steps,
                )
            )

        if (
            configuration.require_rollback_for_high_risk
            and plan.risk_assessment.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
            and not plan.rollback_steps
        ):
            findings.append(
                self._error(
                    "missing-high-risk-rollback",
                    ("High and critical risk plans require rollback steps."),
                )
            )

        return tuple(findings)

    def _validate_phase_sequence(
        self,
        plan: SafeChangePlan,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        sequences = tuple(phase.sequence for phase in plan.phases)

        if len(sequences) != len(set(sequences)):
            findings.append(
                self._error(
                    "duplicate-phase-sequence",
                    ("Change phases must use unique sequence numbers."),
                )
            )

        expected = tuple(range(1, len(plan.phases) + 1))

        if tuple(sorted(sequences)) != expected:
            findings.append(
                self._error(
                    "non-contiguous-phase-sequence",
                    ("Change phase sequence numbers must be contiguous and start at one."),
                )
            )

        action_ids = {action.action_id for action in plan.actions}

        unknown_phase_actions = tuple(
            phase.phase_id
            for phase in plan.phases
            if not set(phase.action_ids).issubset(action_ids)
        )

        if unknown_phase_actions:
            findings.append(
                self._error(
                    "unknown-phase-action",
                    ("One or more phases reference an unknown action."),
                    source_ids=unknown_phase_actions,
                )
            )

        return tuple(findings)

    def _validate_risk_controls(
        self,
        plan: SafeChangePlan,
        configuration: ChangePlanningConfiguration,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        try:
            enforce_unknown_dependency_policy(
                plan.dependencies,
                configuration,
            )
        except Exception as exc:
            findings.append(
                self._error(
                    "unknown-dependency-policy",
                    str(exc),
                )
            )

        try:
            enforce_risk_controls(
                plan.risk_assessment,
                plan.actions,
                rollback_count=len(plan.rollback_steps),
                verification_count=len(plan.verification_steps),
                configuration=configuration,
            )
        except Exception as exc:
            findings.append(
                self._error(
                    "risk-control-violation",
                    str(exc),
                )
            )

        return tuple(findings)

    def _validate_lineage(
        self,
        plan: SafeChangePlan,
        configuration: ChangePlanningConfiguration,
    ) -> tuple[PlanningValidationFinding, ...]:
        findings: list[PlanningValidationFinding] = []

        required_keys = {
            "mission",
            "tasks",
            "impact",
            "engineering_memory",
            "mission_report",
            "repository",
            "index",
            "knowledge_graph",
        }

        available_keys = set(plan.source_fingerprints)
        missing = tuple(sorted(required_keys - available_keys))

        if missing:
            severity = (
                FindingSeverity.ERROR
                if configuration.strict_validation
                else FindingSeverity.WARNING
            )

            findings.append(
                PlanningValidationFinding(
                    code="missing-plan-lineage",
                    message=("The Safe Change Plan is missing required source lineage."),
                    severity=severity,
                    source_ids=missing,
                )
            )

        if plan.request.mission_id.strip() == "":
            findings.append(
                self._error(
                    "missing-mission-lineage",
                    ("The Safe Change Plan request has no Mission ID."),
                )
            )

        return tuple(findings)

    def _result(
        self,
        findings: Sequence[PlanningValidationFinding],
    ) -> PlanningValidationResult:
        ordered = tuple(
            sorted(
                findings,
                key=lambda finding: (
                    finding.severity.value,
                    finding.code,
                    finding.message,
                    finding.source_ids,
                ),
            )
        )

        return PlanningValidationResult(
            valid=not any(finding.is_error for finding in ordered),
            findings=ordered,
        )

    def _error(
        self,
        code: str,
        message: str,
        *,
        source_ids: Sequence[str] = (),
    ) -> PlanningValidationFinding:
        return PlanningValidationFinding(
            code=code,
            message=message,
            severity=FindingSeverity.ERROR,
            source_ids=tuple(source_ids),
        )

    def _warning(
        self,
        code: str,
        message: str,
        *,
        source_ids: Sequence[str] = (),
    ) -> PlanningValidationFinding:
        return PlanningValidationFinding(
            code=code,
            message=message,
            severity=FindingSeverity.WARNING,
            source_ids=tuple(source_ids),
        )

    def _duplicates(
        self,
        values: Iterable[str],
    ) -> tuple[str, ...]:
        materialized: tuple[str, ...] = tuple(values)

        return tuple(sorted({value for value in materialized if materialized.count(value) > 1}))
