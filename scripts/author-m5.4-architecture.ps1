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

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.4-autonomous-decision-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.4 architecture must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$DocsRoot = "docs\autonomous_decision"

Write-Utf8NoBom "$DocsRoot\ARCHITECTURE.md" @'
# Aerion Forge M5.4 — Autonomous Decision Engine Architecture

## Status

Architecture Draft

## Purpose

M5.4 determines the next safe engineering decision for an active mission.

M5.1 governs mission state, authority, approval, events, and recovery.

M5.2 executes one approved engineering step through a controlled tool gateway.

M5.3 coordinates complete mission progress across bounded execution cycles.

M5.4 evaluates mission context, candidate actions, risk, confidence, policy, evidence, and expected utility to select one justified next action or an explicit stop decision.

## Architectural Boundary

M5.4 may:

- inspect mission, plan, orchestration, execution, validation, and repository evidence;
- generate bounded candidate actions;
- reject infeasible, unauthorized, unsafe, duplicate, or out-of-scope candidates;
- score remaining candidates using explicit factors;
- compare alternatives deterministically;
- select one next action;
- produce a structured decision rationale;
- request approval when required;
- choose retry, rollback, replan, pause, escalate, complete, or cancel;
- emit decision evidence for M5.3;
- support deterministic simulation.

M5.4 may not:

- invoke tools directly;
- mutate repository content;
- bypass M5.1 authority or approval controls;
- override M5.2 tool safety;
- execute unbounded reasoning loops;
- invent unsupported repository facts;
- select actions outside the active mission scope;
- silently modify an approved plan;
- conceal uncertainty or missing evidence.

## Core Components

1. Decision Request
2. Decision Context
3. Candidate Action
4. Candidate Generator
5. Feasibility Filter
6. Policy Filter
7. Risk Assessor
8. Confidence Assessor
9. Evidence Evaluator
10. Utility Scorer
11. Candidate Ranker
12. Decision Selector
13. Decision Rationale
14. Decision Journal
15. Decision Service
16. Reporting and CLI

## Decision Flow

```text
DECISION REQUEST
  -> LOAD DECISION CONTEXT
  -> VERIFY MISSION AND SESSION STATE
  -> GENERATE BOUNDED CANDIDATES
  -> REMOVE DUPLICATES
  -> FILTER INFEASIBLE CANDIDATES
  -> FILTER UNAUTHORIZED CANDIDATES
  -> ASSESS RISK
  -> ASSESS CONFIDENCE
  -> ASSESS EVIDENCE QUALITY
  -> SCORE EXPECTED UTILITY
  -> RANK DETERMINISTICALLY
  -> SELECT ONE ACTION OR STOP
  -> RECORD RATIONALE AND EVIDENCE
  -> RETURN DECISION TO M5.3
```

## Safety Principles

- No tool execution inside M5.4.
- Candidate generation is bounded.
- Every rejection has a reason.
- Every score is explainable.
- Every selected action has supporting evidence.
- Missing evidence lowers confidence.
- Policy violations are hard rejections.
- Ties are resolved deterministically.
- Approval requirements propagate unchanged.
- High-risk low-confidence actions stop or escalate.
- No decision is treated as fact without evidence provenance.
- Decision records are immutable.
'@

Write-Utf8NoBom "$DocsRoot\SPECIFICATION.md" @'
# M5.4 Autonomous Decision Engine Specification

## Functional Requirements

- Accept a structured decision request.
- Build a decision context from mission, plan, session, execution, validation, and repository evidence.
- Generate a finite candidate set.
- Normalize and deduplicate candidates.
- Reject candidates outside mission scope.
- Reject candidates requiring unavailable authority.
- Reject candidates violating approval policy.
- Reject candidates exceeding risk thresholds.
- Assess feasibility, risk, confidence, evidence quality, cost, reversibility, and expected value.
- Calculate deterministic candidate scores.
- Rank candidates deterministically.
- Select at most one action.
- Return an explicit stop decision when no candidate is acceptable.
- Produce a structured rationale.
- Record rejected alternatives and reasons.
- Record evidence references.
- Support retry, rollback, replan, pause, escalate, complete, and cancel decisions.
- Support dry-run simulation.
- Prevent replay of an identical decision against the same context fingerprint.
- Produce JSON and Markdown reports.

## Non-Functional Requirements

- Deterministic output for identical inputs
- Bounded candidate generation
- Explicit uncertainty
- Explainable scoring
- Immutable decision records
- Typed errors
- Stable identifiers
- Schema versioning
- Auditability
- No hidden side effects
'@

Write-Utf8NoBom "$DocsRoot\DATA_MODEL.md" @'
# M5.4 Autonomous Decision Engine Data Model

## Core Models

### DecisionRequest

- request_id
- mission_id
- session_id
- plan_id
- plan_version
- repository_root
- decision_kind
- maximum_candidates
- dry_run
- requested_by
- created_at

### DecisionContext

