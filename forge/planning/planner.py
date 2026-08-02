"""Deterministic, evidence-grounded mission-plan construction."""

import hashlib
import json
from typing import Any

from forge.planning.context import PlanningContext
from forge.planning.models import (
    SCHEMA_VERSION,
    MissionAcceptanceCriterion,
    MissionAffectedArea,
    MissionAffectedAreaType,
    MissionApprovalLevel,
    MissionApprovalRequirement,
    MissionAssumption,
    MissionConstraint,
    MissionContextReference,
    MissionDeliverable,
    MissionObjective,
    MissionPlan,
    MissionPlanningConfiguration,
    MissionPlanningStatus,
    MissionPlanStatistics,
    MissionPrerequisite,
    MissionPrerequisiteStatus,
    MissionQuestion,
    MissionRequestCategory,
    MissionRisk,
    MissionRiskLevel,
    MissionScopeItem,
    MissionScopeType,
    MissionValidationCategory,
    MissionValidationStrategy,
    MissionWorkstream,
    NormalizedEngineeringRequest,
    PlanningConfidence,
)
from forge.planning.policies import MILESTONE_EXCLUSIONS, POLICY_VERSION

_CRITICAL_PHRASES = (
    "credential redesign",
    "destructive migration",
    "flight control",
    "irreversible",
    "remove security control",
)

_HIGH_RISK_TERMS = {
    "api",
    "authentication",
    "authorization",
    "database",
    "financial",
    "firmware",
    "infrastructure",
    "migration",
    "schema",
    "security",
}

_LOW_RISK_CATEGORIES = {
    MissionRequestCategory.ANALYZE,
    MissionRequestCategory.DOCUMENT,
    MissionRequestCategory.INVESTIGATE,
}


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _item_id(prefix: str, value: str) -> str:
    return f"{prefix}-{_canonical_hash(value)[:12]}"


def _contains_phrase(
    request: NormalizedEngineeringRequest,
    phrases: tuple[str, ...],
) -> bool:
    text = request.normalized_request
    return any(phrase in text for phrase in phrases)


def _has_term(
    request: NormalizedEngineeringRequest,
    terms: set[str],
) -> bool:
    request_terms = set(request.terms)
    return bool(request_terms.intersection(terms))


def _classify_risk(
    request: NormalizedEngineeringRequest,
) -> MissionRiskLevel:
    if _contains_phrase(request, _CRITICAL_PHRASES):
        return MissionRiskLevel.CRITICAL

    if _has_term(request, _HIGH_RISK_TERMS):
        return MissionRiskLevel.HIGH

    if request.category in _LOW_RISK_CATEGORIES:
        return MissionRiskLevel.LOW

    if request.category is MissionRequestCategory.UNKNOWN:
        return MissionRiskLevel.UNKNOWN

    return MissionRiskLevel.MEDIUM


def _approval_requirements(
    request: NormalizedEngineeringRequest,
    risk: MissionRiskLevel,
) -> tuple[MissionApprovalRequirement, ...]:
    levels = {MissionApprovalLevel.REVIEW_REQUIRED}
    terms = set(request.terms)
    text = request.normalized_request

    if terms.intersection({"api", "contract"}) or "flight control" in text:
        levels.add(MissionApprovalLevel.ARCHITECTURE_APPROVAL)

    if terms.intersection(
        {
            "authentication",
            "authorization",
            "credential",
            "security",
        }
    ):
        levels.add(MissionApprovalLevel.SECURITY_APPROVAL)

    if terms.intersection({"database", "migration", "schema"}):
        levels.add(MissionApprovalLevel.DATA_MIGRATION_APPROVAL)

    if terms.intersection({"finance", "financial"}) or "flight control" in text:
        levels.add(MissionApprovalLevel.DOMAIN_OWNER_APPROVAL)

    if risk in {
        MissionRiskLevel.HIGH,
        MissionRiskLevel.CRITICAL,
    }:
        levels.add(MissionApprovalLevel.HIGH_RISK_APPROVAL)

    return tuple(
        MissionApprovalRequirement(
            approval_id=f"approval-{level.value}",
            level=level,
            reason=(
                f"{level.value.replace('_', ' ').title()} "
                "is required by planning policy."
            ),
        )
        for level in sorted(levels, key=lambda item: item.value)
    )


