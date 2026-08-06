# M5.3 Architecture Decisions

## ADR-001 — M5.3 orchestrates; it does not execute tools

All tool execution remains inside M5.2.

## ADR-002 — One bounded iteration

One orchestration iteration processes at most one mission step execution.

## ADR-003 — One active session per mission

Concurrent orchestration of the same mission is prohibited.

## ADR-004 — Approved plan version is immutable

A plan-version change requires revalidation and a new orchestration decision.

## ADR-005 — Verified checkpoint before resume

Interrupted sessions resume only from verified session checkpoints.

## ADR-006 — Explicit stop gates

Approval, authority, policy, invariant, scope, and budget boundaries stop immediately.

## ADR-007 — Completed work is never replayed

Completed steps and committed iterations are idempotent.

## ADR-008 — Dry-run by default

CLI orchestration defaults to read-only simulation.