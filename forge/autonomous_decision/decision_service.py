"""Application service for one complete autonomous decision."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.assessment_service import (
    CandidateAssessmentService,
)
from forge.autonomous_decision.candidate_service import (
    CandidatePreparationService,
)
from forge.autonomous_decision.context_fingerprint import (
    decision_context_fingerprint,
)
from forge.autonomous_decision.decision_journal import (
    InMemoryDecisionJournal,
)
from forge.autonomous_decision.identifiers import (
    decision_record_identifier,
    decision_stop_identifier,
)
from forge.autonomous_decision.models import (
    CandidateAssessment,
    DecisionContext,
    DecisionRecord,
    DecisionRequest,
    DecisionStop,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.rationale import (
    DecisionRationale,
    build_rationale,
)
from forge.autonomous_decision.replay_guard import (
    DecisionReplayGuard,
)
from forge.autonomous_decision.selector import (
    SelectionResult,
    select_candidate,
)
from forge.autonomous_decision.states import (
    DecisionDisposition,
    DecisionStopKind,
)


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Complete M5.4 decision result."""

    record: DecisionRecord
    stop: DecisionStop | None
    selection: SelectionResult
    rationale: DecisionRationale
    assessments: tuple[CandidateAssessment, ...]


@dataclass(slots=True)
class AutonomousDecisionService:
    """Generate, assess, select, journal, and replay-guard decisions."""

    policy: AutonomousDecisionPolicy
    journal: InMemoryDecisionJournal
    replay_guard: DecisionReplayGuard

    def decide(
        self,
        request: DecisionRequest,
        context: DecisionContext,
    ) -> DecisionResult:
        preparation = CandidatePreparationService(
            policy=self.policy
        ).prepare(request, context)

        assessor = CandidateAssessmentService(
            policy=self.policy
        )
        assessments = tuple(
            assessor.assess(item, context)
            for item in preparation.prepared
        )

        candidates = tuple(
            item.candidate
            for item in preparation.prepared
        )
        selection = select_candidate(
            candidates,
            assessments,
        )

        rationale = build_rationale(
            context=context,
            disposition=selection.disposition,
            selected=selection.selected,
            assessments=assessments,
        )

        fingerprint = decision_context_fingerprint(context)
        selected_candidate_id = (
            selection.selected.candidate.candidate_id
            if selection.selected is not None
            else None
        )
        selected_assessment = (
            selection.selected.assessment
            if selection.selected is not None
            else None
        )

        payload = {
            "request_id": request.request_id,
            "context_id": context.context_id,
            "context_fingerprint": fingerprint,
            "selected_candidate_id": selected_candidate_id,
            "disposition": selection.disposition.value,
        }

        record = DecisionRecord(
            decision_id=decision_record_identifier(payload),
            request_id=request.request_id,
            context_id=context.context_id,
            selected_candidate_id=selected_candidate_id,
            decision_kind=request.decision_kind,
            disposition=selection.disposition,
            rationale=rationale.summary,
            alternative_candidate_ids=tuple(
                ranked.candidate.candidate_id
                for ranked in selection.ranked[1:]
            ),
            rejected_candidate_ids=tuple(
                sorted(
                    assessment.candidate_id
                    for assessment in assessments
                    if assessment.rejection_reasons
                )
            ),
            assessment_ids=tuple(
                assessment.assessment_id
                for assessment in assessments
            ),
            evidence_references=context.evidence_references,
            approval_required=(
                selection.selected.candidate.approval_required
                if selection.selected is not None
                else False
            ),
            confidence=(
                selected_assessment.confidence_score
                if selected_assessment is not None
                else 0.0
            ),
            context_fingerprint=fingerprint,
        )

        committed = self.replay_guard.check_and_record(record)

        if committed.decision_id not in {
            item.decision_id
            for item in self.journal.all_records()
        }:
            self.journal.append(committed)

        stop = None

        if (
            selection.disposition
            is DecisionDisposition.NO_SAFE_ACTION
        ):
            stop = DecisionStop(
                stop_id=decision_stop_identifier(
                    {
                        "request_id": request.request_id,
                        "context_fingerprint": fingerprint,
                        "stop_kind": (
                            DecisionStopKind.NO_SAFE_ACTION.value
                        ),
                    }
                ),
                request_id=request.request_id,
                stop_kind=DecisionStopKind.NO_SAFE_ACTION,
                reason=rationale.summary,
                resumable=True,
                evidence_references=context.evidence_references,
            )

        return DecisionResult(
            record=committed,
            stop=stop,
            selection=selection,
            rationale=rationale,
            assessments=assessments,
        )