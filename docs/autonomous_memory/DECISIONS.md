# M5.5 Architecture Decisions

## ADR-001 — Memory is evidence-backed

Unverified model output cannot be stored as fact.

## ADR-002 — Repository evidence outranks memory

Memory assists current analysis but cannot override fresh repository inspection.

## ADR-003 — Immutable history

Records are superseded, disputed, expired, or quarantined; they are not silently overwritten.

## ADR-004 — Repository scope by default

Cross-repository reuse requires explicit applicability and policy approval.

## ADR-005 — Negative evidence is retained

Failed approaches and failed reused guidance remain available.

## ADR-006 — Secrets are prohibited

Memory ingestion applies mandatory redaction and rejection policy.

## ADR-007 — Deterministic retrieval

Identical queries against identical stores produce identical ordering.

## ADR-008 — Learning is advisory

Learning records do not automatically change authority, approval, or execution policy.

## ADR-009 — Outcome feedback is explicit

Success and failure attribution require validated mission outcomes.