def _context_references(
    context: PlanningContext,
    terms: tuple[str, ...],
    maximum: int,
) -> tuple[MissionContextReference, ...]:
    candidates: list[tuple[str, str, str, str]] = []

    if context.discovery:
        for application in context.discovery.applications:
            candidates.append(
                (
                    f"application:{application.name}",
                    "application",
                    application.name,
                    (
                        "Persisted discovery application "
                        f"({application.kind})."
                    ),
                )
            )

        for library in context.discovery.libraries:
            candidates.append(
                (
                    f"library:{library}",
                    "library",
                    library,
                    "Persisted discovery library.",
                )
            )

        for service in context.discovery.microservices:
            candidates.append(
                (
                    f"service:{service}",
                    "service",
                    service,
                    "Persisted discovery service.",
                )
            )

        for entry in context.discovery.directory_structure:
            candidates.append(
                (
                    f"directory:{entry.path}",
                    "directory",
                    entry.path,
                    "Persisted discovery directory.",
                )
            )

    if context.graph:
        for node in context.graph.nodes:
            candidates.append(
                (
                    node.node_id,
                    node.node_type.value,
                    node.display_name,
                    "Persisted structural knowledge-graph entity.",
                )
            )

    matches: dict[str, MissionContextReference] = {}

    for entity_id, entity_type, name, evidence in candidates:
        haystack = (
            name.casefold()
            .replace("_", " ")
            .replace("-", " ")
        )

        if terms and any(term in haystack for term in terms):
            matches[entity_id] = MissionContextReference(
                entity_id=entity_id,
                entity_type=entity_type,
                canonical_name=name,
                relationship_to_request=(
                    "Term match; likely relevant structural context."
                ),
                evidence=evidence,
                confidence=PlanningConfidence.MEDIUM,
            )

    return tuple(
        matches[key]
        for key in sorted(matches)[:maximum]
    )


def _affected_areas(
    references: tuple[MissionContextReference, ...],
) -> tuple[MissionAffectedArea, ...]:
    supported_types = {
        item.value: item
        for item in MissionAffectedAreaType
    }

    return tuple(
        MissionAffectedArea(
            area_id=_item_id("area", reference.entity_id),
            area_type=supported_types.get(
                reference.entity_type,
                MissionAffectedAreaType.UNKNOWN,
            ),
            canonical_name=reference.canonical_name,
            evidence=reference.evidence,
            confidence=reference.confidence,
        )
        for reference in references
    )


def _prerequisite(
    *,
    prerequisite_id: str,
    description: str,
    satisfied: bool,
    blocking: bool,
    success_evidence: str,
    failure_evidence: str,
    corrective_action: str | None = None,
) -> MissionPrerequisite:
    return MissionPrerequisite(
        prerequisite_id=prerequisite_id,
        description=description,
        status=(
            MissionPrerequisiteStatus.SATISFIED
            if satisfied
            else MissionPrerequisiteStatus.UNSATISFIED
        ),
        blocking=blocking,
        evidence=(
            success_evidence
            if satisfied
            else failure_evidence
        ),
        corrective_action=(
            None
            if satisfied
            else corrective_action
        ),
    )


