# M5.4 Architecture Decisions

## ADR-001 — Decision engine does not execute tools

M5.4 returns decisions to M5.3. M5.2 remains the only controlled execution boundary.

## ADR-002 — Hard filters before scoring

Infeasible, unauthorized, unsafe, duplicate, or out-of-scope candidates are rejected before ranking.

## ADR-003 — Deterministic candidate ranking

Identical inputs and policy versions must produce the same ranking and selected decision.

## ADR-004 — Evidence is mandatory

Every selected action must reference supporting evidence.

## ADR-005 — Explicit uncertainty

Confidence and evidence quality are first-class decision fields.

## ADR-006 — One selected action

A committed decision selects at most one candidate.

## ADR-007 — No-safe-action is valid

When no candidate satisfies policy and thresholds, M5.4 returns a stop decision rather than forcing progress.

## ADR-008 — Context fingerprinting

Committed decisions are bound to the exact evaluated context.

## ADR-009 — Dry-run by default

CLI and simulation paths do not mutate repository or mission state.