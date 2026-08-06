# Autonomous Runtime Specification

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## Functional requirements

- FR-001: Create a validated bounded mission request.
- FR-002: Qualify, clarify, reject, or escalate before planning.
- FR-003: Build provenance-backed context tied to a repository fingerprint.
- FR-004: Produce independently verifiable plan steps.
- FR-005: Evaluate authority before every action.
- FR-006: Pause when approval is missing, stale, revoked, or out of scope.
- FR-007: Reject illegal state transitions.
- FR-008: Require a verified checkpoint before mutation.
- FR-009: Route all external actions through the Tool Gateway.
- FR-010: Record typed tool, validation, review, and completion evidence.
- FR-011: Support bounded retry, replan, rollback, pause, escalation, and abort.
- FR-012: Complete only when all completion guards pass.
- FR-013: Support durable pause and safe resume.
- FR-014: Support authorized cancellation.
- FR-015: Generate mission summary, timeline, changes, evidence, decisions, findings, and outcome reports.

## Non-functional requirements

- NFR-001: Deterministic transitions for the same state, policy, and fingerprint.
- NFR-002: Complete auditability.
- NFR-003: No action beyond authority or scope.
- NFR-004: Finite execution budgets.
- NFR-005: Recoverable mutation unless explicitly non-reversible.
- NFR-006: Persistence across restart.
- NFR-007: Schema-versioned records.
- NFR-008: Secret redaction and network denial by default.
- NFR-009: Unit-testable transitions, authority, recovery, and completion guards.
- NFR-010: Inspectable state, approvals, budgets, evidence, findings, and outcome.

## M5.1 CLI

Read-only commands:

`	ext
forge autonomous mission create --dry-run
forge autonomous mission inspect
forge autonomous mission simulate-transition
forge autonomous mission validate
forge autonomous mission report
`

M5.1 CLI must not perform unrestricted repository mutation.