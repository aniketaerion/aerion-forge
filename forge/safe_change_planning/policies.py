"""Safe Change Planning risk and approval policies."""

from collections import Counter
from collections.abc import Sequence

from forge.safe_change_planning.errors import (
    ChangePlanningRiskError,
)
from forge.safe_change_planning.identifiers import (
    risk_assessment_id,
    risk_factor_id,
)
from forge.safe_change_planning.models import (
    ChangeAction,
    ChangePlanningConfiguration,
    ChangeRiskAssessment,
    ChangeTarget,
    ChangeTargetType,
    DependencyImpact,
    DependencyType,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
)

RISK_WEIGHTS: dict[RiskFactorType, int] = {
    RiskFactorType.FILE_COUNT: 10,
    RiskFactorType.MODULE_COUNT: 10,
    RiskFactorType.DEPENDENCY_DEPTH: 15,
    RiskFactorType.PUBLIC_API: 25,
    RiskFactorType.DATABASE_SCHEMA: 35,
    RiskFactorType.DATA_MIGRATION: 40,
    RiskFactorType.AUTHENTICATION: 45,
    RiskFactorType.AUTHORIZATION: 45,
    RiskFactorType.FINANCIAL: 50,
    RiskFactorType.INFRASTRUCTURE: 35,
    RiskFactorType.DEPLOYMENT: 35,
    RiskFactorType.EXTERNAL_INTEGRATION: 30,
    RiskFactorType.CONFIGURATION: 20,
    RiskFactorType.TEST_COVERAGE_GAP: 30,
    RiskFactorType.MISSING_ROLLBACK: 40,
    RiskFactorType.MISSING_LINEAGE: 50,
    RiskFactorType.UNKNOWN_DEPENDENCY: 35,
    RiskFactorType.CONCURRENCY: 35,
    RiskFactorType.SECURITY: 50,
    RiskFactorType.COMPLIANCE: 50,
}


CRITICAL_FACTORS: frozenset[RiskFactorType] = frozenset(
    {
        RiskFactorType.DATA_MIGRATION,
        RiskFactorType.AUTHENTICATION,
        RiskFactorType.AUTHORIZATION,
        RiskFactorType.FINANCIAL,
        RiskFactorType.SECURITY,
        RiskFactorType.COMPLIANCE,
    }
)


HIGH_RISK_TARGET_TYPES: frozenset[ChangeTargetType] = frozenset(
    {
        ChangeTargetType.DATABASE,
        ChangeTargetType.INFRASTRUCTURE,
        ChangeTargetType.API,
    }
)


def risk_level_for_score(
    score: int,
) -> RiskLevel:
    """Map a normalized score to a deterministic risk level."""

    if score < 0 or score > 100:
        raise ChangePlanningRiskError("Risk score must be between 0 and 100.")

    if score >= 85:
        return RiskLevel.CRITICAL

    if score >= 60:
        return RiskLevel.HIGH

    if score >= 30:
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


def approval_required(
    risk_level: RiskLevel,
    configuration: ChangePlanningConfiguration,
) -> bool:
    """Resolve approval requirements from risk and configuration."""

    if risk_level in {
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }:
        return True

    return configuration.low_risk_approval_required


def unknown_dependency_present(
    dependencies: Sequence[DependencyImpact],
) -> bool:
    return any(
        not dependency.known or dependency.dependency_type is DependencyType.UNKNOWN
        for dependency in dependencies
    )


def maximum_dependency_depth(
    dependencies: Sequence[DependencyImpact],
) -> int:
    if not dependencies:
        return 0

    return max(dependency.depth for dependency in dependencies)


def high_risk_target_present(
    targets: Sequence[ChangeTarget],
) -> bool:
    return any(target.target_type in HIGH_RISK_TARGET_TYPES for target in targets)


def destructive_action_present(
    actions: Sequence[ChangeAction],
) -> bool:
    return any(action.destructive for action in actions)


def mutating_action_count(
    actions: Sequence[ChangeAction],
) -> int:
    return sum(action.mutating for action in actions)


def requires_rollback(
    risk_level: RiskLevel,
    actions: Sequence[ChangeAction],
    configuration: ChangePlanningConfiguration,
) -> bool:
    if destructive_action_present(actions):
        return True

    return configuration.require_rollback_for_high_risk and risk_level in {
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }


def requires_verification(
    actions: Sequence[ChangeAction],
    configuration: ChangePlanningConfiguration,
) -> bool:
    return configuration.require_verification_for_mutations and mutating_action_count(actions) > 0


