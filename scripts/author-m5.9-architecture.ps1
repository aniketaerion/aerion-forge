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

$ExpectedBranch = "feature/m5.9-general-engineering-agent"
$CurrentBranch = git branch --show-current
if ($LASTEXITCODE -ne 0) { throw "Unable to read current branch." }
if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.9 architecture must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

git merge-base --is-ancestor forge-v0.2-m5.8 HEAD
if ($LASTEXITCODE -ne 0) {
    throw "M5.9 branch does not contain the forge-v0.2-m5.8 release baseline."
}

git diff --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Tracked working-tree changes exist. Commit or restore them before authoring M5.9 architecture."
}

git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Staged changes exist. Commit or unstage them before authoring M5.9 architecture."
}

Write-Utf8NoBom "docs\general_engineering_agent\ARCHITECTURE.md" @'
# M5.9 General Engineering Agent Architecture

## Purpose

M5.9 extends the production mission runtime proven by M5.8 into a general software-engineering agent capable of handling previously unseen repository-grounded change requests.

M5.9 does not replace M5.8. It adds engineering understanding, repository grounding, general change planning, edit synthesis, multi-file change execution, and bounded repair above the existing governed mission-runtime safety boundary.

## Product Goal

Given a repository and a natural-language software change request that has not been hard-coded into Forge, the General Engineering Agent shall:

1. inspect repository evidence;
2. understand the requested engineering outcome;
3. identify relevant files, symbols, dependencies, tests, and conventions;
4. produce a structured implementation plan;
5. pause at governed approval boundaries;
6. synthesize bounded edit proposals;
7. execute approved changes through Forge-controlled editing;
8. validate the resulting repository;
9. propose bounded repairs when validation fails;
10. complete with auditable evidence.

## Architectural Principle

The reasoning provider proposes. Forge authorizes and executes.

A model or provider may never receive unrestricted authority to mutate repository files, execute arbitrary shell commands, approve its own plan, approve its own edit, approve release, or silently expand mission scope.

## Architectural Position

M5.9 sits above and reuses:

- workspace and repository discovery;
- incremental project index;
- engineering knowledge graph;
- capability registry;
- engineering memory;
- M5.6 planning concepts;
- M5.7 controlled execution concepts;
- M5.8 mission runtime;
- approval boundaries;
- Safe Code Editing;
- build verification;
- bounded recovery;
- evidence and reporting.

## General Engineering Pipeline

1. Accept natural-language objective.
2. Resolve repository and policy scope.
3. Build an EngineeringRequest.
4. Collect RepositoryEvidence.
5. Select relevant files and symbols.
6. Build EngineeringContext.
7. Produce ChangeSpecification.
8. Produce ChangePlan.
9. Pause for PLAN approval when required.
10. Ask an EngineeringProvider for structured edit proposals.
11. Validate paths, fingerprints, scope, and risk.
12. Pause for EDIT approval when required.
13. Execute edits through governed Safe Code Editing services.
14. Run repository-specific validation.
15. If validation fails, create bounded RepairProposal evidence.
16. Enforce repair-attempt limits and approval policy.
17. Re-run verification.
18. Pause for RELEASE approval when required.
19. Complete with EngineeringEvidence and mission evidence.

## Components

1. General engineering contracts
2. Engineering request normalizer
3. Repository evidence collector
4. Relevant-file and symbol selector
5. Engineering context builder
6. Change specification builder
7. General change planner
8. Engineering provider protocol
9. Structured edit synthesizer
10. Change-set validator
11. Multi-file transaction coordinator
12. Validation coordinator
13. Bounded repair coordinator
14. M5.8 production mission-runtime adapter
15. General engineering reporting and evidence

## Authority Boundary

The engineering reasoning layer MAY analyze supplied objectives and repository context, identify candidate files and symbols, propose requirements, plans, edits, validation, diagnoses, and bounded repairs.

The engineering reasoning layer MUST NOT write files directly, execute arbitrary shell commands directly, access files outside approved repository scope, bypass approval policy, expand scope silently, approve its own actions, or continue indefinitely after repeated failure.

## Repository Grounding Requirement

Every file or symbol selected for change must be supported by repository evidence such as path, symbol definition, dependencies, references, tests, project conventions, configuration, build metadata, implementation patterns, and source fingerprints.

