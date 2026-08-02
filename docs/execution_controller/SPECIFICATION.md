# Execution Controller Specification

Milestone: 3.1
Forge version: 0.4

## Scope

M3.1 establishes controlled execution orchestration, approval enforcement,
state management, evidence recording, atomic persistence, and deterministic
reporting.

It does not implement autonomous source editing, build execution, deployment,
Git mutation, migrations, or autonomous recovery.

## Functional requirements

- Accept an execution request for one persisted mission.
- Resolve Mission, Task, Impact, Memory, and Reporting lineage.
- Reject incomplete or mismatched lineage.
- Require explicit approval before execution.
- Create deterministic request and session identities.
- Enforce the frozen execution state machine.
- Reject illegal transitions.
- Dispatch only registered and approved operations.
- Record operation requests, results, failures, and evidence.
- Support cancellation and terminal-state enforcement.
- Produce deterministic JSON and Markdown reports.
- Preserve bounded execution history.
- Guarantee that dry-run mode causes no target mutation.

## Non-functional requirements

- Frozen strict models
- Canonical ordering
- Deterministic fingerprints
- Atomic persistence
- Controlled errors
- Complete auditability
- No hidden side effects
- Bounded history
