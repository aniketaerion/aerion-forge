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

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read current branch."
}

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 architecture must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "docs\mission_runtime\ARCHITECTURE.md" @'
# M5.8 Forge Mission Runtime Architecture

## Purpose

M5.8 integrates the existing Forge platform into one controlled end-to-end software engineering mission runtime.

It does not create another planning engine, execution engine, memory system, or multi-agent platform.

Its purpose is to connect:

- repository understanding;
- project and technology detection;
- capability selection;
- engineering memory;
- autonomous planning;
- human approval;
- controlled execution;
- build and verification;
- recovery and retry;
- documentation and review generation;
- final human approval.

## Product Boundary

Forge remains a general-purpose software engineering platform.

ERP is the first production proving ground, but M5.8 must support any repository for which Forge has suitable technology and domain capabilities, including:

- ERP;
- CRM;
- websites and web services;
- Flutter applications;
- GCS software;
- PX4 and ROS2 projects;
- embedded and firmware projects.

## Architectural Position

M5.8 sits above existing Forge capabilities.

Inputs:

- workspace and repository context;
- natural-language mission;
- project index and knowledge graph;
- capability registry;
- domain intelligence;
- M5.5 memory context;
- M5.6 approved planning output;
- M5.7 execution output;
- human approval decisions.

Outputs:

- mission session;
- mission state transitions;
- approved engineering plan;
- controlled execution run;
- validation evidence;
- recovery decisions;
- documentation updates;
- review package;
- final mission report.

## Components

1. Mission contracts
2. Mission state machine
3. Mission/session repository
4. Project and capability context adapter
5. Memory context adapter
6. Planning adapter
7. Approval gateway
8. Execution adapter
9. Verification adapter
10. Recovery controller
11. Mission loop
12. Reporting and CLI integration

## Execution Flow

1. Accept mission.
2. Resolve workspace and repository.
3. Understand repository.
4. Detect technologies and domain.
5. Load required capabilities.
6. Retrieve relevant memory and knowledge.
7. Generate engineering plan.
8. Validate risk and dependencies.
9. Pause for human approval when required.
10. Execute approved work through M5.7.
11. Run build and verification.
12. Diagnose and recover within authority.
13. Update documentation.
14. Generate evidence and review package.
15. Pause for final human approval.
16. Complete mission.

## Safety Boundary

M5.8 may orchestrate only existing governed subsystems.

It may not:

- bypass approval requirements;
- bypass the controlled tool gateway;
- perform unrestricted Git operations;
- perform destructive actions without explicit authority;
- invent capabilities that are not registered;
- modify repositories outside the active workspace;
- continue after a blocking validation failure.

## Determinism

For identical mission input and repository state, M5.8 shall produce deterministic:

- identifiers;
- context selection;
- state transitions;
- plan references;
- execution references;
- approval requirements;
- completion reports.

## Deferred to Forge v2

The following are explicitly out of scope:

- multi-agent coordination;
- autonomous agent marketplace;
- cloud mission synchronization;
- self-modifying Forge;
- unrestricted long-running autonomy;
- business process automation unrelated to software engineering;
- team collaboration platform;
- general AI research features.
'@

Write-Utf8NoBom "docs\mission_runtime\SPECIFICATION.md" @'
# M5.8 Mission Runtime Specification

The Forge Mission Runtime shall:

1. accept a natural-language engineering mission;
2. bind the mission to one active workspace and repository;
3. use existing repository understanding and capability discovery;
4. retrieve relevant M5.5 memory;
5. invoke M5.6 planning without reimplementing planning;
6. enforce human approval before high-risk execution;
7. invoke M5.7 execution without bypassing its authority model;
8. run project-specific verification;
9. support bounded recovery and retry;
10. stop safely on blocking failure;
11. generate evidence, documentation, and a review package;
12. request final approval before merge-worthy completion;
13. support multiple project types through registered capabilities;
14. expose deterministic CLI and reports;
15. pass architecture, Ruff, MyPy, focused, integration, and full-suite validation.
'@