A change plan that cannot explain why a target is relevant is invalid.

## Change Planning Boundary

A ChangePlan is structured data, not free-form prose. It must identify objective, requirements, target paths, relevant symbols, intended operations, rationale, risk, dependencies, expected effect, validation plan, and supporting evidence.

## Edit Synthesis Boundary

Generated edits are structured proposals. Initial categories include CREATE_FILE, INSERT, REPLACE, DELETE, and RENAME. An EditOperation remains a proposal until Forge policy and approval permit execution.

## Multi-file Transactions

M5.9 supports bounded coordinated changes across multiple files while preserving approved scope, fingerprints, deterministic ordering, conflict detection, rollback or safe failure semantics, and evidence for each changed path.

## Validation and Repair

Validation uses the repository's real toolchain. Failures produce evidence that may support a RepairProposal. Repair is bounded by policy; the default maximum remains three attempts unless a stricter policy applies. Repeated failure must terminate or pause safely.

## Provider Independence

Core M5.9 contracts must not depend directly on OpenAI, Ollama, or another specific provider. EngineeringProvider adapters remain outside the authority boundary. Provider output is untrusted proposal data until Forge validates it.

## Determinism and Evidence

Provider reasoning may be nondeterministic, but Forge-side identifiers, validation, scope enforcement, state transitions, policy evaluation, approval requirements, transaction records, and evidence serialization must remain deterministic for identical accepted inputs.

## Acceptance Boundary

M5.9 cannot be accepted using only a hard-coded arithmetic objective. Release acceptance must include previously unseen single-file, multi-file, and business-rule/ERP-style tasks, with no task-specific implementation encoded inside Forge.

## Explicitly Deferred

Multi-agent coordination, unrestricted autonomous refactoring, autonomous deployment, browser or desktop automation, unrestricted shell agents, default self-modification, cloud agent swarms, and general AI research features remain out of scope.
'@

Write-Utf8NoBom "docs\general_engineering_agent\SPECIFICATION.md" @'
# M5.9 General Engineering Agent Specification

The General Engineering Agent shall:

1. accept a natural-language engineering objective and repository root;
2. normalize the objective into a validated EngineeringRequest;
3. preserve constraints, acceptance criteria, allowed paths, and forbidden paths;
4. inspect repository evidence before selecting change targets;
5. identify relevant files and symbols using repository-grounded evidence;
6. construct an EngineeringContext with traceable provenance;
7. produce a structured ChangeSpecification and ChangePlan;
8. prevent planning from silently expanding beyond request or policy scope;
9. expose plans for PLAN approval when required;
10. request structured edit proposals through a provider-independent protocol;
11. treat provider output as untrusted proposal data;
12. validate every edit operation before execution;
13. require source fingerprints for destructive or replacement operations where applicable;
14. reject edits outside approved repository scope;
15. reject edits targeting forbidden paths;
16. execute approved mutations only through governed Forge editing services;
17. support bounded coordinated multi-file changes;
18. preserve rollback or safe failure semantics for partial execution;
19. run repository-specific validation after editing;
20. record validation evidence and affected scope;
21. generate bounded repair proposals from validation evidence;
22. enforce configured repair-attempt limits;
23. require REPAIR approval where policy requires it;
24. prevent unbounded correction loops;
25. require RELEASE approval where policy requires it;
26. record end-to-end EngineeringEvidence;
27. support deterministic fake-provider testing;
28. avoid provider-specific dependencies in core contracts;
29. avoid acceptance-task-specific logic in Forge implementation;
30. pass architecture, Ruff, MyPy, focused, integration, real-project, and full-suite validation.

## Functional Input

A request may contain objective, repository root, constraints, acceptance criteria, explicit target paths, forbidden paths, code-change authority, repair limit, and provider selection through configuration.

## Functional Output

A successful mission produces EngineeringRequest, RepositoryEvidence, EngineeringContext, ChangeSpecification, approved ChangePlan, GeneratedChangeSet, edit transaction evidence, ValidationOutcome, zero or more RepairProposal records, approval evidence, final EngineeringEvidence, and terminal mission status.

## Fail-Closed Requirements

