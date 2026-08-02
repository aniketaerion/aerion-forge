"""Mission-plan integrity and safety validation."""

import hashlib
import json
import re

from forge.planning.models import (
    MissionApprovalLevel,
    MissionPlan,
    MissionRiskLevel,
    MissionScopeType,
    MissionValidationMessage,
    MissionValidationResult,
    MissionValidationSeverity,
)

_ABSOLUTE = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|root|tmp)/)")
_SECRET = re.compile(r"(?i)(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+")


def validate_plan(plan: MissionPlan) -> MissionValidationResult:
    messages: list[MissionValidationMessage] = []

    def error(field: str, message: str) -> None:
        messages.append(
            MissionValidationMessage(
                severity=MissionValidationSeverity.ERROR, field=field, message=message
            )
        )

    ids: list[str] = []
    for collection in (
        plan.scope,
        plan.assumptions,
        plan.constraints,
        plan.prerequisites,
        plan.context,
        plan.affected_areas,
        plan.workstreams,
        plan.deliverables,
        plan.acceptance_criteria,
        plan.validation_strategy,
        plan.risks,
        plan.approvals,
        plan.questions,
    ):
        for item in collection:
            for name in type(item).model_fields:
                if name.endswith("_id") and name != "entity_id":
                    ids.append(str(getattr(item, name)))
                    break
    if len(ids) != len(set(ids)):
        error("ids", "Canonical item identifiers must be unique.")
    scope_types = {x.scope_type for x in plan.scope}
    if scope_types != set(MissionScopeType):
        error("scope", "Mission scope must include in, out, conditional and unknown types.")
    if not plan.objective.statement.strip():
        error("objective", "Mission objective is required.")
    if not plan.deliverables or not plan.acceptance_criteria:
        error("deliverables", "Deliverables and acceptance criteria are required.")
    if plan.risk_level in {MissionRiskLevel.HIGH, MissionRiskLevel.CRITICAL} and not any(
        x.level is MissionApprovalLevel.HIGH_RISK_APPROVAL for x in plan.approvals
    ):
        error("approvals", "High-risk missions require high-risk approval.")
    actual = plan.statistics.model_copy(
        update={
            "affected_area_count": len(plan.affected_areas),
            "workstream_count": len(plan.workstreams),
            "assumption_count": len(plan.assumptions),
            "question_count": len(plan.questions),
            "blocking_prerequisite_count": sum(
                x.blocking and x.status.value == "unsatisfied" for x in plan.prerequisites
            ),
        }
    )
    if actual != plan.statistics:
        error("statistics", "Mission statistics do not match canonical collections.")
    safe = json.dumps(plan.model_dump(mode="json"), sort_keys=True)
    if _ABSOLUTE.search(safe):
        error("portable", "Mission contains a private absolute path.")
    if _SECRET.search(safe):
        error("security", "Mission may contain a secret value.")
    executable = ("edit ", "run pytest", "git commit", "line ", "apply patch")
    if any(term in safe.casefold() for term in executable):
        error("boundary", "Mission contains executable task or edit detail.")
    raw = plan.model_dump(mode="json")
    raw["mission_fingerprint"] = ""
    expected = hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if expected != plan.mission_fingerprint:
        error("mission_fingerprint", "Mission fingerprint does not match canonical plan content.")
    return MissionValidationResult(valid=not messages, messages=tuple(messages))

