# M5.3 Autonomous Mission Orchestrator Specification

## Functional Requirements

- Start a new orchestration session from an eligible mission.
- Resume an interrupted session from a verified checkpoint.
- Load the mission's approved plan.
- Reject plan-version mismatch.
- Reject unsupported mission states.
- Select the next eligible step deterministically.
- Create exactly one M5.2 execution request per orchestration iteration.
- Process successful, failed, dry-run, blocked, paused, and escalated outcomes.
- Record execution evidence references on the mission.
- Update completed-step identifiers.
- Maintain attempt, tool-call, replan, rollback, and cycle counts.
- Enforce all M5.1 and M5.2 budgets.
- Stop at approval boundaries.
- Apply recovery decisions through the M5.1 recovery model.
- Persist restart-safe orchestration checkpoints.
- Detect stale session versions.
- Produce structured progress reports.
- Support read-only simulation.

## Non-Functional Requirements

- Deterministic orchestration
- Bounded loops
- Idempotent resume
- Immutable journal
- Optimistic session versioning
- Explicit stop reasons
- Typed errors
- Auditability
- Restart safety
- Dry-run by default