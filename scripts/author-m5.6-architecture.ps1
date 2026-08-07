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

$AllowedBranches = @(
    "feature/m5.6-autonomous-planning-engine",
    "feature/m5.7-autonomous-execution-engine",
    "feature/m5.8-autonomous-agent-runtime"
)

$CurrentBranch = git branch --show-current

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read current branch."
}

if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.6 architecture reconstruction must run on an M5.6+ autonomous branch. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "docs\autonomous_planning\ARCHITECTURE.md" @'
# M5.6 Autonomous Planning Engine Architecture

## Purpose

M5.6 converts an engineering objective into a deterministic, validated, dependency-aware engineering plan that can later be approved and executed by M5.7.

M5.6 is a planning subsystem. It does not directly edit source files, execute tools, perform Git operations, or bypass approval controls.

## Architectural Position

Inputs:

- repository root and repository fingerprint;
- engineering objective;
- planning intent;
- repository-grounded capabilities;
- architecture and operational constraints;
- evidence and memory references.

Outputs:

- immutable planning request;
- immutable planning plan;
- ordered planning steps;
- dependency graph;
- risk and approval requirements;
- validation findings;
- approved/rejected plan lifecycle state.

## Core Components

1. Planning contracts
2. Deterministic identifiers
3. Planning state model
4. Planning policy
5. Repository/context analysis
6. Step synthesis
7. Dependency synthesis
8. Dependency graph and cycle detection
9. Ordering and eligibility
10. Plan generation
11. Plan validation
12. Approval and revision
13. Planning repository
14. Planning service
15. Reporting and CLI integration

## Safety Boundary

M5.6 may describe code-changing, release, migration, test, validation, documentation, and approval work, but it may not execute that work.

Destructive steps must carry an explicit approval requirement.

Plans with blocking validation findings are not executable.

## Determinism

For identical planning request and planning context, M5.6 must produce deterministic:

- request identifiers;
- plan identifiers;
- step identifiers;
- dependency identifiers;
- dependency ordering;
- risk classification;
- approval requirements;
- validation findings.

## Compatibility

M5.6 must preserve existing Forge repository understanding, capability, memory, decision, orchestration, and tool-safety contracts.

M5.7 consumes approved M5.6 plans as its source of executable work.
'@

Write-Utf8NoBom "docs\autonomous_planning\SPECIFICATION.md" @'
# M5.6 Autonomous Planning Specification

The planning engine shall:

1. accept a repository-grounded engineering objective;
2. classify the planning intent;
3. bind planning to one repository root;
4. accept explicit target paths and constraints;
5. consume only known/registered capabilities;
6. synthesize ordered planning steps;
7. synthesize explicit step dependencies;
8. reject cyclic dependency graphs;
9. assign risk to plans and individual steps;
10. require explicit approval for destructive work;
11. validate generated plans before readiness;
12. allow approval, rejection, and bounded revision;
13. persist planning sessions and plan versions through an explicit repository;
14. expose deterministic reporting and CLI behavior;
15. remain execution-free;
16. pass Ruff, MyPy, focused tests, and the full repository suite.
'@

Write-Utf8NoBom "docs\autonomous_planning\DATA_MODEL.md" @'
# M5.6 Autonomous Planning Data Model

## PlanningRequest

Immutable request describing:

- request ID;
- objective;
- repository root;
- intent;
- target paths;
- constraints;
- acceptance criteria;
- requested capabilities;
- creator;
- creation timestamp.

## PlanningStep

Immutable unit of planned engineering work.

Fields include:

- step ID;
- sequence;
- name and description;
- step kind;
- target paths;
- required capabilities;
- required tools;
- expected outputs;
- acceptance criteria;
- risk;
- approval requirement;
- destructive flag.

## PlanningDependency

Explicit relation between two planning steps.

Supported dependency kinds:

- requires;
- blocks;
- orders_after;
- optional.

Self-dependencies are invalid.

## PlanningPlan

Immutable versioned plan containing:

- plan ID;
- request ID;
- version;
- planning state;
- summary;
- ordered steps;
- dependencies;
- aggregate risk;
- approval requirement;
- warnings;
- timestamps.

A plan must contain at least one step, unique step identifiers, sequence-ordered steps, and dependencies referencing known steps.

## PlanningSession

Tracks request state, current plan identity/version, failure reason, and timestamps.

## PlanningValidationFinding

Records severity, code, message, optional step reference, and blocking status.

## PlanningValidationResult

A valid plan may not contain blocking findings.
'@

Write-Utf8NoBom "docs\autonomous_planning\STATE_MACHINE.md" @'
# M5.6 Planning State Machine

Planning states:

- created
- analysing
- generating
- validating
- awaiting_approval
- approved
- rejected
- ready
- failed
- cancelled

Typical lifecycle:

created
→ analysing
→ generating
→ validating
→ awaiting_approval or ready
→ approved
→ ready

Alternative terminal paths:

- rejected
- failed
- cancelled

State changes must occur through explicit planning services and must preserve plan/session traceability.
'@

Write-Utf8NoBom "docs\autonomous_planning\INTENT_AND_STEP_MODEL.md" @'
# M5.6 Intent and Step Model

## Planning Intents

M5.6 supports:

- implement_feature
- fix_defect
- refactor
- migrate
- validate
- investigate
- document
- release

## Step Kinds

M5.6 supports:

- analysis
- code_change
- test
- validation
- documentation
- approval
- release

The planning intent describes the mission-level engineering objective.

Step kinds describe the planned units needed to satisfy that objective.

A planning plan may combine multiple step kinds under one intent.
'@

Write-Utf8NoBom "docs\autonomous_planning\DEPENDENCY_MODEL.md" @'
# M5.6 Dependency Model

