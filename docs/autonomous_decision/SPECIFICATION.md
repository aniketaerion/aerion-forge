# M5.4 Autonomous Decision Engine Specification

## Functional Requirements

- Accept a structured decision request.
- Build a decision context from mission, plan, session, execution, validation, and repository evidence.
- Generate a finite candidate set.
- Normalize and deduplicate candidates.
- Reject candidates outside mission scope.
- Reject candidates requiring unavailable authority.
- Reject candidates violating approval policy.
- Reject candidates exceeding risk thresholds.
- Assess feasibility, risk, confidence, evidence quality, cost, reversibility, and expected value.
- Calculate deterministic candidate scores.
- Rank candidates deterministically.
- Select at most one action.
- Return an explicit stop decision when no candidate is acceptable.
- Produce a structured rationale.
- Record rejected alternatives and reasons.
- Record evidence references.
- Support retry, rollback, replan, pause, escalate, complete, and cancel decisions.
- Support dry-run simulation.
- Prevent replay of an identical decision against the same context fingerprint.
- Produce JSON and Markdown reports.

## Non-Functional Requirements

- Deterministic output for identical inputs
- Bounded candidate generation
- Explicit uncertainty
- Explainable scoring
- Immutable decision records
- Typed errors
- Stable identifiers
- Schema versioning
- Auditability
- No hidden side effects