- context_id
- mission_id
- session_id
- mission_state
- orchestration_state
- current_step_id
- completed_step_ids
- failed_step_ids
- retry_count
- rollback_count
- replan_count
- authority_level
- approval_state
- repository_fingerprint
- evidence_references
- unresolved_findings
- policy_version
- created_at

### CandidateAction

- candidate_id
- action_kind
- target_step_id
- description
- required_authority
- approval_required
- risk_class
- expected_effects
- expected_cost
- reversible
- dependencies
- evidence_references
- source
- created_at

### CandidateAssessment

- assessment_id
- candidate_id
- feasible
- policy_allowed
- risk_score
- confidence_score
- evidence_score
- utility_score
- reversibility_score
- total_score
- rejection_reasons
- warnings
- created_at

### DecisionRecord

- decision_id
- request_id
- context_id
- selected_candidate_id
- decision_kind
- disposition
- rationale
- alternative_candidate_ids
- rejected_candidate_ids
- assessment_ids
- evidence_references
- approval_required
- confidence
- context_fingerprint
- created_at

### DecisionStop

- stop_id
- request_id
- stop_kind
- reason
- resumable
- approval_required
- evidence_references
- created_at

## Invariants

- Candidate count never exceeds the request or policy limit.
- Candidate identifiers are unique.
- Rejected candidates cannot be selected.
- Selected candidate must have an assessment.
- Selected candidate must be feasible and policy-allowed.
- Selected candidate must satisfy the configured risk threshold.
- Selected candidate must satisfy the configured confidence threshold.
- Decision context fingerprint must match the evaluated context.
- Identical context fingerprints cannot produce conflicting committed decisions.
- Stop decisions cannot contain a selected candidate.
- Decision records are immutable.
'@

Write-Utf8NoBom "$DocsRoot\DECISION_MODEL.md" @'
# M5.4 Decision Model

## Decision Dispositions

- select_action
- retry
- rollback
- replan
- pause
- escalate
- complete
- cancel
- no_safe_action

## Evaluation Dimensions

### Feasibility

Can the action be performed with the available repository state, dependencies, tools, and prerequisites?

### Policy Compliance

Does the action comply with authority, approval, scope, architecture, security, and runtime policy?

### Risk

What is the probability and impact of failure, data loss, scope drift, security exposure, or irreversible mutation?

### Confidence

How strongly does available evidence support the candidate and its expected outcome?

### Evidence Quality

Are the supporting sources current, relevant, complete, and traceable?

### Utility

What expected progress does the action provide relative to cost, risk, delay, and reversibility?

### Reversibility

Can the action be safely undone using a verified checkpoint or rollback procedure?

## Deterministic Scoring

Each accepted candidate receives normalized scores from 0.0 to 1.0.

```text
total_score =
    utility_weight * utility_score
  + confidence_weight * confidence_score
  + evidence_weight * evidence_score
  + reversibility_weight * reversibility_score
  - risk_weight * risk_score
```

Hard policy rejection occurs before scoring.

Ties are resolved using:

1. lower risk;
2. higher confidence;
3. higher evidence quality;
4. greater reversibility;
5. stable candidate identifier.
'@

Write-Utf8NoBom "$DocsRoot\CANDIDATE_MODEL.md" @'
# M5.4 Candidate Generation and Filtering Model

## Candidate Sources

- approved mission plan
- current orchestration state
- previous execution outcome
- validation findings
- recovery policy
- unresolved blockers
- repository evidence
- architecture constraints
- approval requirements
- budget state

## Candidate Categories

- execute_next_step
- retry_current_step
- rollback_current_step
- replan_remaining_work
- request_approval
- pause_mission
- escalate_mission
- complete_mission
- cancel_mission

## Candidate Generation Rules

- Candidate generation is deterministic.
- Candidate generation is bounded.
- Candidates must reference supporting evidence.
- Duplicate semantic actions are collapsed.
- Completed steps are not generated again.
- Unsupported action kinds are rejected.
- Candidate scope must remain within the mission.
- Candidate authority must not exceed configured policy.
- Candidate approval requirements are preserved.

## Rejection Reasons

- duplicate
- infeasible
- missing_dependency
- insufficient_authority
- approval_required
- scope_violation
- risk_threshold_exceeded
- confidence_below_threshold
- evidence_insufficient
- completed_step_replay
- budget_exhausted
- policy_violation
'@

Write-Utf8NoBom "$DocsRoot\CONFIDENCE_MODEL.md" @'
# M5.4 Confidence and Evidence Model

## Confidence Inputs

- direct repository evidence
- test and validation evidence
- execution outcome consistency
- architecture alignment
- dependency completeness
- source freshness
- source agreement
- unresolved uncertainty
- historical decision performance

## Confidence Rules

- Confidence ranges from 0.0 to 1.0.
- Unsupported assumptions reduce confidence.
- Conflicting evidence reduces confidence.
- Missing required evidence may force rejection.
- High-risk actions require higher confidence.
- Confidence cannot be increased by candidate popularity.
- Confidence rationale must be recorded.