The agent must fail or pause when repository root is invalid, required evidence is unavailable, target relevance cannot be established, proposed edits exceed scope, fingerprints conflict, provider output is malformed or unsafe, required approval is missing, validation remains unsuccessful beyond the repair-attempt limit, or a required execution capability is unavailable.
'@

Write-Utf8NoBom "docs\general_engineering_agent\DATA_MODEL.md" @'
# M5.9 General Engineering Agent Data Model

## EngineeringRequest
Canonical user engineering request with request ID, objective, repository root, constraints, acceptance criteria, explicit target paths, forbidden paths, code-change authority, repair limit, and timestamp.

## RepositoryEvidence
Traceable repository fact with evidence ID, path, symbol, evidence type, relevance, fingerprint, rationale, and provenance.

## RelevantFile
Repository file selected for possible change with relevance rationale and evidence references.

## RelevantSymbol
Class, function, method, schema, route, component, configuration key, or other repository symbol relevant to the request.

## EngineeringContext
Normalized request plus selected repository evidence supplied to planning or synthesis.

## ChangeRequirement
One verifiable requirement derived from the EngineeringRequest.

## ChangeSpecification
Normalized requirements, constraints, invariants, and acceptance conditions.

## ChangePlan
Structured implementation plan containing ordered FileChangePlan entries, validation intent, expected effect, risk, and evidence references.

## FileChangePlan
One file-level planned change with path, symbols, rationale, dependencies, operations, risk, and evidence.

## EditOperation
One proposed mutation with operation ID, type, target path, optional symbol, source fingerprint, proposed content or patch data, rationale, requirement reference, and evidence references.

## GeneratedChangeSet
Ordered bounded collection of EditOperation proposals plus plan and evidence references.

## ValidationPlan
Approved commands or registered validation capabilities.

## ValidationOutcome
Validation status, commands, failures, scope, and evidence.

## RepairProposal
Bounded response to failed validation referencing failure evidence and necessary corrective changes.

## EngineeringEvidence
Traceability object linking request, repository evidence, plan, approvals, edits, validation, repairs, and final result.
'@

Write-Utf8NoBom "docs\general_engineering_agent\CHANGE_PLAN_MODEL.md" @'
# M5.9 Change Plan Model

A ChangePlan is the authoritative structured implementation proposal presented to Forge policy and approval systems.

## Required Properties

A ChangePlan contains plan ID, engineering request ID, objective, requirements, ordered file changes, dependencies, expected effect, validation plan, aggregate risk, repository evidence references, and timestamp.

## FileChangePlan

Each FileChangePlan identifies target path, relevant symbols, path-selection rationale, supporting evidence, intended operations, dependencies, expected local effect, and risk.

## Plan Validity

A plan is invalid when a target has no supporting evidence, a target is forbidden, acceptance criteria are omitted, dependencies contain an unresolved cycle, code-changing validation is absent, or scope exceeds the approved request.

## Approval Boundary

PLAN approval authorizes the structured plan scope. It does not authorize arbitrary mutation outside that plan. Material scope changes require replanning or renewed approval.
'@

Write-Utf8NoBom "docs\general_engineering_agent\EDIT_MODEL.md" @'
# M5.9 Edit Model

## Principle
Provider output is a proposed edit, never direct write authority.

## EditOperation Types
CREATE_FILE, INSERT, REPLACE, DELETE, and RENAME are the initial contract categories. Unsupported operations fail explicitly.

## EditOperation Fields
Operation ID, operation type, target path, optional target symbol, optional source fingerprint, proposed content or structured patch information, rationale, originating requirement, evidence references, and ordering metadata.

## Safety Requirements
Every operation must be checked for repository containment, forbidden-path policy, approved plan scope, current fingerprint where applicable, operation eligibility, content and size limits, self-modification policy, and conflicts with other operations.

## GeneratedChangeSet
A GeneratedChangeSet contains ordered EditOperation objects and is validated as one bounded unit before mutation begins.

## Execution
Approved operations flow through Forge-controlled editing and transaction services. Provider adapters expose no direct filesystem mutation authority.
'@

Write-Utf8NoBom "docs\general_engineering_agent\VALIDATION_AND_REPAIR_MODEL.md" @'
# M5.9 Validation and Repair Model