def _prerequisites(
    context: PlanningContext,
    configuration: MissionPlanningConfiguration,
) -> tuple[MissionPrerequisite, ...]:
    diagnostic_status = context.diagnostic_status

    if diagnostic_status == "healthy":
        diagnostic_prerequisite = MissionPrerequisite(
            prerequisite_id="runtime_healthy",
            description="Runtime diagnostics permit planning.",
            status=MissionPrerequisiteStatus.SATISFIED,
            blocking=True,
            evidence="Persisted diagnostic status: healthy.",
        )
    elif diagnostic_status in {"missing", "unknown"}:
        diagnostic_prerequisite = MissionPrerequisite(
            prerequisite_id="runtime_healthy",
            description="Runtime diagnostics permit planning.",
            status=MissionPrerequisiteStatus.UNKNOWN,
            blocking=configuration.strict,
            evidence=(
                f"Persisted diagnostic status: "
                f"{diagnostic_status}."
            ),
            corrective_action="Run forge health",
        )
    else:
        diagnostic_prerequisite = MissionPrerequisite(
            prerequisite_id="runtime_healthy",
            description="Runtime diagnostics permit planning.",
            status=MissionPrerequisiteStatus.UNSATISFIED,
            blocking=diagnostic_status == "unhealthy",
            evidence=(
                f"Persisted diagnostic status: "
                f"{diagnostic_status}."
            ),
            corrective_action="Run forge health",
        )

    values = (
        MissionPrerequisite(
            prerequisite_id="target_resolved",
            description=(
                "Target resolves to a workspace or repository."
            ),
            status=MissionPrerequisiteStatus.SATISFIED,
            blocking=True,
            evidence="Resolved without target traversal.",
        ),
        _prerequisite(
            prerequisite_id="discovery_present",
            description="Persisted discovery state is available.",
            satisfied=context.discovery is not None,
            blocking=True,
            success_evidence="Persisted discovery store.",
            failure_evidence="No matching discovery state.",
            corrective_action=(
                f"Run forge inspect {context.target_name}"
            ),
        ),
        _prerequisite(
            prerequisite_id="index_present",
            description="Persisted index state is available.",
            satisfied=context.project_index is not None,
            blocking=True,
            success_evidence="Persisted index store.",
            failure_evidence="No matching index state.",
            corrective_action=(
                f"Run forge index {context.target_name}"
            ),
        ),
        _prerequisite(
            prerequisite_id="knowledge_graph_current",
            description=(
                "Persisted knowledge graph matches "
                "the current project index."
            ),
            satisfied=context.graph_is_current,
            blocking=configuration.require_current_graph,
            success_evidence=(
                "Knowledge graph generation and index "
                "fingerprint match the current index."
            ),
            failure_evidence=(
                context.graph_staleness_reason
                or "Knowledge graph is unavailable."
            ),
            corrective_action=(
                f"Run forge graph {context.target_name}"
            ),
        ),
        diagnostic_prerequisite,
        _prerequisite(
            prerequisite_id="diagnostic_target_matches",
            description=(
                "Persisted target diagnostics belong "
                "to the selected target."
            ),
            satisfied=context.diagnostic_target_matches,
            blocking=configuration.strict,
            success_evidence=(
                "Diagnostic target identity matches "
                "the selected workspace or repository."
            ),
            failure_evidence=(
                "Only runtime diagnostics or diagnostics "
                "for another target are available."
            ),
            corrective_action=(
                f"Run forge diagnose {context.target_name}"
            ),
        ),
        _prerequisite(
            prerequisite_id="required_capabilities_available",
            description=(
                "Required Phase 1 capabilities are available."
            ),
            satisfied=not context.unavailable_capabilities,
            blocking=True,
            success_evidence=(
                "Persisted registry has no unavailable prerequisite."
            ),
            failure_evidence=(
                "Unavailable: "
                + ", ".join(context.unavailable_capabilities)
            ),
        ),
    )

    return tuple(
        sorted(
            values,
            key=lambda item: item.prerequisite_id,
        )
    )


def _readiness(
    request: NormalizedEngineeringRequest,
    context: PlanningContext,
    references: tuple[MissionContextReference, ...],
    prerequisites: tuple[MissionPrerequisite, ...],
    configuration: MissionPlanningConfiguration,
) -> tuple[
    MissionPlanningStatus,
    PlanningConfidence,
    int,
]:
    blocking = sum(
        prerequisite.blocking
        and prerequisite.status
        is not MissionPrerequisiteStatus.SATISFIED
        for prerequisite in prerequisites
    )

    if blocking:
        return (
            MissionPlanningStatus.BLOCKED,
            PlanningConfidence.INSUFFICIENT,
            blocking,
        )

    degraded_runtime = context.diagnostic_status != "healthy"

    conditional = (
        degraded_runtime
        or not references
        or request.ambiguity is not PlanningConfidence.HIGH
    )

    if degraded_runtime and not configuration.allow_degraded_runtime:
        return (
            MissionPlanningStatus.BLOCKED,
            PlanningConfidence.INSUFFICIENT,
            1,
        )

    if conditional:
        return (
            MissionPlanningStatus.READY_WITH_CONDITIONS,
            PlanningConfidence.MEDIUM,
            0,
        )

    return (
        MissionPlanningStatus.READY,
        PlanningConfidence.HIGH,
        0,
    )