def build_file_count_factor(
    targets: Sequence[ChangeTarget],
) -> RiskFactor | None:
    file_count = sum(target.target_type is ChangeTargetType.FILE for target in targets)

    if file_count <= 1:
        return None

    score = min(
        30,
        5 + ((file_count - 1) * 3),
    )

    return RiskFactor(
        factor_id=risk_factor_id(
            factor_type=RiskFactorType.FILE_COUNT.value,
            reason=f"{file_count} files are affected.",
            source_ids=tuple(
                target.target_id
                for target in targets
                if target.target_type is ChangeTargetType.FILE
            ),
        ),
        factor_type=RiskFactorType.FILE_COUNT,
        score=score,
        reason=f"{file_count} files are affected.",
        source_ids=tuple(
            target.target_id for target in targets if target.target_type is ChangeTargetType.FILE
        ),
        mitigation=("Split the change into smaller independently verifiable increments."),
    )


def build_module_count_factor(
    targets: Sequence[ChangeTarget],
) -> RiskFactor | None:
    components = {target.component for target in targets}

    if len(components) <= 1:
        return None

    score = min(
        30,
        5 + ((len(components) - 1) * 5),
    )

    reason = f"{len(components)} components are affected."

    return RiskFactor(
        factor_id=risk_factor_id(
            factor_type=RiskFactorType.MODULE_COUNT.value,
            reason=reason,
            source_ids=tuple(target.target_id for target in targets),
        ),
        factor_type=RiskFactorType.MODULE_COUNT,
        score=score,
        reason=reason,
        source_ids=tuple(target.target_id for target in targets),
        mitigation=("Define component boundaries and sequence changes by dependency order."),
    )


def build_dependency_depth_factor(
    dependencies: Sequence[DependencyImpact],
) -> RiskFactor | None:
    depth = maximum_dependency_depth(dependencies)

    if depth <= 1:
        return None

    score = min(
        40,
        10 + ((depth - 1) * 5),
    )

    reason = f"Maximum dependency depth is {depth}."

    return RiskFactor(
        factor_id=risk_factor_id(
            factor_type=(RiskFactorType.DEPENDENCY_DEPTH.value),
            reason=reason,
            source_ids=tuple(dependency.dependency_id for dependency in dependencies),
        ),
        factor_type=RiskFactorType.DEPENDENCY_DEPTH,
        score=score,
        reason=reason,
        source_ids=tuple(dependency.dependency_id for dependency in dependencies),
        mitigation=("Verify dependencies in order and isolate high-coupling changes."),
    )


def build_unknown_dependency_factor(
    dependencies: Sequence[DependencyImpact],
) -> RiskFactor | None:
    unknown = tuple(
        dependency
        for dependency in dependencies
        if (not dependency.known or dependency.dependency_type is DependencyType.UNKNOWN)
    )

    if not unknown:
        return None

    reason = f"{len(unknown)} dependencies are unknown."

    return RiskFactor(
        factor_id=risk_factor_id(
            factor_type=(RiskFactorType.UNKNOWN_DEPENDENCY.value),
            reason=reason,
            source_ids=tuple(dependency.dependency_id for dependency in unknown),
        ),
        factor_type=RiskFactorType.UNKNOWN_DEPENDENCY,
        score=RISK_WEIGHTS[RiskFactorType.UNKNOWN_DEPENDENCY],
        reason=reason,
        source_ids=tuple(dependency.dependency_id for dependency in unknown),
        mitigation=("Resolve unknown dependencies before execution."),
    )


def build_target_type_factors(
    targets: Sequence[ChangeTarget],
) -> tuple[RiskFactor, ...]:
    mappings: dict[
        ChangeTargetType,
        tuple[RiskFactorType, str, str],
    ] = {
        ChangeTargetType.API: (
            RiskFactorType.PUBLIC_API,
            "Public API or contract changes are present.",
            "Version and contract-test all API changes.",
        ),
        ChangeTargetType.DATABASE: (
            RiskFactorType.DATABASE_SCHEMA,
            "Database schema changes are present.",
            "Use reversible migrations, backups, and dry runs.",
        ),
        ChangeTargetType.INFRASTRUCTURE: (
            RiskFactorType.INFRASTRUCTURE,
            "Infrastructure changes are present.",
            "Use staged rollout and infrastructure review.",
        ),
        ChangeTargetType.CONFIGURATION: (
            RiskFactorType.CONFIGURATION,
            "Runtime configuration changes are present.",
            "Validate defaults, environment overrides, and rollback.",
        ),
    }

    grouped: dict[
        ChangeTargetType,
        list[ChangeTarget],
    ] = {}

    for target in targets:
        grouped.setdefault(
            target.target_type,
            [],
        ).append(target)

    factors: list[RiskFactor] = []

    for target_type, group in sorted(
        grouped.items(),
        key=lambda item: item[0].value,
    ):
        mapping = mappings.get(target_type)

        if mapping is None:
            continue

        factor_type, reason, mitigation = mapping
        source_ids = tuple(target.target_id for target in group)

        factors.append(
            RiskFactor(
                factor_id=risk_factor_id(
                    factor_type=factor_type.value,
                    reason=reason,
                    source_ids=source_ids,
                ),
                factor_type=factor_type,
                score=RISK_WEIGHTS[factor_type],
                reason=reason,
                source_ids=source_ids,
                mitigation=mitigation,
            )
        )

    return tuple(factors)


