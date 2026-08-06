[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

$GeneratedDate = Get-Date -Format "yyyy-MM-dd"

Write-Utf8NoBom "docs\autonomous_runtime\ARCHITECTURE.md" @"
# Aerion Forge v1.0 — Autonomous Runtime Architecture

**Phase:** 5  
**Milestone:** M5.1  
**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

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

```text
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
```

## 5. Core components

### Mission Intake Gateway

Normalizes objective, repository, scope, exclusions, constraints, acceptance criteria, requested authority, and budgets into a `MissionRequest`.

### Mission Qualifier

Returns `ACCEPT`, `REQUEST_CLARIFICATION`, `REJECT`, or `ESCALATE` after checking repository availability, clarity, risk, capability availability, and policy.

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

Read-only component that decides `APPROVE`, `REVISE`, `ESCALATE`, or `REJECT` after comparing results with the original objective and approved plan.

### Recovery Controller

Classifies failure and selects bounded retry, replan, rollback, pause, escalation, or abort.

### Event Journal

Append-only, ordered, redacted mission events. M5.1 uses snapshots plus an event journal; it does not require full event sourcing of repository content.

### Mission Repository

Persists versioned mission snapshots and immutable approvals, events, evidence, checkpoints, tool invocations, and outcomes.

## 6. Runtime loop

```text
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
```

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

```text
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
```
"@

Write-Utf8NoBom "docs\autonomous_runtime\DATA_MODEL.md" @"
# Autonomous Runtime Data Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## Design rules

- Core contracts are immutable.
- Unknown fields are rejected.
- Timestamps are UTC.
- Persistent records carry schema versions.
- Events, approvals, evidence, checkpoints, and outcomes are immutable.
- Secrets and raw environment values are prohibited.

## MissionState

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

## Core enumerations

- `MissionDecision`: ACCEPT, REQUEST_CLARIFICATION, REJECT, ESCALATE
- `RiskClass`: R0_READ_ONLY through R5_HUMAN_CONTROLLED
- `AuthorityLevel`: A0_READ through A6_MERGE_RELEASE
- `StepStatus`: PENDING, READY, AWAITING_APPROVAL, RUNNING, SUCCEEDED, FAILED, SKIPPED, ROLLED_BACK, CANCELLED
- `ValidationStatus`: PASS, FAIL, WARN, SKIP, UNAVAILABLE, ERROR
- `ReviewDecision`: APPROVE, REVISE, ESCALATE, REJECT
- `RecoveryAction`: RETRY_STEP, REPLAN, ROLLBACK_STEP, ROLLBACK_MISSION, PAUSE, ESCALATE, ABORT

## MissionRequest

```text
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
```

## AutonomousMission

```text
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
```

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
"@

Write-Utf8NoBom "docs\autonomous_runtime\STATE_MACHINE.md" @"
# Autonomous Runtime State Machine

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## Primary flow

```text
RECEIVED -> QUALIFYING -> QUALIFIED -> CONTEXT_BUILDING -> CONTEXT_READY
-> PLANNING -> PLAN_READY -> AWAITING_APPROVAL -> APPROVED
-> EXECUTING -> VALIDATING -> REVIEWING -> COMPLETED
```

## Legal transitions

| From | To | Guard |
|---|---|---|
| RECEIVED | QUALIFYING | Request valid |
| QUALIFYING | QUALIFIED | Accepted |
| QUALIFYING | CLARIFICATION_REQUIRED | Required information missing |
| QUALIFYING | FAILED | Rejected |
| QUALIFYING | ESCALATED | Human decision required |
| CLARIFICATION_REQUIRED | QUALIFYING | Clarification supplied |
| QUALIFIED | CONTEXT_BUILDING | Capabilities available |
| CONTEXT_BUILDING | CONTEXT_READY | Context complete |
| CONTEXT_BUILDING | BLOCKED | Context dependency unavailable |
| CONTEXT_READY | PLANNING | Fingerprint valid |
| PLANNING | PLAN_READY | Plan structurally valid |
| PLANNING | BLOCKED | No safe plan |
| PLAN_READY | AWAITING_APPROVAL | Approval required |
| PLAN_READY | APPROVED | Automatic policy permits |
| AWAITING_APPROVAL | APPROVED | Valid approval issued |
| AWAITING_APPROVAL | CANCELLED | Denied and cancelled |
| APPROVED | EXECUTING | Preconditions, authority, checkpoint valid |
| EXECUTING | VALIDATING | Step execution ends |
| EXECUTING | ROLLING_BACK | Failure after mutation |
| EXECUTING | PAUSED | Authorized pause |
| EXECUTING | BLOCKED | Environment unavailable |
| VALIDATING | EXECUTING | Step passed; steps remain |
| VALIDATING | REVIEWING | Plan and validations complete |
| VALIDATING | ROLLING_BACK | Validation requires restoration |
| VALIDATING | PLANNING | Replan approved |
| REVIEWING | COMPLETED | Completion guard passes |
| REVIEWING | PLANNING | Revision and budget available |
| REVIEWING | ESCALATED | Human judgment required |
| ROLLING_BACK | ROLLED_BACK | Restoration verified |
| ROLLING_BACK | FAILED | Restoration failed |
| ROLLED_BACK | EXECUTING | Retry approved |
| ROLLED_BACK | PLANNING | Replan selected |
| PAUSED | EXECUTING | Resume checks pass |
| BLOCKED | CONTEXT_BUILDING | Context restored |
| BLOCKED | EXECUTING | Execution dependency restored |
| ESCALATED | AWAITING_APPROVAL | Escalation resolved |
| Any non-terminal | CANCELLED | Authorized cancellation |
| Any active | FAILED | Fatal invariant or unrecoverable error |

## Forbidden examples

- RECEIVED -> EXECUTING
- QUALIFIED -> COMPLETED
- PLAN_READY -> EXECUTING without approval evaluation
- VALIDATING -> COMPLETED without review
- FAILED, CANCELLED, or COMPLETED -> active state

## Transition guard order

1. current state;
2. legal transition;
3. non-terminal mission;
4. current version and lease;
5. available budgets;
6. authority;
7. approval;
8. evidence;
9. checkpoint;
10. transition-specific invariant.

## Completion guard

Completion requires objective satisfaction, required step completion, required validation, scope compliance, no critical finding, review approval, and persisted final evidence.
"@

Write-Utf8NoBom "docs\autonomous_runtime\AUTHORITY_MODEL.md" @"
# Autonomous Runtime Authority Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## Authority levels

| Level | Name | Examples |
|---|---|---|
| A0 | READ | Read files, search, inspect Git |
| A1 | PLAN | Build context and plans, generate proposals |
| A2 | MODIFY | Write approved files and bounded patches |
| A3 | EXECUTE | Run approved local tools, builds, and tests |
| A4 | COMMIT | Create branches, stage, and commit locally |
| A5 | PUSH | Push approved branches or review artifacts |
| A6 | MERGE_RELEASE | Merge, tag, migrate, deploy, or release |

Default autonomous ceiling in M5.1 is A2. Allowlisted validation may receive A3. A4–A6 require explicit approval.

## Risk classes

| Risk | Description | Default handling |
|---|---|---|
| R0 | Read-only | Automatic |
| R1 | Documentation or isolated tests | Automatic with evidence |
| R2 | Bounded local implementation | Plan approval |
| R3 | API, schema, auth, finance, safety, architecture | Explicit step approval |
| R4 | Migration, deployment, push, release, destructive | Multi-stage approval |
| R5 | Production or safety-critical control | Human-controlled only |

## Approval scope

Approval may restrict mission, plan version, step, repository, paths, commands, authority ceiling, time window, attempts, network, branch, remote, or release target.

Approval becomes invalid after expiry, revocation, incompatible repository change, plan revision, scope expansion, authority increase, or risk increase.

## Mandatory explicit approval

- authentication or authorization changes;
- destructive database operations;
- public API changes;
- financial or safety-critical logic;
- weakening tests or validation;
- dependency installation;
- network access;
- commit, push, merge, tag, deploy, migrate, or release.

## Separation of duties

For R4 and R5, planner and approver are distinct roles, reviewer is read-only, and release approval is separate from implementation approval.
"@

Write-Utf8NoBom "docs\autonomous_runtime\EVENT_MODEL.md" @"
# Autonomous Runtime Event Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## Event envelope

```text
event_id
schema_version
mission_id
sequence
event_type
actor
previous_state
new_state
correlation_id
causation_id
payload
occurred_at
```

## Event families

Mission:

```text
MISSION_RECEIVED
MISSION_QUALIFIED
MISSION_CLARIFICATION_REQUESTED
MISSION_CONTEXT_READY
MISSION_PLAN_READY
MISSION_APPROVAL_REQUESTED
MISSION_APPROVED
MISSION_PAUSED
MISSION_RESUMED
MISSION_BLOCKED
MISSION_ESCALATED
MISSION_CANCELLED
MISSION_COMPLETED
MISSION_FAILED
```

Step and plan:

```text
PLAN_CREATED
PLAN_REVISED
PLAN_INVALIDATED
STEP_READY
STEP_STARTED
STEP_TOOL_INVOKED
STEP_TOOL_COMPLETED
STEP_VALIDATION_COMPLETED
STEP_REVIEWED
STEP_COMPLETED
STEP_FAILED
STEP_RETRY_SCHEDULED
STEP_ROLLED_BACK
```

Authority and recovery:

```text
AUTHORITY_EVALUATED
AUTHORITY_GRANTED
AUTHORITY_DENIED
APPROVAL_ISSUED
APPROVAL_REVOKED
APPROVAL_EXPIRED
CHECKPOINT_CREATED
CHECKPOINT_VERIFIED
ROLLBACK_STARTED
ROLLBACK_COMPLETED
ROLLBACK_FAILED
REPLAN_REQUESTED
INVARIANT_VIOLATION_DETECTED
FINAL_EVIDENCE_BUNDLE_CREATED
```

## Guarantees

- Sequence increases strictly per mission.
- Events are append-only.
- Consumers are idempotent.
- Snapshot update and event append form one logical transaction.
- Payloads are schema-versioned and redacted.
- Secrets, tokens, keys, passwords, and raw environment values are prohibited.
"@

Write-Utf8NoBom "docs\autonomous_runtime\RECOVERY_MODEL.md" @"
# Autonomous Runtime Recovery Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## Checkpoint kinds

```text
GIT_COMMIT
GIT_STASH
WORKTREE_SNAPSHOT
FILE_SNAPSHOT
REVERSIBLE_PATCH
```

Every modifying step requires a verified checkpoint before execution.

## Failure classes

```text
TRANSIENT_TOOL_FAILURE
DETERMINISTIC_TOOL_FAILURE
VALIDATION_FAILURE
SCOPE_VIOLATION
AUTHORITY_FAILURE
APPROVAL_FAILURE
ENVIRONMENT_FAILURE
CHECKPOINT_FAILURE
ROLLBACK_FAILURE
INVARIANT_VIOLATION
BUDGET_EXHAUSTION
```

## Recovery actions

```text
RETRY_STEP
REPLAN
ROLLBACK_STEP
ROLLBACK_MISSION
PAUSE
ESCALATE
ABORT
```

## Default budgets

```text
maximum attempts per step: 2
maximum replans per mission: 2
maximum rollback attempts: 1
maximum consecutive tool failures: 3
maximum total execution cycles: 20
```

## Retry guard

Retry requires a retryable failure, unchanged valid authority, verified restored fingerprint, remaining budget, and no amplification of destructive effects.

## Rollback procedure

1. stop scheduling;
2. record process state;
3. select checkpoint;
4. verify metadata;
5. restore;
6. verify repository fingerprint;
7. run restoration checks;
8. append event;
9. retry, replan, pause, escalate, or fail.

Rollback failure stops autonomous mutation and transitions to `FAILED` or `ESCALATED` with manual recovery evidence.

Non-reversible actions require R4/R5 approval, compensating action, operator acknowledgement, and no automatic retry.
"@

Write-Utf8NoBom "docs\autonomous_runtime\SPECIFICATION.md" @"
# Autonomous Runtime Specification

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## Functional requirements

- FR-001: Create a validated bounded mission request.
- FR-002: Qualify, clarify, reject, or escalate before planning.
- FR-003: Build provenance-backed context tied to a repository fingerprint.
- FR-004: Produce independently verifiable plan steps.
- FR-005: Evaluate authority before every action.
- FR-006: Pause when approval is missing, stale, revoked, or out of scope.
- FR-007: Reject illegal state transitions.
- FR-008: Require a verified checkpoint before mutation.
- FR-009: Route all external actions through the Tool Gateway.
- FR-010: Record typed tool, validation, review, and completion evidence.
- FR-011: Support bounded retry, replan, rollback, pause, escalation, and abort.
- FR-012: Complete only when all completion guards pass.
- FR-013: Support durable pause and safe resume.
- FR-014: Support authorized cancellation.
- FR-015: Generate mission summary, timeline, changes, evidence, decisions, findings, and outcome reports.

## Non-functional requirements

- NFR-001: Deterministic transitions for the same state, policy, and fingerprint.
- NFR-002: Complete auditability.
- NFR-003: No action beyond authority or scope.
- NFR-004: Finite execution budgets.
- NFR-005: Recoverable mutation unless explicitly non-reversible.
- NFR-006: Persistence across restart.
- NFR-007: Schema-versioned records.
- NFR-008: Secret redaction and network denial by default.
- NFR-009: Unit-testable transitions, authority, recovery, and completion guards.
- NFR-010: Inspectable state, approvals, budgets, evidence, findings, and outcome.

## M5.1 CLI

Read-only commands:

```text
forge autonomous mission create --dry-run
forge autonomous mission inspect
forge autonomous mission simulate-transition
forge autonomous mission validate
forge autonomous mission report
```

M5.1 CLI must not perform unrestricted repository mutation.
"@

Write-Utf8NoBom "docs\autonomous_runtime\ACCEPTANCE_CRITERIA.md" @"
# M5.1 Autonomous Runtime Acceptance Criteria

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## Architecture

- [ ] Mission-driven architecture is implemented.
- [ ] Phase 1–4 integrations are explicit.
- [ ] Module boundaries are enforced.
- [ ] Multi-agent mutation is deferred.
- [ ] Snapshots and event journal have separate responsibilities.

## Data and state

- [ ] Core contracts are immutable and schema-versioned.
- [ ] Every state is defined once.
- [ ] Legal transitions have guards.
- [ ] Illegal transitions raise typed errors.
- [ ] Terminal states cannot resume.
- [ ] Completion requires objective, evidence, validation, scope compliance, and review.

## Authority and recovery

- [ ] A0–A6 and R0–R5 are machine-enforceable.
- [ ] Approval scope, expiry, revocation, and invalidation are enforced.
- [ ] A4–A6 require explicit approval.
- [ ] Mutation requires a verified checkpoint.
- [ ] Retry and replan budgets are finite.
- [ ] Rollback verifies the restored fingerprint.
- [ ] Rollback failure stops autonomous execution.

## Runtime and events

- [ ] Runtime executes one step at a time.
- [ ] Tool actions pass through one gateway.
- [ ] Review engine is read-only.
- [ ] Events are ordered, append-only, redacted, and idempotent.
- [ ] Mission state survives restart.

## CLI and validation

- [ ] CLI creates dry-run missions.
- [ ] CLI inspects missions.
- [ ] CLI simulates legal transitions and rejects illegal transitions.
- [ ] CLI generates reports.
- [ ] Ruff passes.
- [ ] MyPy passes.
- [ ] Focused M5.1 tests pass.
- [ ] Full repository tests pass.
- [ ] M5.1 architecture and completion validators pass.
- [ ] No unrestricted autonomous mutation exists in M5.1.
"@

Write-Utf8NoBom "docs\autonomous_runtime\DECISIONS.md" @"
# Autonomous Runtime Architecture Decisions

**Status:** Active  
**Version:** 0.2  
**Last Updated:** $GeneratedDate

## ADR-001 — Mission-driven runtime

Use `AutonomousMission`, not prompt history, as the runtime aggregate.

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
"@

Write-Host ""
Write-Host "Running architecture consistency checks..." -ForegroundColor Cyan

$Root = Join-Path $RepositoryRoot "docs\autonomous_runtime"
$RequiredFiles = @(
    "ARCHITECTURE.md",
    "SPECIFICATION.md",
    "DATA_MODEL.md",
    "STATE_MACHINE.md",
    "AUTHORITY_MODEL.md",
    "EVENT_MODEL.md",
    "RECOVERY_MODEL.md",
    "ACCEPTANCE_CRITERIA.md",
    "DECISIONS.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $Root $File

    if (-not (Test-Path $Path)) {
        throw "Missing architecture document: $Path"
    }

    if ((Get-Item $Path).Length -lt 500) {
        throw "Architecture document is unexpectedly small: $Path"
    }

    if ((Get-Content $Path -Raw) -match "_To be completed\._") {
        throw "Placeholder remains in architecture document: $Path"
    }
}

$States = @(
    "RECEIVED", "QUALIFYING", "CLARIFICATION_REQUIRED", "QUALIFIED",
    "CONTEXT_BUILDING", "CONTEXT_READY", "PLANNING", "PLAN_READY",
    "AWAITING_APPROVAL", "APPROVED", "EXECUTING", "VALIDATING",
    "REVIEWING", "PAUSED", "BLOCKED", "ROLLING_BACK", "ROLLED_BACK",
    "ESCALATED", "COMPLETED", "FAILED", "CANCELLED"
)

$DataModel = Get-Content (Join-Path $Root "DATA_MODEL.md") -Raw
$StateMachine = Get-Content (Join-Path $Root "STATE_MACHINE.md") -Raw

foreach ($State in $States) {
    if ($DataModel -notmatch "\b$State\b") {
        throw "State missing from DATA_MODEL.md: $State"
    }

    if ($StateMachine -notmatch "\b$State\b") {
        throw "State missing from STATE_MACHINE.md: $State"
    }
}

Write-Host ""
Write-Host "M5.1 ARCHITECTURE DOCUMENTS WRITTEN AND CHECKED" -ForegroundColor Green

Get-ChildItem $Root |
    Sort-Object Name |
    Select-Object Name, Length |
    Format-Table -AutoSize

git status --short