## Validation
Validation is repository-specific and uses approved project tooling or registered Forge capabilities. Evidence includes command or capability, working directory, exit status, structured failures where available, output summary, scope, and timestamp.

## ValidationOutcome States
passed, failed, blocked, and skipped_by_approved_exception.

A code-changing mission cannot complete without required validation passing or an explicitly approved exception supported by policy.

## RepairProposal
A failed ValidationOutcome may produce a RepairProposal containing repair ID, failure evidence, diagnosis, bounded affected requirements, proposed corrective plan or edits, target paths, risk, and attempt number.

## Repair Limits
Repair is bounded. Default maximum repair attempts: 3. Request or policy may impose a stricter limit but may not exceed platform authority limits.

## Repair Authority
Repair may not silently expand mission scope. Material expansion requires replanning and renewed approval. REPAIR approval is required where policy requires it.

## Terminal Failure
When validation remains unsuccessful after permitted attempts, Forge stops or pauses and preserves evidence.
'@

Write-Utf8NoBom "docs\general_engineering_agent\PROVIDER_MODEL.md" @'
# M5.9 Engineering Provider Model

## Purpose
EngineeringProvider separates reasoning and code-generation services from Forge authority and execution.

## Provider Responsibilities
A provider may normalize intent from supplied context, propose a ChangePlan, synthesize structured EditOperation proposals, analyze ValidationOutcome evidence, and propose a bounded RepairProposal.

## Provider Non-Authority
A provider must not write repository files, invoke arbitrary shell commands, persist approvals, change policy, mark a mission complete, bypass validation, or expand repository scope without Forge authorization.

## Protocol Shape
The provider contract exposes typed operations conceptually equivalent to understand_request(...), propose_change_plan(...), synthesize_edits(...), and propose_repair(...).

## Provider Implementations
Possible adapters include OpenAIEngineeringProvider, OllamaEngineeringProvider, deterministic FakeEngineeringProvider, and future enterprise providers.

Core general_engineering models, policies, and protocols must not import provider SDKs.

## Output Validation
All provider output is untrusted structured data until parsed and validated against Forge contracts, repository evidence, approved scope, and policy.
'@

Write-Utf8NoBom "docs\general_engineering_agent\ACCEPTANCE_CRITERIA.md" @'
# M5.9 General Engineering Agent Acceptance Criteria

M5.9 is complete only when:

1. previously unseen natural-language software tasks are accepted;
2. repository inspection occurs before change planning;
3. relevant files and symbols are selected using evidence;
4. every planned target has traceable rationale;
5. plans are structured rather than prose-only;
6. PLAN approval is enforced according to policy;
7. provider-specific reasoning is isolated behind EngineeringProvider contracts;
8. edit proposals are structured and validated;
9. provider output cannot mutate repository files directly;
10. EDIT approval is enforced according to policy;
11. safe single-file edits are supported;
12. bounded multi-file edits are supported;
13. forbidden paths and scope boundaries are enforced;
14. source fingerprints prevent stale destructive edits where required;
15. repository-specific validation runs after mutation;
16. validation failures produce evidence;
17. bounded repair proposals can be generated;
18. repair-attempt limits are enforced;
19. repeated failure terminates safely;
20. RELEASE approval is enforced according to policy;
21. end-to-end evidence links request, plan, approvals, edits, validation, repair, and result;
22. deterministic fake-provider tests pass;
23. no acceptance-task-specific implementation is encoded in Forge;
24. an unfamiliar single-file acceptance mission passes;
25. an unfamiliar multi-file acceptance mission passes;
26. an ERP-style or business-rule acceptance mission passes;
27. architecture validation passes;
28. Ruff passes;
29. MyPy passes;
30. focused and integration tests pass;
31. the full Forge regression suite passes;
32. worktree and release-gate requirements are clean before tagging.

## Prohibited Acceptance Shortcut
M5.9 must not be declared complete solely by demonstrating predefined calculator operations or another task explicitly encoded into Forge implementation logic.
'@

Write-Utf8NoBom "docs\general_engineering_agent\DECISIONS.md" @'
# M5.9 Architecture Decisions

## AD-1 — M5.9 Extends M5.8
M5.9 reuses the production mission runtime and safety gates proven by M5.8 rather than creating a competing agent runtime.