def build_action_factors(
    actions: Sequence[ChangeAction],
) -> tuple[RiskFactor, ...]:
    factors: list[RiskFactor] = []

    destructive = tuple(action for action in actions if action.destructive)

    if destructive:
        reason = f"{len(destructive)} destructive actions are present."
        source_ids = tuple(action.action_id for action in destructive)

        factors.append(
            RiskFactor(
                factor_id=risk_factor_id(
                    factor_type=(RiskFactorType.MISSING_ROLLBACK.value),
                    reason=reason,
                    source_ids=source_ids,
                ),
                factor_type=(RiskFactorType.MISSING_ROLLBACK),
                score=RISK_WEIGHTS[RiskFactorType.MISSING_ROLLBACK],
                reason=reason,
                source_ids=source_ids,
                mitigation=(
                    "Provide tested rollback or compensation steps for every destructive action."
                ),
            )
        )

    action_types = Counter(action.action_type.value for action in actions)

    if action_types.get("migrate", 0):
        migration_actions = tuple(
            action for action in actions if action.action_type.value == "migrate"
        )
        reason = "Data migration actions are present."
        source_ids = tuple(action.action_id for action in migration_actions)

        factors.append(
            RiskFactor(
                factor_id=risk_factor_id(
                    factor_type=(RiskFactorType.DATA_MIGRATION.value),
                    reason=reason,
                    source_ids=source_ids,
                ),
                factor_type=RiskFactorType.DATA_MIGRATION,
                score=RISK_WEIGHTS[RiskFactorType.DATA_MIGRATION],
                reason=reason,
                source_ids=source_ids,
                mitigation=("Require backups, migration dry runs, and explicit rollback strategy."),
            )
        )

    return tuple(factors)


def aggregate_risk_score(
    factors: Sequence[RiskFactor],
) -> int:
    if not factors:
        return 0

    base = max(factor.score for factor in factors)
    additional = sum(factor.score for factor in factors if factor.score != base) // 4

    return min(
        100,
        base + additional,
    )


def resolve_risk_level(
    factors: Sequence[RiskFactor],
) -> RiskLevel:
    factor_types = {factor.factor_type for factor in factors}

    critical_count = len(factor_types & CRITICAL_FACTORS)

    score = aggregate_risk_score(factors)

    if critical_count >= 2:
        return RiskLevel.CRITICAL

    return risk_level_for_score(score)


def build_risk_assessment(
    *,
    request_id: str,
    targets: Sequence[ChangeTarget],
    actions: Sequence[ChangeAction],
    dependencies: Sequence[DependencyImpact],
    configuration: ChangePlanningConfiguration,
) -> ChangeRiskAssessment:
    """Build a deterministic risk assessment from planning scope."""

    factors: list[RiskFactor] = []

    for factor in (
        build_file_count_factor(targets),
        build_module_count_factor(targets),
        build_dependency_depth_factor(dependencies),
        build_unknown_dependency_factor(dependencies),
    ):
        if factor is not None:
            factors.append(factor)

    factors.extend(build_target_type_factors(targets))
    factors.extend(build_action_factors(actions))

    ordered = tuple(
        sorted(
            factors,
            key=lambda factor: (
                factor.factor_type.value,
                factor.factor_id,
            ),
        )
    )

    score = aggregate_risk_score(ordered)
    level = resolve_risk_level(ordered)

    mitigations = tuple(
        sorted({factor.mitigation for factor in ordered if factor.mitigation is not None})
    )

    return ChangeRiskAssessment(
        assessment_id=risk_assessment_id(
            request_id=request_id,
            factors=ordered,
        ),
        risk_level=level,
        score=score,
        factors=ordered,
        approval_required=approval_required(
            level,
            configuration,
        ),
        mitigations=mitigations,
    )


def enforce_unknown_dependency_policy(
    dependencies: Sequence[DependencyImpact],
    configuration: ChangePlanningConfiguration,
) -> None:
    if unknown_dependency_present(dependencies) and not configuration.allow_unknown_dependencies:
        raise ChangePlanningRiskError("Unknown dependencies are not allowed by configuration.")


def enforce_risk_controls(
    assessment: ChangeRiskAssessment,
    actions: Sequence[ChangeAction],
    *,
    rollback_count: int,
    verification_count: int,
    configuration: ChangePlanningConfiguration,
) -> None:
    if (
        requires_verification(
            actions,
            configuration,
        )
        and verification_count == 0
    ):
        raise ChangePlanningRiskError("Mutating actions require verification steps.")

    if (
        requires_rollback(
            assessment.risk_level,
            actions,
            configuration,
        )
        and rollback_count == 0
    ):
        raise ChangePlanningRiskError("The assessed risk requires rollback steps.")

    if (
        assessment.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        and not assessment.approval_required
    ):
        raise ChangePlanningRiskError("High and critical risks require approval.")
