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

$ExpectedBranch = "feature/m5.7-autonomous-execution-engine"
$CurrentBranch = git branch --show-current

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read current branch."
}

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.7 architecture must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "docs\autonomous_execution_v2\ARCHITECTURE.md" @'
# M5.7 Autonomous Execution Engine Architecture

## Purpose

M5.7 converts validated autonomous plans into governed execution runs. It does not replace the M5.2 tool gateway or M5.3 mission orchestrator. It coordinates them through explicit execution contracts, policy checks, leases, evidence, recovery, and completion reporting.

## Architectural Position

Inputs:

- approved M5.6 planning plans;
- M5.4 decision outputs;
- M5.5 memory context;
- M5.3 orchestration sessions;
- M5.2 controlled tool execution.

Outputs:

- immutable execution runs;
- step attempts;
- evidence records;
- recovery decisions;
- execution reports;
- validated completion state.

## Components

1. Execution contracts
2. Run lifecycle
3. Step scheduler
4. Execution coordinator
5. Policy and authority checks
6. Attempt journal
7. Evidence capture
8. Retry and recovery controller
9. Completion validator
10. CLI and reporting integration

## Safety Boundary

The engine may execute only approved planning steps. Every tool invocation must pass through the existing controlled tool gateway. Destructive execution remains forbidden unless policy and authority explicitly allow it.

## Determinism

Identifiers, ordering, dependency evaluation, retry decisions, and reports must be deterministic for identical inputs.

## Compatibility

M5.7 must preserve all existing M5.1-M5.6 contracts and CLI namespaces.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\SPECIFICATION.md" @'
# M5.7 Specification

The autonomous execution engine shall:

1. accept only validated, executable planning plans;
2. create immutable execution runs;
3. preserve plan and step traceability;
4. evaluate dependencies before scheduling;
5. enforce authority and policy checks;
6. record every attempt and state transition;
7. capture evidence for each completed step;
8. support bounded retries and governed recovery;
9. stop safely on blocking failure;
10. produce deterministic reports;
11. expose a non-conflicting CLI namespace;
12. pass Ruff, MyPy, focused tests, and the full repository suite.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\DATA_MODEL.md" @'
# M5.7 Data Model

## ExecutionRequest

Links an approved planning plan to an execution run.

## ExecutionRun

Tracks run identity, plan identity, lifecycle state, risk, current step, timestamps, failure reason, and completion summary.

## ExecutionStep

Represents the executable projection of a planning step.

## ExecutionAttempt

Represents one bounded attempt to execute one step.

## ExecutionDependency

Preserves the prerequisite relation from the planning plan.

## ExecutionEvidence

Stores references proving the observed effect of an attempt.

## RecoveryDecision

Records retry, skip, rollback, pause, or abort decisions.

## ExecutionValidationResult

Records completion checks and blocking findings.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\STATE_MACHINE.md" @'
# M5.7 State Machine

Execution run states:

- created
- validating
- ready
- running
- paused
- recovering
- awaiting_approval
- succeeded
- failed
- cancelled

Step states:

- pending
- eligible
- running
- succeeded
- failed
- skipped
- blocked
- cancelled

Invalid transitions must raise explicit execution state errors.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\AUTHORITY_MODEL.md" @'
# M5.7 Authority Model

Execution requires:

- an approved or approval-exempt plan;
- repository scope match;
- permitted capability;
- permitted tool;
- acceptable risk;
- valid authority token where required.

High-risk, destructive, release, credential, infrastructure, and production actions require explicit approval. M5.7 may never bypass the M5.1 authority model or M5.2 tool gateway.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\RECOVERY_MODEL.md" @'
# M5.7 Recovery Model

Recovery actions:

- retry with bounded count;
- pause for approval;
- skip only when policy permits;
- rollback using an existing checkpoint;
- replan through M5.6;
- abort safely.

Recovery decisions must be deterministic, journaled, evidence-backed, and policy constrained.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\EVIDENCE_MODEL.md" @'
# M5.7 Evidence Model

Evidence shall include:

- execution ID;
- step ID;
- attempt ID;
- tool invocation references;
- observed outputs;
- validation results;
- timestamps;
- repository fingerprint;
- before and after references where available.

A step cannot be considered complete without required evidence.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\ACCEPTANCE_CRITERIA.md" @'
# M5.7 Acceptance Criteria

M5.7 is complete when:

1. execution contracts are implemented;
2. dependency-aware scheduling is implemented;
3. controlled execution is integrated;
4. attempt journaling and evidence capture are implemented;
5. recovery and retry controls are implemented;
6. reporting and CLI integration are implemented;
7. architecture validation passes;
8. Ruff passes;
9. MyPy passes;
10. focused M5.7 tests pass;
11. the full repository suite passes;
12. prior milestone behaviour remains compatible.
'@

Write-Utf8NoBom "docs\autonomous_execution_v2\DECISIONS.md" @'
# M5.7 Architecture Decisions

## AD-1

M5.7 orchestrates execution but does not bypass M5.2 controlled tool execution.

## AD-2

Approved M5.6 plans are the only executable source of work.

## AD-3

Execution state and attempts are immutable records updated through explicit services.

## AD-4

Retries are bounded and policy controlled.

## AD-5

Evidence is mandatory for successful completion.

## AD-6

The CLI namespace shall be `autonomous-execution-v2` to avoid collision with the existing autonomous execution CLI.
'@

$Required = @(
    ".\docs\autonomous_execution_v2\ARCHITECTURE.md",
    ".\docs\autonomous_execution_v2\SPECIFICATION.md",
    ".\docs\autonomous_execution_v2\DATA_MODEL.md",
    ".\docs\autonomous_execution_v2\STATE_MACHINE.md",
    ".\docs\autonomous_execution_v2\AUTHORITY_MODEL.md",
    ".\docs\autonomous_execution_v2\RECOVERY_MODEL.md",
    ".\docs\autonomous_execution_v2\EVIDENCE_MODEL.md",
    ".\docs\autonomous_execution_v2\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_execution_v2\DECISIONS.md"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) {
        throw "Missing architecture file: $Path"
    }

    if ((Get-Item $Path).Length -lt 200) {
        throw "Architecture file too small: $Path"
    }
}

Write-Host ""
Write-Host "M5.7 ARCHITECTURE DOCUMENTS WRITTEN AND CHECKED" -ForegroundColor Green

Get-ChildItem ".\docs\autonomous_execution_v2" -File |
    Sort-Object Name |
    Select-Object Name, Length
