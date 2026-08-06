# Autonomous Runtime Architecture Decisions

**Status:** Active  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## ADR-001 — Mission-driven runtime

Use AutonomousMission, not prompt history, as the runtime aggregate.

## ADR-002 — Explicit state machine

Exactly one state and only documented transitions.

## ADR-003 — One-step execution

Execute one eligible step at a time to support approval, evidence, checkpointing, and rollback.

## ADR-004 — Per-action authority

Editing authority does not imply commit, push, merge, deployment, or release authority.

## ADR-005 — Snapshot plus event journal

Use versioned snapshots and append-only events. Full event sourcing is unnecessary in M5.1.

## ADR-006 — Single writer

Permit one active execution lease per mission. Defer autonomous multi-agent mutation.

## ADR-007 — Checkpoint before mutation

No repository mutation without a verified restoration point.

## ADR-008 — Read-only reviewer

The component judging completion cannot silently change the work.

## ADR-009 — Finite budgets

Attempts, replans, tool calls, steps, and duration are bounded.

## ADR-010 — Structured evidence

Completion uses typed evidence tied to a repository fingerprint, not console text.

## ADR-011 — No unrestricted execution in M5.1

M5.1 implements contracts, policies, transitions, simulation, inspection, and reporting before real autonomous mutation is enabled.