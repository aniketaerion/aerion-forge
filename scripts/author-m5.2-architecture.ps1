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

$ExpectedBranch = "feature/m5.2-autonomous-execution-engine"
$CurrentBranch = git branch --show-current

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read the current branch."
}

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.2 architecture must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$DocsRoot = "docs\autonomous_execution"

Write-Utf8NoBom "$DocsRoot\ARCHITECTURE.md" @'
# Aerion Forge M5.2 — Autonomous Execution Engine Architecture

## Status

Architecture Draft

## Purpose

M5.2 converts the governed M5.1 autonomous-runtime control plane into a bounded execution engine that can execute approved engineering mission steps without unrestricted autonomy.

## Architectural Boundary

M5.2 may:

- execute one approved step at a time;
- invoke registered tools through a controlled gateway;
- create and verify checkpoints;
- collect structured execution evidence;
- stop, retry, replan, roll back, pause, or escalate;
- persist execution state and events;
- support dry-run and simulation modes.

M5.2 may not:

- bypass M5.1 authority checks;
- execute arbitrary shell commands;
- mutate files outside approved scope;
- push, merge, deploy, release, or migrate without explicit approval;
- run unbounded autonomous loops;
- conceal tool inputs, outputs, or affected files.

## Core Components

1. Execution Request
2. Step Eligibility Evaluator
3. Execution Lease Manager
4. Controlled Tool Gateway
5. Tool Registry
6. Step Executor
7. Evidence Collector
8. Checkpoint Coordinator
9. Execution Journal
10. Failure Classifier
11. Recovery Coordinator
12. Autonomous Execution Service
13. Read-only CLI and reporting

## Execution Flow

```text
MISSION APPROVED
  -> STEP SELECTED
  -> ELIGIBILITY CHECKED
  -> AUTHORITY CHECKED
  -> APPROVAL CHECKED
  -> EXECUTION LEASE ACQUIRED
  -> CHECKPOINT VERIFIED
  -> TOOL INVOCATION PREPARED
  -> TOOL EXECUTED
  -> EFFECTS VERIFIED
  -> EVIDENCE RECORDED
  -> STEP COMPLETED OR RECOVERY SELECTED
```

## Safety Principles

- Single active writer per mission repository.
- One tool invocation at a time.
- Every mutation has an approved scope.
- Every mutating step requires a verified checkpoint.
- Every tool invocation has a deterministic identifier.
- Every result records affected files and evidence.
- Every retry consumes a finite budget.
- Every failure maps to an explicit recovery decision.
- Execution is offline by default.
- Dry-run is the default mode for CLI operations.
'@

Write-Utf8NoBom "$DocsRoot\SPECIFICATION.md" @'
# M5.2 Autonomous Execution Engine Specification

## Functional Requirements

- Select the next eligible mission step deterministically.
- Reject steps with unmet dependencies.
- Reject actions exceeding granted authority.
- Reject high-risk actions without valid approval.
- Acquire a single-writer execution lease.
- Require a verified checkpoint before mutation.
- Resolve tools only from a registered allowlist.
- Validate tool arguments before invocation.
- Capture start time, end time, exit status, outputs, and affected files.
- Compare actual effects against approved scope.
- Emit ordered execution events.
- Persist execution evidence.
- Classify failures.
- Apply bounded retry, rollback, replan, pause, escalation, or abort decisions.
- Support simulation without mutation.
- Support inspection and reporting.

## Non-Functional Requirements

- Deterministic decisions
- Immutable evidence
- Typed errors
- Bounded execution
- Restart-safe state
- Secret redaction
- Auditability
- Testability
- No unrestricted shell
- No hidden repository mutation
'@

Write-Utf8NoBom "$DocsRoot\DATA_MODEL.md" @'
# M5.2 Autonomous Execution Data Model

## Core Models

### ExecutionRequest

- request_id
- mission_id
- plan_id
- step_id
- repository_root
- dry_run
- requested_by
- created_at

### ExecutionLease

- lease_id
- mission_id
- repository_root
- holder
- acquired_at
- expires_at
- released_at
- version

### ToolDefinition

- tool_name
- action_kinds
- authority_required
- risk_class
- mutates_repository
- requires_checkpoint
- argument_schema
- timeout_seconds

### ToolExecutionRequest

- invocation_id
- mission_id
- step_id
- tool_name
- action_kind
- arguments
- approved_scope
- checkpoint_id
- approval_id
- dry_run

### ToolExecutionResult

- invocation_id
- status
- exit_code
- stdout_reference
- stderr_reference
- affected_files
- result_digest
- started_at
- completed_at

### StepExecutionRecord

