# Aerion Forge v1.0 — Autonomous Runtime Architecture

**Phase:** 5  
**Milestone:** M5.1  
**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## 1. Purpose

Aerion Forge Phase 5 converts existing runtime, planning, execution, domain-intelligence, validation, and memory capabilities into a governed autonomous engineering platform.

The runtime operates on bounded missions, not free-form prompt loops. Every mission is qualified, planned, approved, executed one step at a time, validated, reviewed, recovered when necessary, and completed only with structured evidence.

## 2. Non-negotiable principles

- Mission-driven, not prompt-driven.
- Exactly one mission state is active.
- One plan step executes at a time.
- Every modifying action passes through a Tool Gateway.
- Authority is checked per action.
- Mutation requires a verified checkpoint.
- Retry, replan, runtime, and tool budgets are finite.
- Review is read-only.
- Tests alone do not prove mission completion.
- Push, merge, tag, deploy, migrate, and release require explicit authority.

## 3. M5.1 scope

M5.1 establishes the control plane:

- mission contracts and identifiers;
- lifecycle states and legal transitions;
- authority, risk, and approval contracts;
- event journal contracts;
- checkpoint and recovery policies;
- persistence interfaces;
- read-only CLI inspection and simulation;
- reporting and milestone validation.

M5.1 does **not** enable unrestricted autonomous code modification, multi-agent writing, deployment, or automatic release.

## 4. Layered architecture

`	ext
User / API / CLI
        |
        v
Mission Intake Gateway
        |
        v
Mission Qualification
        |
        v
Context Builder
        |
        v
Autonomous Planner
        |
        v
Authority + Approval Engine
        |
        v
Mission Orchestrator
        |
        +-------------------+
        |                   |
        v                   v
Tool Gateway          Event Journal
        |
        v
Execution -> Validation -> Review
        |
        v
Recovery Controller
        |
        v
Mission Outcome + Evidence Bundle
`

## 5. Core components

### Mission Intake Gateway

Normalizes objective, repository, scope, exclusions, constraints, acceptance criteria, requested authority, and budgets into a MissionRequest.

### Mission Qualifier

Returns ACCEPT, REQUEST_CLARIFICATION, REJECT, or ESCALATE after checking repository availability, clarity, risk, capability availability, and policy.

### Context Builder

Builds the minimum sufficient, provenance-backed context using Phase 1–4 capabilities. It must not load the entire repository blindly.

### Autonomous Planner

Creates a deterministic plan of independently verifiable steps. Each modifying step declares expected files, prohibited files, required authority, validation, timeout, attempt budget, and checkpoint strategy.

### Authority and Approval Engine

Evaluates every action against authority, risk, scope, approval freshness, expiry, revocation, and repository fingerprint.

### Mission Orchestrator

Selects the only legal next transition, enforces budgets, invokes tools, records evidence, coordinates validation and review, and persists mission state.

### Tool Gateway

The only permitted interface to filesystem, shell, Git, tests, build tools, network, and report generation. It validates arguments, confines paths, enforces policy, redacts secrets, and records affected files and results.

### Validation Coordinator

Produces typed evidence for syntax, static analysis, typing, focused tests, full tests, architecture, security, compatibility, acceptance, and scope checks.

### Review Engine

Read-only component that decides APPROVE, REVISE, ESCALATE, or REJECT after comparing results with the original objective and approved plan.

### Recovery Controller

Classifies failure and selects bounded retry, replan, rollback, pause, escalation, or abort.

### Event Journal

Append-only, ordered, redacted mission events. M5.1 uses snapshots plus an event journal; it does not require full event sourcing of repository content.

### Mission Repository

Persists versioned mission snapshots and immutable approvals, events, evidence, checkpoints, tool invocations, and outcomes.

## 6. Runtime loop

`	ext
1. Load mission snapshot.
2. Verify lease, version, invariants, and budgets.
3. Determine legal next action.
4. Verify authority and approval.
5. Create and verify checkpoint when mutation is possible.
6. Execute one action through the Tool Gateway.
7. Capture result and affected files.
8. Run required validation.
9. Run independent review.
10. Apply one state transition.
11. Persist snapshot and append event.
12. Continue, pause, recover, escalate, fail, cancel, or complete.
`

## 7. Integration with Phases 1–4

Phase 5 reuses:

- Workspace Manager and repository discovery;
- incremental index and knowledge graph;
- capability registry and runtime diagnostics;
- planning and safe-change planning;
- safe code editing and execution control;
- engineering memory;
- API, database, business, embedded, and knowledge-loader intelligence;
- phase-validation intelligence.

Duplication requires an explicit architecture decision.

