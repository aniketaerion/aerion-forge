# M5.2 Architecture Decisions

## ADR-001 — Controlled tool gateway

All executable actions pass through one registered gateway.

## ADR-002 — One-step execution

The engine executes one eligible step at a time.

## ADR-003 — Single-writer lease

Only one active execution may mutate a repository.

## ADR-004 — Verified checkpoint before mutation

A mutating action cannot start without a verified checkpoint.

## ADR-005 — Effect verification

Actual affected files are compared with approved scope.

## ADR-006 — Dry-run by default

CLI execution defaults to simulation.

## ADR-007 — Finite recovery

Retries, replans, rollbacks, and execution cycles are bounded.

## ADR-008 — No arbitrary shell

M5.2 does not provide unrestricted command execution.