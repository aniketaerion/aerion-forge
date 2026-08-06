"""Application service for bounded candidate preparation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.candidate_generator import (
    CandidateGenerationResult,
    generate_candidates,
)
from forge.autonomous_decision.deduplication import (
    CandidateDeduplicationResult,
    deduplicate_candidates,
)
from forge.autonomous_decision.feasibility import (
    FeasibilityResult,
    evaluate_feasibility,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.policy_filter import (
    PolicyFilterResult,
    evaluate_candidate_policy,
)
from forge.autonomous_decision.states import (
    CandidateRejectionReason,
)


@dataclass(frozen=True, slots=True)
class PreparedCandidate:
    """Candidate with hard-filter results."""

    candidate: CandidateAction
    feasibility: FeasibilityResult
    policy: PolicyFilterResult

    @property
    def accepted(self) -> bool:
        return self.feasibility.feasible and self.policy.allowed

    @property
    def rejection_reasons(
        self,
    ) -> tuple[CandidateRejectionReason, ...]:
        return tuple(
            dict.fromkeys(
                self.feasibility.rejection_reasons
                + self.policy.rejection_reasons
            )
        )


@dataclass(frozen=True, slots=True)
class CandidatePreparationResult:
    """Complete candidate-preparation result."""

    generated: CandidateGenerationResult
    deduplicated: CandidateDeduplicationResult
    prepared: tuple[PreparedCandidate, ...]

    @property
    def accepted(self) -> tuple[PreparedCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.prepared
            if candidate.accepted
        )

    @property
    def rejected(self) -> tuple[PreparedCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.prepared
            if not candidate.accepted
        )


@dataclass(frozen=True, slots=True)
class CandidatePreparationService:
    """Generate, deduplicate, and hard-filter candidates."""

    policy: AutonomousDecisionPolicy

    def prepare(
        self,
        request: DecisionRequest,
        context: DecisionContext,
    ) -> CandidatePreparationResult:
        generated = generate_candidates(
            request,
            context,
            self.policy,
        )
        deduplicated = deduplicate_candidates(
            generated.candidates
        )

        prepared = tuple(
            PreparedCandidate(
                candidate=candidate,
                feasibility=evaluate_feasibility(
                    candidate,
                    context,
                ),
                policy=evaluate_candidate_policy(
                    candidate,
                    context,
                    self.policy,
                ),
            )
            for candidate in deduplicated.candidates
        )

        return CandidatePreparationResult(
            generated=generated,
            deduplicated=deduplicated,
            prepared=prepared,
        )