## 8. Concurrency

M5.1 permits one active execution lease per mission. Parallel reads are allowed. Concurrent repository mutation is deferred unless separate worktrees, disjoint scopes, and explicit policy are introduced later.

## 9. Completion

A mission may complete only when:

- the objective is satisfied;
- required steps are complete;
- required validation passes;
- scope compliance passes;
- no critical finding remains;
- review approves completion;
- the final evidence bundle is persisted.

## 10. Critical corrections to the original concept

1. Use a mission aggregate instead of a generic agent loop.
2. Use snapshots plus events instead of full event sourcing in M5.1.
3. Keep one writer; defer autonomous multi-agent mutation.
4. Check authority per action rather than once per mission.
5. Require finite budgets instead of confidence-based continuation.
6. Require verified checkpoints before mutation.
7. Keep the reviewer read-only.
8. Treat structured evidence, not console output, as proof.

## 11. Module boundary

`	ext
forge/autonomous_runtime/
    __init__.py
    errors.py
    identifiers.py
    models.py
    states.py
    transitions.py
    policies.py
    authority.py
    approvals.py
    events.py
    checkpoints.py
    recovery.py
    repository.py
    service.py
    reporting.py
    cli.py
`
"@

Write-Utf8NoBom "docs\autonomous_runtime\DATA_MODEL.md" @"
# Autonomous Runtime Data Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## Design rules

- Core contracts are immutable.
- Unknown fields are rejected.
- Timestamps are UTC.
- Persistent records carry schema versions.
- Events, approvals, evidence, checkpoints, and outcomes are immutable.
- Secrets and raw environment values are prohibited.

## MissionState

`	ext
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
`

## Core enumerations

- MissionDecision: ACCEPT, REQUEST_CLARIFICATION, REJECT, ESCALATE
- RiskClass: R0_READ_ONLY through R5_HUMAN_CONTROLLED
- AuthorityLevel: A0_READ through A6_MERGE_RELEASE
- StepStatus: PENDING, READY, AWAITING_APPROVAL, RUNNING, SUCCEEDED, FAILED, SKIPPED, ROLLED_BACK, CANCELLED
- ValidationStatus: PASS, FAIL, WARN, SKIP, UNAVAILABLE, ERROR
- ReviewDecision: APPROVE, REVISE, ESCALATE, REJECT
- RecoveryAction: RETRY_STEP, REPLAN, ROLLBACK_STEP, ROLLBACK_MISSION, PAUSE, ESCALATE, ABORT

## MissionRequest

`	ext
request_id
schema_version
objective
repository_root
requested_scope
excluded_scope
constraints
acceptance_criteria
requested_authority
time_budget_seconds
maximum_steps
maximum_attempts_per_step
maximum_replans
requested_by
created_at
`

## AutonomousMission

`	ext
mission_id
schema_version
version
request
state
risk_class
granted_authority
approval_state
context_id
plan_id
current_step_id
attempt_count
replan_count
tool_call_count
checkpoint_ids
event_sequence
validation_evidence_ids
finding_ids
outcome_id
created_at
updated_at
`

Invariants:

- one active state;
- version increases on every persisted transition;
- terminal states cannot resume;
- current step belongs to the active plan;
- granted authority does not exceed approval;
- completed missions require an outcome.

## MissionContext

Contains repository fingerprint, relevant files and symbols, dependency edges, architecture constraints, business rules, tests, validation commands, risks, knowledge references, and provenance.

## MissionPlan

Contains versioned ordered steps, expected and prohibited files, required validation, completion criteria, risk, and authority ceiling.

## MissionStep

Contains sequence, action, preconditions, expected outputs, expected/prohibited files, authority, risk, approval requirement, validations, checkpoint requirement, timeout, dependencies, and attempt budget.

## ApprovalDecision

Contains mission, plan and step scope, authority granted, constraints, approver, issue/expiry/revocation times, and reason. Approval is immutable and cannot be reused across missions.

## ToolInvocation

Contains tool, action, redacted arguments, authority, approval reference, timing, exit code, output references, affected files, digest, and status.

## ValidationEvidence

Contains check name and kind, required flag, status, command, exit code, metrics, artifacts, repository fingerprint, and timing.

## MissionCheckpoint

Contains checkpoint kind, repository fingerprint, Git head, working-tree digest, snapshot references, verification result, and restoration test.

## MissionEvent

Contains sequence, type, actor, previous/new state, correlation and causation IDs, redacted payload, and timestamp.

## MissionOutcome

Contains terminal state, objective satisfaction, completed steps, changed files, evidence, unresolved findings, review decision, report references, and completion time.