Write-Utf8NoBom "docs\mission_runtime\DATA_MODEL.md" @'
# M5.8 Mission Runtime Data Model

## MissionRequest

Represents the user instruction and repository scope.

Fields include:

- mission request ID;
- workspace ID;
- repository root;
- mission statement;
- requested by;
- risk tolerance;
- approval policy;
- created timestamp.

## MissionSession

Represents one end-to-end engineering mission.

Fields include:

- session ID;
- request ID;
- state;
- repository fingerprint;
- detected technologies;
- selected capabilities;
- memory query references;
- planning request and plan references;
- approval references;
- execution run references;
- verification references;
- review package reference;
- failure reason;
- timestamps.

## MissionCheckpoint

Records resumable mission progress.

## MissionApproval

Records planning or final approval decisions.

## MissionEvidence

Aggregates evidence from understanding, planning, execution, verification, documentation, and review.

## MissionResult

Represents terminal mission outcome.
'@

Write-Utf8NoBom "docs\mission_runtime\STATE_MACHINE.md" @'
# M5.8 Mission State Machine

Mission states:

- created
- resolving_workspace
- understanding_repository
- selecting_capabilities
- retrieving_context
- planning
- validating_plan
- awaiting_plan_approval
- approved
- executing
- verifying
- recovering
- documenting
- generating_review
- awaiting_final_approval
- completed
- failed
- cancelled
- paused

Terminal states:

- completed
- failed
- cancelled

Invalid transitions must raise explicit mission state errors.

The runtime must support safe pause and resume from approved checkpoints.
'@

Write-Utf8NoBom "docs\mission_runtime\INTEGRATION_MODEL.md" @'
# M5.8 Integration Model

## Existing Forge Core

M5.8 consumes:

- workspace management;
- repository discovery;
- indexing;
- knowledge graph;
- capability registry;
- domain intelligence;
- safe change planning;
- safe code editing;
- build verification;
- Git and review package capabilities;
- documentation generation.

## M5.5 Memory

M5.8 retrieves relevant context and may persist validated mission lessons.

It does not reimplement memory storage or learning.

## M5.6 Planning

M5.8 invokes `AutonomousPlanningService` to create, validate, approve, or reject plans.

It does not synthesize a second planning model.

## M5.7 Execution

M5.8 invokes `AutonomousExecutionService` to register and execute controlled runs.

It does not bypass execution authority, evidence, retry, or recovery controls.

## Project and Domain Capabilities

M5.8 selects capabilities based on detected project technologies and domain.

Examples:

- React, Node, PostgreSQL and ERP capabilities;
- CRM and web-service capabilities;
- Flutter and Dart capabilities;
- C++, Qt, MAVLink, PX4 and ROS2 capabilities;
- embedded C/C++, CMake and firmware capabilities.
'@

Write-Utf8NoBom "docs\mission_runtime\APPROVAL_MODEL.md" @'
# M5.8 Approval Model

M5.8 has two primary approval gates.

## Plan Approval

Required before execution when:

- the plan is high risk;
- the plan includes destructive changes;
- the plan includes migrations;
- the plan affects authentication, finance, infrastructure, credentials, release, or production systems;
- policy explicitly requires approval.

## Final Approval

Required before:

- merge-worthy completion;
- local commit where policy requires approval;
- release or deployment;
- destructive cleanup;
- externally visible publication.

Approval decisions must include:

- approver;
- decision;
- rationale;
- scope;
- timestamp;
- related mission and plan references.
'@

Write-Utf8NoBom "docs\mission_runtime\CAPABILITY_MODEL.md" @'
# M5.8 Capability Selection Model

M5.8 shall use repository evidence to determine required engineering capabilities.

Selection inputs include:

- detected languages;
- package managers;
- build systems;
- frameworks;
- database technologies;
- API styles;
- domain markers;
- repository configuration;
- test infrastructure.

Capability selection must be:

- repository-grounded;
- deterministic;
- explainable;
- limited to registered capabilities;
- recorded in mission evidence.

M5.8 must fail safely when required capabilities are unavailable.
'@