- execution_id
- mission_id
- step_id
- attempt_number
- lease_id
- checkpoint_id
- invocation_ids
- evidence_ids
- status
- failure_class
- started_at
- completed_at

## Invariants

- One active lease per repository.
- One active step execution per mission.
- Mutating tools require verified checkpoints.
- Actual affected files must remain inside approved scope.
- Tool execution records are immutable.
- Completed executions require evidence.
'@

Write-Utf8NoBom "$DocsRoot\STATE_MACHINE.md" @'
# M5.2 Step Execution State Machine

```text
PENDING
  -> ELIGIBILITY_CHECK
  -> READY
  -> LEASE_ACQUIRING
  -> CHECKPOINT_VERIFYING
  -> TOOL_PREPARING
  -> TOOL_RUNNING
  -> EFFECT_VERIFYING
  -> EVIDENCE_RECORDING
  -> SUCCEEDED
```

Failure and control states:

```text
BLOCKED
AWAITING_APPROVAL
RETRY_PENDING
ROLLBACK_PENDING
ROLLED_BACK
PAUSED
ESCALATED
FAILED
CANCELLED
```

Terminal execution states:

- SUCCEEDED
- FAILED
- CANCELLED

No terminal execution may resume.
'@

Write-Utf8NoBom "$DocsRoot\TOOL_GATEWAY.md" @'
# M5.2 Controlled Tool Gateway

## Responsibilities

- Resolve tools from an explicit registry.
- Validate action kind.
- Validate required authority.
- Validate approval requirement.
- Validate checkpoint requirement.
- Validate arguments.
- Enforce timeout.
- Redact secrets.
- Record invocation metadata.
- Capture affected files.
- Reject out-of-scope effects.

## Prohibited Behavior

- Arbitrary command passthrough
- Dynamic import of unknown tools
- Network access by default
- Shell expansion without explicit contract
- Unrecorded filesystem mutation
- Silent retries
'@

Write-Utf8NoBom "$DocsRoot\FAILURE_MODEL.md" @'
# M5.2 Failure Model

## Failure Classes

- eligibility_failure
- dependency_failure
- authority_failure
- approval_failure
- lease_failure
- checkpoint_failure
- tool_resolution_failure
- argument_validation_failure
- tool_timeout
- tool_exit_failure
- scope_violation
- evidence_failure
- invariant_violation
- rollback_failure

## Recovery Mapping

- Retryable transient tool failures may retry within budget.
- Scope violations immediately stop execution and escalate.
- Authority and approval failures never auto-retry.
- Checkpoint failures block mutation.
- Rollback failure escalates.
- Exhausted budgets abort.
'@

Write-Utf8NoBom "$DocsRoot\ACCEPTANCE_CRITERIA.md" @'
# M5.2 Acceptance Criteria

M5.2 is complete only when:

- [ ] Step eligibility is deterministic.
- [ ] Dependencies are enforced.
- [ ] Single-writer execution leases are enforced.
- [ ] Tool registry rejects unknown tools.
- [ ] Tool arguments are validated.
- [ ] Authority is checked before every invocation.
- [ ] Approval is checked where required.
- [ ] Mutations require verified checkpoints.
- [ ] Actual effects are checked against approved scope.
- [ ] Tool results are immutable.
- [ ] Execution evidence is persisted.
- [ ] Failures are classified.
- [ ] Retry and recovery remain bounded.
- [ ] Dry-run mode performs no mutation.
- [ ] CLI defaults to read-only simulation.
- [ ] Ruff passes.
- [ ] MyPy passes.
- [ ] M5.2 focused tests pass.
- [ ] Full repository tests pass.
'@

Write-Utf8NoBom "$DocsRoot\DECISIONS.md" @'
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
'@

$RequiredFiles = @(
    "ARCHITECTURE.md",
    "SPECIFICATION.md",
    "DATA_MODEL.md",
    "STATE_MACHINE.md",
    "TOOL_GATEWAY.md",
    "FAILURE_MODEL.md",
    "ACCEPTANCE_CRITERIA.md",
    "DECISIONS.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $DocsRoot $File

    if (-not (Test-Path $Path)) {
        throw "Missing M5.2 architecture document: $Path"
    }

    if ((Get-Item $Path).Length -lt 300) {
        throw "M5.2 architecture document is unexpectedly small: $Path"
    }

    $Content = Get-Content $Path -Raw

    if ($Content -match "_To be completed\._") {
        throw "Placeholder remains in M5.2 architecture document: $Path"
    }
}

Write-Host ""
Write-Host "M5.2 ARCHITECTURE DOCUMENTS WRITTEN AND CHECKED" -ForegroundColor Green

Get-ChildItem $DocsRoot |
    Sort-Object Name |
    Select-Object Name, Length |
    Format-Table -AutoSize