Planning dependencies are explicit and directional.

Supported kinds:

- requires
- blocks
- orders_after
- optional

The dependency subsystem shall:

1. preserve step traceability;
2. reject self-dependencies;
3. reject references to unknown steps;
4. detect dependency cycles;
5. produce deterministic ordering;
6. expose eligibility based on prerequisite completion;
7. prevent execution consumers from treating blocked steps as ready.

M5.7 must preserve these dependency relationships when projecting a plan into an execution run.
'@

Write-Utf8NoBom "docs\autonomous_planning\APPROVAL_AND_RISK_MODEL.md" @'
# M5.6 Approval and Risk Model

## Planning Risk

Supported levels:

- low
- medium
- high
- critical

Risk may be assigned at both plan and step level.

## Approval Requirements

Supported approval requirements:

- none
- plan
- code
- release

Destructive steps cannot use `none`.

A plan may also carry an aggregate `requires_approval` flag.

M5.6 records approval requirements but does not grant authority to execute. Execution authority is enforced downstream by M5.7 and the mission runtime.
'@

Write-Utf8NoBom "docs\autonomous_planning\VALIDATION_MODEL.md" @'
# M5.6 Validation Model

Plan validation shall detect at minimum:

- invalid contracts;
- empty plans;
- duplicate step identifiers;
- invalid step ordering;
- unknown dependency references;
- dependency cycles;
- destructive steps without approval;
- capability mismatches;
- blocking policy findings.

Validation output consists of:

- plan ID;
- valid flag;
- validation findings;
- finding severity;
- finding code;
- message;
- optional step reference;
- blocking flag.

A plan marked valid may not contain blocking findings.
'@

Write-Utf8NoBom "docs\autonomous_planning\ACCEPTANCE_CRITERIA.md" @'
# M5.6 Acceptance Criteria

M5.6 is complete when:

1. planning request, plan, step, dependency, session, and validation contracts exist;
2. deterministic identifiers exist;
3. planning state and intent models exist;
4. dependency graph construction exists;
5. cycle detection exists;
6. deterministic ordering and eligibility exist;
7. step and dependency synthesis exist;
8. plan generation exists;
9. plan validation exists;
10. approval and revision controls exist;
11. planning persistence/repository exists;
12. planning service exists;
13. reporting and CLI integration exist;
14. Ruff passes;
15. MyPy passes;
16. focused M5.6 tests pass;
17. the full repository regression suite passes;
18. M5.7 can consume approved plans without redefining planning contracts.
'@

Write-Utf8NoBom "docs\autonomous_planning\DECISIONS.md" @'
# M5.6 Architecture Decisions

## AD-1

M5.6 plans engineering work but never executes tools or edits repositories directly.

## AD-2

Planning contracts are immutable and versioned.

## AD-3

Planning identifiers and ordering are deterministic.

## AD-4

Dependencies are explicit graph edges rather than implicit sequence assumptions.

## AD-5

Destructive work requires explicit approval.

## AD-6

Validation is mandatory before a plan can become executable.

## AD-7

M5.7 is the execution consumer of approved M5.6 plans.

## AD-8

Repository, memory, capability, and architecture context are inputs to planning rather than duplicated planning-owned subsystems.
'@

$Required = @(
    ".\docs\autonomous_planning\ARCHITECTURE.md",
    ".\docs\autonomous_planning\SPECIFICATION.md",
    ".\docs\autonomous_planning\DATA_MODEL.md",
    ".\docs\autonomous_planning\STATE_MACHINE.md",
    ".\docs\autonomous_planning\INTENT_AND_STEP_MODEL.md",
    ".\docs\autonomous_planning\DEPENDENCY_MODEL.md",
    ".\docs\autonomous_planning\APPROVAL_AND_RISK_MODEL.md",
    ".\docs\autonomous_planning\VALIDATION_MODEL.md",
    ".\docs\autonomous_planning\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_planning\DECISIONS.md"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.6 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -lt 200) {
        throw "M5.6 architecture file is unexpectedly small: $Path"
    }
}

$States = Get-Content ".\forge\autonomous_planning\states.py" -Raw
$Models = Get-Content ".\forge\autonomous_planning\models.py" -Raw

foreach ($RequiredState in @(
    "IMPLEMENT_FEATURE",
    "FIX_DEFECT",
    "REFACTOR",
    "MIGRATE",
    "VALIDATE",
    "INVESTIGATE",
    "DOCUMENT",
    "RELEASE",
    "CODE_CHANGE",
    "ApprovalRequirement"
)) {
    if ($States -notmatch [regex]::Escape($RequiredState)) {
        throw "Current M5.6 implementation does not contain expected planning contract: $RequiredState"
    }
}

foreach ($RequiredModel in @(
    "class PlanningRequest",
    "class PlanningStep",
    "class PlanningDependency",
    "class PlanningPlan",
    "class PlanningSession",
    "class PlanningValidationResult"
)) {
    if ($Models -notmatch [regex]::Escape($RequiredModel)) {
        throw "Current M5.6 implementation does not contain expected model: $RequiredModel"
    }
}

Write-Host ""
Write-Host "M5.6 ARCHITECTURE DOCUMENTS RECONSTRUCTED AND CHECKED" `
    -ForegroundColor Green

Write-Host ""
Write-Host "NOTE: This script reconstructs missing M5.6 architecture documentation" `
    -ForegroundColor Yellow
Write-Host "from the already-implemented M5.6 contracts; it does not modify M5.6 code." `
    -ForegroundColor Yellow

Get-ChildItem ".\docs\autonomous_planning" -File |
    Sort-Object Name |
    Select-Object Name, Length
