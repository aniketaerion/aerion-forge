"""Bounded deterministic candidate generation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.identifiers import (
    candidate_action_identifier,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


@dataclass(frozen=True, slots=True)
class CandidateGenerationResult:
    """Generated candidates and truncation metadata."""

    candidates: tuple[CandidateAction, ...]
    truncated: bool


def _candidate(
    *,
    context: DecisionContext,
    action_kind: CandidateActionKind,
    description: str,
    source: CandidateSource,
    target_step_id: str | None = None,
    approval_required: bool = False,
    risk_class: str = "medium",
    reversible: bool = True,
    dependencies: tuple[str, ...] = (),
    evidence_references: tuple[str, ...] = (),
) -> CandidateAction:
    payload = {
        "context_id": context.context_id,
        "action_kind": action_kind.value,
        "target_step_id": target_step_id,
        "description": description,
        "source": source.value,
    }

    return CandidateAction(
        candidate_id=candidate_action_identifier(payload),
        action_kind=action_kind,
        target_step_id=target_step_id,
        description=description,
        required_authority=context.authority_level,
        approval_required=approval_required,
        risk_class=risk_class,
        expected_effects=(description,),
        reversible=reversible,
        dependencies=dependencies,
        evidence_references=evidence_references,
        source=source,
    )


def generate_candidates(
    request: DecisionRequest,
    context: DecisionContext,
    policy: AutonomousDecisionPolicy,
) -> CandidateGenerationResult:
    """Generate a deterministic finite candidate set."""
    limit = min(
        request.maximum_candidates,
        policy.thresholds.maximum_candidates,
    )
    candidates: list[CandidateAction] = []

    if context.current_step_id is not None:
        if context.current_step_id in context.failed_step_ids:
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.RETRY_CURRENT_STEP
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        f"Retry failed step {context.current_step_id}."
                    ),
                    source=CandidateSource.EXECUTION_OUTCOME,
                    evidence_references=context.evidence_references,
                )
            )
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.ROLLBACK_CURRENT_STEP
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        f"Rollback failed step "
                        f"{context.current_step_id}."
                    ),
                    source=CandidateSource.RECOVERY_POLICY,
                    approval_required=True,
                    risk_class="high",
                    evidence_references=context.evidence_references,
                )
            )
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.REPLAN_REMAINING_WORK
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        "Replan remaining work after failed step."
                    ),
                    source=CandidateSource.RECOVERY_POLICY,
                    approval_required=True,
                    risk_class="medium",
                    evidence_references=context.evidence_references,
                )
            )
        elif context.current_step_id not in context.completed_step_ids:
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.EXECUTE_NEXT_STEP
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        f"Execute current approved step "
                        f"{context.current_step_id}."
                    ),
                    source=CandidateSource.APPROVED_PLAN,
                    evidence_references=context.evidence_references,
                )
            )

    if context.approval_state != "approved":
        candidates.append(
            _candidate(
                context=context,
                action_kind=CandidateActionKind.REQUEST_APPROVAL,
                description="Request approval before continuing.",
                source=CandidateSource.ORCHESTRATION_STATE,
                approval_required=True,
                risk_class="low",
                evidence_references=context.evidence_references,
            )
        )

    if context.unresolved_findings:
        candidates.append(
            _candidate(
                context=context,
                action_kind=CandidateActionKind.PAUSE_MISSION,
                description=(
                    "Pause mission until unresolved findings are "
                    "addressed."
                ),
                source=CandidateSource.VALIDATION_FINDING,
                risk_class="low",
                evidence_references=context.evidence_references,
            )
        )

    if (
        context.current_step_id is None
        and not context.failed_step_ids
        and not context.unresolved_findings
    ):
        candidates.append(
            _candidate(
                context=context,
                action_kind=CandidateActionKind.COMPLETE_MISSION,
                description="Complete the mission.",
                source=CandidateSource.ORCHESTRATION_STATE,
                risk_class="low",
                evidence_references=context.evidence_references,
            )
        )

    candidates.append(
        _candidate(
            context=context,
            action_kind=CandidateActionKind.ESCALATE_MISSION,
            description="Escalate the mission for human review.",
            source=CandidateSource.ORCHESTRATION_STATE,
            risk_class="low",
            evidence_references=context.evidence_references,
        )
    )

    ordered = tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                candidate.action_kind.value,
                candidate.target_step_id or "",
                candidate.candidate_id,
            ),
        )
    )
    truncated = len(ordered) > limit

    return CandidateGenerationResult(
        candidates=ordered[:limit],
        truncated=truncated,
    )