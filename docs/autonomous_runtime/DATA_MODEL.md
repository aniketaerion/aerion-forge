# Aerion Forge Autonomous Runtime Data Model

**Status:** Architecture Draft
**Phase:** Phase 5
**Milestone:** M5.1
**Version:** 0.2

## 1. Design Rules

- Core contracts are immutable.
- Unknown fields are rejected.
- Timestamps use UTC.
- Persisted records include schema versions.
- Mission snapshots use optimistic versioning.
- Approvals, events, evidence, checkpoints, and outcomes are immutable.
- Secrets and raw environment values are prohibited.

## 2. Mission States

```text
RECEIVED
QUALIFYING
CLARIFICATION_REQUIRED
QUALIFIED
CONTEXT_BUILDING
CONTEXT_READY
PLANNING
PLAN_READY
AWAITING_APPROVAL
APPROVED
EXECUTING
VALIDATING
REVIEWING
PAUSED
BLOCKED
ROLLING_BACK
ROLLED_BACK
ESCALATED
COMPLETED
FAILED
CANCELLED
```

## 3. Core Models

### MissionRequest

Defines the engineering objective, repository root, requested scope, excluded scope, constraints, acceptance criteria, authority request, execution budgets, requester, and creation time.

### AutonomousMission

The AutonomousMission is the aggregate root of the runtime.

It contains:

- mission identifier
- schema version
- snapshot version
- current state
- risk class
- granted authority
- approval state
- context reference
- active plan reference
- current step
- attempt count
- replan count
- tool-call count
- checkpoint references
- event sequence
- validation evidence references
- findings
- final outcome
- creation and update timestamps

### MissionContext

Contains relevant repository files, symbols, dependency edges, architecture constraints, business rules, existing tests, validation commands, known risks, knowledge references, repository fingerprint, and source provenance.

### MissionPlan

Contains ordered steps, expected files, prohibited files, validation requirements, completion criteria, risk class, required authority, plan version, and approval state.

### MissionStep

Contains sequence, title, description, action kind, preconditions, expected outputs, expected files, prohibited files, authority requirement, risk class, approval requirement, validation requirements, checkpoint requirement, attempt budget, timeout, and dependencies.

### ApprovalDecision

Contains approval scope, authority granted, conditions, approver, issue time, expiry time, revocation state, and reason.

Approvals are immutable and cannot be reused for another mission.

### ToolInvocation

Contains tool name, action kind, redacted arguments, authority requirement, approval reference, execution times, exit code, output references, affected files, result digest, and status.

### ValidationEvidence

Contains check name, check kind, required status, result status, command, exit code, metrics, artifact references, repository fingerprint, and timestamps.

### MissionCheckpoint

Contains checkpoint type, repository fingerprint, Git head, working-tree digest, file snapshots, verification status, restoration test, and creation time.

A checkpoint is usable only when verified.

### MissionEvent

Contains event identifier, schema version, mission identifier, sequence, event type, previous state, new state, actor, redacted payload, correlation identifier, causation identifier, and timestamp.

Events are append-only and strictly ordered per mission.

### RecoveryDecision

Contains failure classification, selected recovery action, checkpoint reference, attempt number, reason, approver, and creation time.

### MissionOutcome

Contains terminal state, objective-satisfied flag, completed steps, changed files, validation evidence, unresolved findings, review decision, reports, and completion time.

## 4. Persistence Boundary

The mission snapshot changes only through validated and versioned transitions.

The following records are immutable:

- approvals
- events
- tool invocations
- validation evidence
- checkpoints
- recovery decisions
- outcomes

Repository content remains the source of truth for code. Forge stores mission control state and evidence, not a duplicate repository.