def _scope(
    request: NormalizedEngineeringRequest,
) -> tuple[MissionScopeItem, ...]:
    excluded = tuple(
        MissionScopeItem(
            scope_id=_item_id("scope", statement),
            scope_type=MissionScopeType.OUT_OF_SCOPE,
            statement=statement,
        )
        for statement in MILESTONE_EXCLUSIONS
    )

    included = (
        MissionScopeItem(
            scope_id="scope-current-state",
            scope_type=MissionScopeType.IN_SCOPE,
            statement=(
                "Establish current-state evidence from persisted "
                "Phase 1 state."
            ),
        ),
        MissionScopeItem(
            scope_id="scope-outcomes",
            scope_type=MissionScopeType.IN_SCOPE,
            statement=(
                "Define the approved outcomes for "
                f"{request.primary_object or request.normalized_request}."
            ),
        ),
        MissionScopeItem(
            scope_id="scope-contracts",
            scope_type=MissionScopeType.CONDITIONAL,
            statement=(
                "Assess architecture and contract implications "
                "if supported by approved analysis."
            ),
        ),
        MissionScopeItem(
            scope_id="scope-unknown",
            scope_type=MissionScopeType.UNKNOWN,
            statement=(
                "Implementation detail is not established by "
                "persisted structural evidence."
            ),
        ),
    )

    return tuple(
        sorted(
            (*excluded, *included),
            key=lambda item: item.scope_id,
        )
    )


def _assumptions(
    context: PlanningContext,
    maximum: int,
) -> tuple[MissionAssumption, ...]:
    values = (
        MissionAssumption(
            assumption_id="assumption-target",
            statement=(
                f"{context.target_name} is the intended target."
            ),
            basis="Resolved target selection.",
            risk_if_incorrect=(
                "The mission would address the wrong product."
            ),
            requires_confirmation=True,
        ),
        MissionAssumption(
            assumption_id="assumption-baseline",
            statement=(
                "Persisted discovery, index and graph state "
                "represents the approved baseline."
            ),
            basis=(
                "Milestone 2.1 consumes persisted Phase 1 "
                "evidence only."
            ),
            risk_if_incorrect=(
                "Scope and affected areas may be incomplete."
            ),
            requires_confirmation=context.graph is None,
        ),
        MissionAssumption(
            assumption_id="assumption-architecture",
            statement=(
                "Current architecture remains authoritative "
                "unless an approved decision changes it."
            ),
            basis="Preserve-architecture policy.",
            risk_if_incorrect=(
                "Contract changes may require replanning."
            ),
            requires_confirmation=False,
        ),
    )

    return values[:maximum]


def _constraints() -> tuple[MissionConstraint, ...]:
    statements = (
        "Planning is read-only and performs no execution "
        "or target mutation.",
        "Use only persisted structural evidence; "
        "do not infer source semantics.",
        "Preserve existing architecture by default.",
        "High-risk change requires human approval.",
    )

    return tuple(
        MissionConstraint(
            constraint_id=f"constraint-{index}",
            statement=statement,
        )
        for index, statement in enumerate(
            statements,
            start=1,
        )
    )


def _workstreams(
    risk: MissionRiskLevel,
    approvals: tuple[MissionApprovalRequirement, ...],
    maximum: int,
) -> tuple[MissionWorkstream, ...]:
    specifications = (
        (
            "Current-State Assessment",
            (
                "Review persisted structural evidence and "
                "identify confirmed gaps."
            ),
            "current-state evidence summary",
            "Evidence and uncertainty are explicitly recorded.",
        ),
        (
            "Functional Gap Definition",
            (
                "Define the requested outcome and bounded "
                "functional scope."
            ),
            "approved functional scope",
            "Stakeholders approve the outcome boundary.",
        ),
        (
            "Architecture and Contract Review",
            (
                "Identify architecture, data and integration "
                "decisions requiring approval."
            ),
            "architecture impact statement",
            (
                "Required decisions and approvals "
                "are recorded."
            ),
        ),
        (
            "Validation Planning",
            (
                "Define proportionate verification "
                "and regression gates."
            ),
            "validation strategy",
            (
                "Validation gates cover functionality "
                "and regression safety."
            ),
        ),
        (
            "Documentation and Release Preparation",
            (
                "Define documentation and release-readiness "
                "evidence."
            ),
            "release-readiness criteria",
            (
                "Documentation and release criteria "
                "are approved."
            ),
        ),
    )

    approval_levels = tuple(
        approval.level
        for approval in approvals
    )

    values: list[MissionWorkstream] = []

    for index, specification in enumerate(
        specifications[:maximum],
        start=1,
    ):
        name, objective, output, criterion = specification

        values.append(
            MissionWorkstream(
                workstream_id=f"workstream-{index}",
                name=name,
                objective=objective,
                expected_outputs=(output,),
                dependencies=(
                    (f"workstream-{index - 1}",)
                    if index > 1
                    else ()
                ),
                risk_level=risk,
                required_approvals=approval_levels,
                completion_criteria=(criterion,),
            )
        )

    return tuple(values)