## Evidence Quality

Evidence is assessed for:

- relevance
- provenance
- completeness
- recency
- consistency
- reproducibility
- integrity

## Required Behaviour

When evidence is inadequate, M5.4 must:

- request clarification;
- request additional inspection;
- pause;
- escalate;
- or return no_safe_action.

It must not invent missing facts.
'@

Write-Utf8NoBom "$DocsRoot\POLICY_MODEL.md" @'
# M5.4 Decision Policy Model

## Hard Policies

The following conditions reject a candidate before scoring:

- authority is insufficient;
- approval is missing;
- action is outside scope;
- action violates architecture constraints;
- action exceeds configured risk class;
- action would replay completed work;
- required dependency is absent;
- required checkpoint is absent;
- runtime budget is exhausted;
- action is prohibited by security policy.

## Threshold Policies

- maximum candidate count
- maximum accepted risk
- minimum confidence
- minimum evidence quality
- minimum utility
- minimum reversibility for mutating actions

## Default-Safe Behaviour

- Dry-run is the default.
- No candidate is selected when all candidates fail policy.
- High-risk and low-confidence decisions escalate.
- Irreversible actions require approval.
- Ties are resolved deterministically.
- Policy versions are recorded in every decision.
'@

Write-Utf8NoBom "$DocsRoot\ACCEPTANCE_CRITERIA.md" @'
# M5.4 Acceptance Criteria

M5.4 is complete only when:

- [ ] Decision contracts are immutable and versioned.
- [ ] Candidate generation is finite and deterministic.
- [ ] Candidate limits are enforced.
- [ ] Duplicate candidates are removed.
- [ ] Scope violations are rejected.
- [ ] Authority violations are rejected.
- [ ] Approval requirements are preserved.
- [ ] Risk assessment is explicit.
- [ ] Confidence assessment is explicit.
- [ ] Evidence quality is explicit.
- [ ] Utility scoring is deterministic.
- [ ] Candidate ranking is deterministic.
- [ ] Rejected alternatives include reasons.
- [ ] At most one candidate is selected.
- [ ] No-safe-action decisions are supported.
- [ ] Retry, rollback, replan, pause, escalate, complete, and cancel are supported.
- [ ] Decision context fingerprints prevent conflicting replay.
- [ ] Structured rationale is produced.
- [ ] JSON and Markdown reports are produced.
- [ ] CLI simulation is read-only.
- [ ] Ruff passes.
- [ ] MyPy passes.
- [ ] M5.4 focused tests pass.
- [ ] Full repository tests pass.
'@

Write-Utf8NoBom "$DocsRoot\DECISIONS.md" @'
# M5.4 Architecture Decisions

## ADR-001 — Decision engine does not execute tools

M5.4 returns decisions to M5.3. M5.2 remains the only controlled execution boundary.

## ADR-002 — Hard filters before scoring

Infeasible, unauthorized, unsafe, duplicate, or out-of-scope candidates are rejected before ranking.

## ADR-003 — Deterministic candidate ranking

Identical inputs and policy versions must produce the same ranking and selected decision.

## ADR-004 — Evidence is mandatory

Every selected action must reference supporting evidence.

## ADR-005 — Explicit uncertainty

Confidence and evidence quality are first-class decision fields.

## ADR-006 — One selected action

A committed decision selects at most one candidate.

## ADR-007 — No-safe-action is valid

When no candidate satisfies policy and thresholds, M5.4 returns a stop decision rather than forcing progress.

## ADR-008 — Context fingerprinting

Committed decisions are bound to the exact evaluated context.

## ADR-009 — Dry-run by default

CLI and simulation paths do not mutate repository or mission state.
'@

$RequiredFiles = @(
    "ARCHITECTURE.md",
    "SPECIFICATION.md",
    "DATA_MODEL.md",
    "DECISION_MODEL.md",
    "CANDIDATE_MODEL.md",
    "CONFIDENCE_MODEL.md",
    "POLICY_MODEL.md",
    "ACCEPTANCE_CRITERIA.md",
    "DECISIONS.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $DocsRoot $File

    if (-not (Test-Path $Path)) {
        throw "Missing M5.4 architecture document: $Path"
    }

    if ((Get-Item $Path).Length -lt 300) {
        throw "M5.4 architecture document is unexpectedly small: $Path"
    }

    $Content = Get-Content $Path -Raw

    if ($Content -match "_To be completed\._") {
        throw "Placeholder remains in M5.4 architecture document: $Path"
    }
}

Write-Host ""
Write-Host "M5.4 ARCHITECTURE DOCUMENTS WRITTEN AND CHECKED" -ForegroundColor Green

Get-ChildItem $DocsRoot |
    Sort-Object Name |
    Select-Object Name, Length |
    Format-Table -AutoSize