## AD-2 — Provider Proposes, Forge Executes
Engineering providers have reasoning authority only. Repository mutation remains governed by Forge.

## AD-3 — Repository Grounding Is Mandatory
General engineering plans must cite repository evidence for selected files and symbols.

## AD-4 — Plans and Edits Are Structured Contracts
Free-form provider prose is insufficient for execution authority.

## AD-5 — Multi-file Work Is Bounded
Coordinated multi-file changes remain inside approved scope and transaction controls.

## AD-6 — Repair Is Bounded
Repair attempts are finite and policy-governed. Default maximum: three.

## AD-7 — Provider Independence
Core contracts remain independent from OpenAI, Ollama, and other provider SDKs.

## AD-8 — Acceptance Must Be Previously Unseen
Release acceptance includes tasks not encoded into Forge implementation beforehand.

## AD-9 — No Default Self-Modification
General engineering capability does not override existing self-modification policy.

## AD-10 — No Scope Drift
Material requirement, target, or risk expansion requires replanning and renewed authority.

## AD-11 — M5.9 Is Not Multi-agent
Multi-agent coordination, autonomous deployment, browser automation, and unrestricted shell agents remain outside M5.9.
'@

$RequiredFiles = @(
    ".\docs\general_engineering_agent\ARCHITECTURE.md",
    ".\docs\general_engineering_agent\SPECIFICATION.md",
    ".\docs\general_engineering_agent\DATA_MODEL.md",
    ".\docs\general_engineering_agent\CHANGE_PLAN_MODEL.md",
    ".\docs\general_engineering_agent\EDIT_MODEL.md",
    ".\docs\general_engineering_agent\VALIDATION_AND_REPAIR_MODEL.md",
    ".\docs\general_engineering_agent\PROVIDER_MODEL.md",
    ".\docs\general_engineering_agent\ACCEPTANCE_CRITERIA.md",
    ".\docs\general_engineering_agent\DECISIONS.md"
)

foreach ($Path in $RequiredFiles) {
    if (-not (Test-Path $Path)) { throw "Missing M5.9 architecture file: $Path" }
    if ((Get-Item $Path).Length -lt 350) { throw "M5.9 architecture file is unexpectedly small: $Path" }
}

$Architecture = Get-Content ".\docs\general_engineering_agent\ARCHITECTURE.md" -Raw
$Specification = Get-Content ".\docs\general_engineering_agent\SPECIFICATION.md" -Raw
$Acceptance = Get-Content ".\docs\general_engineering_agent\ACCEPTANCE_CRITERIA.md" -Raw
$ProviderModel = Get-Content ".\docs\general_engineering_agent\PROVIDER_MODEL.md" -Raw

foreach ($RequiredTerm in @("Repository Grounding Requirement", "Authority Boundary", "Multi-file Transactions", "Validation and Repair", "Provider Independence")) {
    if ($Architecture -notmatch [regex]::Escape($RequiredTerm)) {
        throw "ARCHITECTURE.md is missing required M5.9 concept: $RequiredTerm"
    }
}

foreach ($RequiredTerm in @("EngineeringRequest", "RepositoryEvidence", "ChangePlan", "provider-independent", "repair-attempt")) {
    if ($Specification -notmatch [regex]::Escape($RequiredTerm)) {
        throw "SPECIFICATION.md is missing required M5.9 concept: $RequiredTerm"
    }
}

if ($ProviderModel -notmatch "must not write repository files") {
    throw "PROVIDER_MODEL.md does not explicitly prohibit direct repository mutation."
}

if ($Acceptance -notmatch "previously unseen" -or $Acceptance -notmatch "multi-file") {
    throw "M5.9 acceptance criteria do not enforce general, previously unseen multi-file engineering acceptance."
}

Write-Host ""
Write-Host "M5.9 GENERAL ENGINEERING AGENT ARCHITECTURE WRITTEN AND CHECKED" -ForegroundColor Green
Write-Host "NOTE: This script authors architecture only. It does not implement M5.9 runtime code." -ForegroundColor Yellow

Get-ChildItem ".\docs\general_engineering_agent" -File |
    Sort-Object Name |
    Select-Object Name, Length