def _deliverables() -> tuple[MissionDeliverable, ...]:
    descriptions = (
        "Approved functional scope",
        "Current-state evidence summary",
        "Implementation-ready requirement baseline",
        "Architecture impact statement",
        "Validation strategy",
        "Documentation and release-readiness criteria",
    )

    return tuple(
        MissionDeliverable(
            deliverable_id=f"deliverable-{index}",
            description=description,
        )
        for index, description in enumerate(
            descriptions,
            start=1,
        )
    )


def _acceptance_criteria(
    request: NormalizedEngineeringRequest,
) -> tuple[MissionAcceptanceCriterion, ...]:
    subject = request.primary_object or "engineering work"
    normalized_subject = (
        subject[4:]
        if subject.casefold().startswith("the ")
        else subject
    )

    statements = (
        (
            f"The approved {normalized_subject} scope "
            "is completed and verifiable."
        ),
        (
            "Existing architecture and contracts remain "
            "compatible or have approved versioned changes."
        ),
        (
            "All required static, test, build and review "
            "validation gates pass."
        ),
        (
            "Architecture, user-facing and changelog "
            "documentation is updated."
        ),
        (
            "High-risk changes receive required approval "
            "before merge."
        ),
        (
            "Regression safety is demonstrated for likely "
            "related structural areas."
        ),
    )

    return tuple(
        MissionAcceptanceCriterion(
            criterion_id=f"criterion-{index}",
            statement=statement,
        )
        for index, statement in enumerate(
            statements,
            start=1,
        )
    )


def _validation_strategy(
    context: PlanningContext,
    risk: MissionRiskLevel,
) -> tuple[MissionValidationStrategy, ...]:
    strategies = [
        MissionValidationStrategy(
            strategy_id="validation-manual",
            category=MissionValidationCategory.MANUAL_REVIEW,
            description=(
                "Review scope, evidence, architecture "
                "and approvals."
            ),
        )
    ]

    if context.discovery and context.discovery.test_frameworks:
        strategies.append(
            MissionValidationStrategy(
                strategy_id="validation-unit",
                category=MissionValidationCategory.UNIT_TESTING,
                description=(
                    "Run the target's established unit-test "
                    "framework during future execution."
                ),
            )
        )

    if context.discovery and context.discovery.build_systems:
        strategies.append(
            MissionValidationStrategy(
                strategy_id="validation-build",
                category=MissionValidationCategory.BUILD_VALIDATION,
                description=(
                    "Run the established build validation "
                    "during future execution."
                ),
            )
        )

    if risk in {
        MissionRiskLevel.HIGH,
        MissionRiskLevel.CRITICAL,
    }:
        strategies.append(
            MissionValidationStrategy(
                strategy_id="validation-security",
                category=(
                    MissionValidationCategory.SECURITY_VALIDATION
                ),
                description=(
                    "Validate security and high-risk controls "
                    "before release."
                ),
            )
        )

    return tuple(
        sorted(
            strategies,
            key=lambda item: item.strategy_id,
        )
    )


def _questions(
    request: NormalizedEngineeringRequest,
    maximum: int,
) -> tuple[MissionQuestion, ...]:
    subject = request.primary_object or "capabilities"
    normalized_subject = (
        subject[4:]
        if subject.casefold().startswith("the ")
        else subject
    )

    values = (
        MissionQuestion(
            question_id="question-1",
            question=(
                "Which parts of "
                f"{normalized_subject} are currently incomplete?"
            ),
        ),
        MissionQuestion(
            question_id="question-2",
            question=(
                "Which persisted contracts define completion?"
            ),
        ),
        MissionQuestion(
            question_id="question-3",
            question=(
                "Must existing integrations remain "
                "backward compatible?"
            ),
        ),
        MissionQuestion(
            question_id="question-4",
            question="What rollout constraints apply?",
        ),
    )

    return values[:maximum]


