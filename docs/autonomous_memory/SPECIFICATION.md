# M5.5 Autonomous Memory and Learning Specification

## Functional Requirements

- Accept typed memory observations from completed or paused missions.
- Validate source provenance before persistence.
- Reject secret-bearing or prohibited content.
- Classify observations as fact, hypothesis, decision, outcome, failure, recovery, lesson, constraint, or preference.
- Preserve repository, mission, session, decision, execution, and evidence references.
- Calculate explicit confidence.
- Calculate applicability scope.
- Detect exact and semantic duplicates.
- Preserve immutable history.
- Supersede outdated records explicitly.
- Store positive and negative outcomes.
- Retrieve memory by repository, capability, module, domain, tags, event type, and time.
- Enforce authority and scope filters.
- Rank retrieval results deterministically.
- Explain retrieval scores.
- Prevent stale memory from overriding fresh repository evidence.
- Extract lessons from validated outcomes.
- Record whether reused guidance succeeds or fails.
- Produce JSON and Markdown memory reports.
- Provide read-only CLI inspection and simulation.

## Non-Functional Requirements

- Deterministic retrieval
- Typed immutable records
- Explicit provenance
- Explicit confidence
- Scope isolation
- Secret rejection
- Schema versioning
- Auditability
- Bounded retrieval
- Backward-compatible persistence
- No hidden side effects