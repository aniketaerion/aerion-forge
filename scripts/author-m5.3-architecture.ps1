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

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

$ExpectedBranch = "feature/m5.3-autonomous-mission-orchestrator"
$CurrentBranch = git branch --show-current

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read the current Git branch."
}

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.3 architecture must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$DocsRoot = "docs\autonomous_orchestration"

Write-Utf8NoBom "$DocsRoot\ARCHITECTURE.md" @'
# Aerion Forge M5.3 — Autonomous Mission Orchestrator Architecture

## Status

Architecture Draft

## Purpose

M5.3 coordinates complete engineering missions across the M5.1 autonomous runtime and the M5.2 autonomous execution engine.

M5.1 governs mission state, authority, approval, events, and recovery.

M5.2 executes one approved step through a controlled tool gateway.

M5.3 is the orchestration layer that repeatedly selects, executes, validates, records, and advances bounded mission steps until the mission reaches a terminal state or requires human intervention.

## Architectural Boundary

M5.3 may:

- start or resume one mission;
- load the approved mission plan;
- select the next eligible step;
- create one execution request;
- invoke M5.2 for one bounded execution attempt;
- record outcomes and evidence;
- advance mission and step states;
- apply bounded retry, rollback, replan, pause, or escalation decisions;
- stop at approvals, policy boundaries, or exhausted budgets;
- persist orchestration checkpoints;
- resume safely after interruption.

M5.3 may not:

- bypass M5.1 authority or approval controls;
- invoke tools directly;
- execute multiple mutating steps concurrently;
- create unbounded autonomous loops;
- silently alter an approved plan;
- continue after invariant, scope, or rollback failure;
- push, merge, release, deploy, or migrate without explicit approval.

## Core Components

1. Mission Orchestration Request
2. Mission Session
3. Orchestration State Machine
4. Plan Loader
5. Step Coordinator
6. Execution Request Factory
7. Outcome Processor
8. Mission Progress Tracker
9. Budget Monitor
10. Recovery Coordinator
11. Approval Stop Gate
12. Session Checkpoint Store
13. Resume Service
14. Orchestration Journal
15. Mission Orchestrator Service
16. Reporting and CLI

## Orchestration Flow

```text
MISSION START OR RESUME
  -> LOAD MISSION SNAPSHOT
  -> VERIFY MISSION STATE
  -> LOAD APPROVED PLAN
  -> VERIFY PLAN VERSION
  -> SELECT NEXT ELIGIBLE STEP
  -> CHECK AUTHORITY AND APPROVAL
  -> CREATE EXECUTION REQUEST
  -> EXECUTE ONE STEP THROUGH M5.2
  -> PROCESS EXECUTION OUTCOME
  -> RECORD EVIDENCE AND EVENTS
  -> UPDATE STEP AND MISSION PROGRESS
  -> CHECK BUDGETS AND STOP CONDITIONS
  -> CONTINUE, RETRY, ROLLBACK, REPLAN, PAUSE, ESCALATE, OR COMPLETE
```

## Safety Principles

- One mission session per mission.
- One active step execution per mission.
- One repository writer at a time.
- Every iteration consumes an execution-cycle budget.
- Every state change is journaled.
- Approved plan versions are immutable.
- Resumption requires a verified session checkpoint.
- Human approval gates are hard stops.
- Terminal missions never resume.
- Failure is explicit; no silent continuation.
'@

Write-Utf8NoBom "$DocsRoot\SPECIFICATION.md" @'
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
'@

Write-Utf8NoBom "$DocsRoot\DATA_MODEL.md" @'
# M5.3 Autonomous Mission Orchestration Data Model

## Core Models

### OrchestrationRequest

- request_id
- mission_id
- repository_root
- dry_run
- maximum_cycles
- requested_by
- created_at

### MissionSession

- session_id
- mission_id
- plan_id
- plan_version
- repository_root
- state
- current_step_id
- completed_step_ids
- failed_step_ids
- cycle_count
- execution_count
- retry_count
- rollback_count
- replan_count
- checkpoint_id
- stop_reason
- version
- created_at
- updated_at

### OrchestrationIteration

- iteration_id
- session_id
- sequence
- mission_version_before
- mission_version_after
- selected_step_id
- execution_request_id
- execution_id
- outcome
- recovery_action
- evidence_ids
- event_ids
- started_at
- completed_at

### SessionCheckpoint

- checkpoint_id
- session_id
- mission_id
- session_version
- mission_snapshot_version
- plan_version
- repository_fingerprint
- current_step_id
- completed_step_ids
- verified
- created_at

### OrchestrationStop

- stop_id
- session_id
- stop_kind
- reason
- approval_required
- resumable
- created_at

## Invariants