def _source_fingerprints(
    context: PlanningContext,
) -> dict[str, str]:
    discovery_fingerprint = (
        _canonical_hash(
            context.discovery.model_dump(mode="json")
        )
        if context.discovery
        else "missing"
    )

    index_fingerprint = (
        context.project_index.generation.repository_state_fingerprint
        if context.project_index
        else "missing"
    )

    graph_fingerprint = (
        context.graph.generation.graph_state_fingerprint
        if context.graph
        else "missing"
    )

    return {
        "capabilities": context.capability_fingerprint,
        "configuration": context.configuration_fingerprint,
        "diagnostics": context.diagnostic_fingerprint,
        "discovery": discovery_fingerprint,
        "graph": graph_fingerprint,
        "index": index_fingerprint,
    }


def _mission_id(
    request: NormalizedEngineeringRequest,
    context: PlanningContext,
) -> str:
    identity = {
        "policy": POLICY_VERSION,
        "request": request.normalized_request,
        "schema": SCHEMA_VERSION,
        "target": context.target_identity,
        "workspace": context.workspace_identity,
    }
    return f"mission-{_canonical_hash(identity)[:20]}"


def _plan_fingerprint(plan: MissionPlan) -> str:
    payload = plan.model_dump(mode="json")
    payload["mission_fingerprint"] = ""
    return _canonical_hash(payload)


def build_plan(
    request: NormalizedEngineeringRequest,
    context: PlanningContext,
    configuration: MissionPlanningConfiguration,
) -> MissionPlan:
    risk = _classify_risk(request)

    references = _context_references(
        context,
        request.terms,
        configuration.max_affected_areas,
    )

    areas = _affected_areas(references)

    prerequisites = _prerequisites(
        context,
        configuration,
    )

    status, confidence, blocking_count = _readiness(
        request,
        context,
        references,
        prerequisites,
        configuration,
    )

    approvals = _approval_requirements(
        request,
        risk,
    )

    assumptions = _assumptions(
        context,
        configuration.max_assumptions,
    )

    workstreams = _workstreams(
        risk,
        approvals,
        configuration.max_workstreams,
    )

    questions = _questions(
        request,
        configuration.max_questions,
    )

    statistics = MissionPlanStatistics(
        affected_area_count=len(areas),
        workstream_count=len(workstreams),
        assumption_count=len(assumptions),
        question_count=len(questions),
        blocking_prerequisite_count=blocking_count,
    )

    plan = MissionPlan(
        schema_version=SCHEMA_VERSION,
        mission_id=_mission_id(request, context),
        mission_fingerprint="",
        request=request,
        target_identity=context.target_identity,
        target_name=context.target_name,
        workspace_identity=context.workspace_identity,
        source_fingerprints=_source_fingerprints(context),
        objective=MissionObjective(
            statement=(
                "Define an implementation-ready engineering "
                "mission for "
                f"{request.primary_object or request.normalized_request}, "
                "while preserving established architecture, "
                "contracts and release quality requirements."
            )
        ),
        status=status,
        planning_confidence=confidence,
        risk_level=risk,
        scope=_scope(request),
        assumptions=assumptions,
        constraints=_constraints(),
        prerequisites=prerequisites,
        context=references,
        affected_areas=areas,
        workstreams=workstreams,
        deliverables=_deliverables(),
        acceptance_criteria=_acceptance_criteria(request),
        validation_strategy=_validation_strategy(
            context,
            risk,
        ),
        risks=(
            MissionRisk(
                risk_id="risk-primary",
                level=risk,
                statement=(
                    "The request is classified as "
                    f"{risk.value} risk from explicit request "
                    "terms and structural evidence."
                ),
                evidence=request.normalized_request,
                mitigation=(
                    "Confirm scope, approvals and validation "
                    "gates before execution."
                ),
            ),
        ),
        approvals=approvals,
        questions=questions,
        statistics=statistics,
    )

    return plan.model_copy(
        update={
            "mission_fingerprint": _plan_fingerprint(plan),
        }
    )