Write-Utf8NoBom "docs\mission_runtime\VERIFICATION_MODEL.md" @'
# M5.8 Verification Model

Verification must use the actual project toolchain.

Examples include:

- Python: Ruff, MyPy, Pytest;
- React/Node: lint, type checking, unit tests, build;
- PostgreSQL: migration and schema validation;
- Flutter: analyzer, tests, build checks;
- C/C++: compiler, CMake, unit tests;
- PX4: SITL and PX4 test tooling where configured;
- ROS2: colcon build and test where configured;
- embedded: compiler, static analysis, unit or hardware-in-loop checks where available.

A mission cannot complete unless required verification passes or an approved exception is recorded.
'@

Write-Utf8NoBom "docs\mission_runtime\RECOVERY_MODEL.md" @'
# M5.8 Recovery Model

M5.8 coordinates existing recovery capabilities.

Permitted actions:

- retry within bounded policy;
- return to planning;
- request revised approval;
- restore checkpoint;
- rollback through existing rollback capability;
- pause for human intervention;
- abort safely.

Recovery must never expand mission scope without approval.

Repeated failure beyond configured limits must terminate or pause the mission.
'@

Write-Utf8NoBom "docs\mission_runtime\ACCEPTANCE_CRITERIA.md" @'
# M5.8 Acceptance Criteria

M5.8 is complete when:

1. mission contracts and state machine are implemented;
2. workspace and repository context are integrated;
3. capability selection is implemented;
4. M5.5 memory is integrated;
5. M5.6 planning is integrated;
6. human plan approval is enforced;
7. M5.7 execution is integrated;
8. real project verification is integrated;
9. bounded recovery is implemented;
10. documentation and review generation are integrated;
11. final approval is enforced;
12. CLI and reporting are implemented;
13. architecture validation passes;
14. Ruff passes;
15. MyPy passes;
16. focused and integration tests pass;
17. the full repository suite passes;
18. a bounded mission against a real external Aerion repository is demonstrated before v1.0 release.
'@

Write-Utf8NoBom "docs\mission_runtime\DECISIONS.md" @'
# M5.8 Architecture Decisions

## AD-1

M5.8 is the Forge Mission Runtime, not a new planning or execution engine.

## AD-2

Forge remains general-purpose; ERP is the first production proving ground.

## AD-3

M5.8 consumes M5.5, M5.6, and M5.7 through explicit adapters.

## AD-4

Human approval is mandatory at plan and final review gates where policy requires it.

## AD-5

Capability selection is repository-grounded and limited to registered capabilities.

## AD-6

The runtime may not bypass controlled execution, verification, recovery, or Git safety boundaries.

## AD-7

Multi-agent orchestration and research-oriented autonomy are deferred to Forge v2.

## AD-8

M5.8 completion does not itself constitute Forge v1.0 release; a real-project acceptance mission is required.
'@

$RequiredFiles = @(
    ".\docs\mission_runtime\ARCHITECTURE.md",
    ".\docs\mission_runtime\SPECIFICATION.md",
    ".\docs\mission_runtime\DATA_MODEL.md",
    ".\docs\mission_runtime\STATE_MACHINE.md",
    ".\docs\mission_runtime\INTEGRATION_MODEL.md",
    ".\docs\mission_runtime\APPROVAL_MODEL.md",
    ".\docs\mission_runtime\CAPABILITY_MODEL.md",
    ".\docs\mission_runtime\VERIFICATION_MODEL.md",
    ".\docs\mission_runtime\RECOVERY_MODEL.md",
    ".\docs\mission_runtime\ACCEPTANCE_CRITERIA.md",
    ".\docs\mission_runtime\DECISIONS.md"
)

foreach ($Path in $RequiredFiles) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.8 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -lt 200) {
        throw "M5.8 architecture file is unexpectedly small: $Path"
    }
}

Write-Host ""
Write-Host "M5.8 MISSION RUNTIME ARCHITECTURE WRITTEN AND CHECKED" `
    -ForegroundColor Green

Get-ChildItem ".\docs\mission_runtime" -File |
    Sort-Object Name |
    Select-Object Name, Length