- One active session per mission.
- Session plan version must match the approved mission plan.
- Cycle count never exceeds the request or runtime budget.
- Completed steps cannot execute again.
- One iteration creates at most one execution request.
- Session updates require matching optimistic version.
- Resume requires a verified checkpoint.
- Terminal missions and sessions cannot resume.
'@

Write-Utf8NoBom "$DocsRoot\STATE_MACHINE.md" @'
# M5.3 Mission Orchestration State Machine

```text
CREATED
  -> INITIALIZING
  -> PLAN_LOADING
  -> READY
  -> STEP_SELECTING
  -> STEP_PREPARING
  -> STEP_EXECUTING
  -> OUTCOME_PROCESSING
  -> PROGRESS_UPDATING
  -> CONTINUE_CHECK
```

From `CONTINUE_CHECK`, the session may transition to:

```text
STEP_SELECTING
AWAITING_APPROVAL
RETRY_PENDING
ROLLBACK_PENDING
REPLAN_PENDING
PAUSED
ESCALATED
COMPLETED
FAILED
CANCELLED
```

Resume flow:

```text
PAUSED
  -> RESUME_VALIDATING
  -> READY
```

Terminal states:

- COMPLETED
- FAILED
- CANCELLED

Terminal sessions cannot resume.
'@

Write-Utf8NoBom "$DocsRoot\STOP_MODEL.md" @'
# M5.3 Orchestration Stop Model

## Mandatory Stop Conditions

- Approval required
- Authority insufficient
- Mission paused or cancelled
- Plan-version mismatch
- Session-version conflict
- Cycle budget exhausted
- Retry budget exhausted
- Rollback budget exhausted
- Replan budget exhausted
- Scope violation
- Invariant violation
- Checkpoint verification failure
- Rollback failure
- Terminal mission state
- Human escalation required

## Stop Categories

- awaiting_approval
- blocked
- paused
- escalated
- completed
- failed
- cancelled

Every stop includes a reason, resumability flag, and evidence references.
'@

Write-Utf8NoBom "$DocsRoot\RESUME_MODEL.md" @'
# M5.3 Resume and Restart Model

## Resume Preconditions

- Session is resumable.
- Session checkpoint exists.
- Checkpoint is verified.
- Mission identifier matches.
- Mission snapshot version is compatible.
- Approved plan version matches.
- Repository fingerprint is acceptable.
- No conflicting active session exists.
- No active execution lease exists.
- Mission is not terminal.

## Resume Behaviour

- Restore session state.
- Revalidate budgets.
- Revalidate approval and authority.
- Re-evaluate the current step.
- Never replay a completed iteration.
- Never repeat a completed step.
- Emit a resume event.
'@

Write-Utf8NoBom "$DocsRoot\ACCEPTANCE_CRITERIA.md" @'
# M5.3 Acceptance Criteria

M5.3 is complete only when:

- [ ] Mission sessions are immutable and versioned.
- [ ] One active session per mission is enforced.
- [ ] Approved plan versions are enforced.
- [ ] Next-step selection is deterministic.
- [ ] One orchestration iteration invokes at most one M5.2 execution.
- [ ] Completed steps cannot execute again.
- [ ] Mission progress is updated from execution outcomes.
- [ ] Execution evidence is linked to mission progress.
- [ ] All orchestration budgets are finite and enforced.
- [ ] Approval boundaries stop execution.
- [ ] Recovery actions follow M5.1 policy.
- [ ] Session checkpoints are verified.
- [ ] Resume is idempotent.
- [ ] Terminal sessions cannot resume.
- [ ] Dry-run performs no repository mutation.
- [ ] Structured reports are generated.
- [ ] Ruff passes.
- [ ] MyPy passes.
- [ ] M5.3 focused tests pass.
- [ ] Full repository tests pass.
'@

Write-Utf8NoBom "$DocsRoot\DECISIONS.md" @'
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
'@

$RequiredFiles = @(
    "ARCHITECTURE.md",
    "SPECIFICATION.md",
    "DATA_MODEL.md",
    "STATE_MACHINE.md",
    "STOP_MODEL.md",
    "RESUME_MODEL.md",
    "ACCEPTANCE_CRITERIA.md",
    "DECISIONS.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $DocsRoot $File

    if (-not (Test-Path $Path)) {
        throw "Missing M5.3 architecture document: $Path"
    }

    if ((Get-Item $Path).Length -lt 300) {
        throw "M5.3 architecture document is unexpectedly small: $Path"
    }

    $Content = Get-Content $Path -Raw

    if ($Content -match "_To be completed\._") {
        throw "Placeholder remains in M5.3 architecture document: $Path"
    }
}

Write-Host ""
Write-Host "M5.3 ARCHITECTURE DOCUMENTS WRITTEN AND CHECKED" -ForegroundColor Green

Get-ChildItem $DocsRoot |
    Sort-Object Name |
    Select-Object Name, Length |
    Format-Table -AutoSize