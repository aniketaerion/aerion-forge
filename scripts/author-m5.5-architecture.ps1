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

$ExpectedBranch = "feature/m5.5-autonomous-memory-learning"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.5 architecture must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$DocsRoot = "docs\autonomous_memory"

Write-Utf8NoBom "$DocsRoot\ARCHITECTURE.md" @'
# Aerion Forge M5.5 — Autonomous Memory and Learning Architecture

## Status

Architecture Draft

## Purpose

M5.5 gives Aerion Forge durable, evidence-backed engineering memory.

The subsystem captures mission outcomes, decisions, execution evidence, validation results, repository facts, failure patterns, recovery results, and reusable engineering knowledge. It retrieves only relevant and authorized memory for later missions.

M5.5 improves future planning and decisions without bypassing M5.1 authority, M5.2 execution controls, M5.3 orchestration, or M5.4 decision policy.

## Architectural Boundary

M5.5 may:

- ingest validated mission artifacts;
- normalize observations into typed memory records;
- retain provenance and repository fingerprints;
- classify facts, hypotheses, outcomes, failures, recoveries, and lessons;
- deduplicate semantically equivalent records;
- supersede outdated records without deleting history;
- retrieve relevant memory using deterministic filters;
- score relevance, confidence, recency, and applicability;
- associate memory with repositories, modules, capabilities, and business domains;
- generate learning summaries from completed missions;
- record whether prior guidance succeeded or failed;
- support memory export, inspection, and retention policy enforcement.

M5.5 may not:

- treat unverified model output as fact;
- store secrets, credentials, raw environment values, or sensitive payloads;
- mutate repositories;
- execute tools;
- overwrite immutable evidence;
- silently delete historical records;
- reuse memory outside its authority or repository scope;
- convert correlation into causation;
- update policy automatically without explicit approval;
- allow memory to override current repository evidence.

## Core Components

1. Memory Observation
2. Memory Record
3. Evidence Provenance
4. Confidence Model
5. Memory Classifier
6. Deduplication Engine
7. Supersession Model
8. Memory Store
9. Retrieval Query
10. Retrieval Filter
11. Relevance Ranker
12. Applicability Evaluator
13. Learning Extractor
14. Outcome Feedback Processor
15. Retention and Redaction Policy
16. Memory Service
17. Reporting and CLI

## Memory Flow

```text
MISSION ARTIFACTS
  -> VALIDATE SOURCE AND PROVENANCE
  -> REDACT PROHIBITED DATA
  -> CLASSIFY OBSERVATION
  -> NORMALIZE MEMORY RECORD
  -> CALCULATE CONFIDENCE
  -> DEDUPLICATE
  -> SUPERSEDE WHEN REQUIRED
  -> PERSIST IMMUTABLY
  -> INDEX BY SCOPE AND DOMAIN
  -> RETRIEVE BY EXPLICIT QUERY
  -> FILTER BY AUTHORITY AND APPLICABILITY
  -> RANK DETERMINISTICALLY
  -> RETURN MEMORY WITH PROVENANCE
```

## Safety Principles

- Current repository evidence outranks memory.
- Unverified observations are never stored as facts.
- Every memory has provenance.
- Every memory has confidence.
- Every memory has applicability boundaries.
- Historical records are immutable.
- Corrections supersede; they do not erase.
- Retrieval is scope-constrained.
- Secrets are prohibited.
- Learning is advisory unless approved policy says otherwise.
- Failed guidance remains visible as negative evidence.
- Identical inputs produce deterministic retrieval ordering.
'@

Write-Utf8NoBom "$DocsRoot\SPECIFICATION.md" @'
# M5.5 Autonomous Memory and Learning Specification

## Functional Requirements

- Accept typed memory observations from completed or paused missions.
- Validate source provenance before persistence.
- Reject secret-bearing or prohibited content.
- Classify observations as fact, hypothesis, decision, outcome, failure, recovery, lesson, constraint, or preference.
- Preserve repository, mission, session, decision, execution, and evidence references.
- Calculate explicit confidence.
- Calculate applicability scope.
- Detect exact and semantic duplicates.
- Preserve immutable history.
- Supersede outdated records explicitly.
- Store positive and negative outcomes.
- Retrieve memory by repository, capability, module, domain, tags, event type, and time.
- Enforce authority and scope filters.
- Rank retrieval results deterministically.
- Explain retrieval scores.
- Prevent stale memory from overriding fresh repository evidence.
- Extract lessons from validated outcomes.
- Record whether reused guidance succeeds or fails.
- Produce JSON and Markdown memory reports.
- Provide read-only CLI inspection and simulation.

## Non-Functional Requirements

- Deterministic retrieval
- Typed immutable records
- Explicit provenance
- Explicit confidence
- Scope isolation
- Secret rejection
- Schema versioning
- Auditability
- Bounded retrieval
- Backward-compatible persistence
- No hidden side effects
'@

Write-Utf8NoBom "$DocsRoot\DATA_MODEL.md" @'
# M5.5 Autonomous Memory Data Model

## Core Models

### MemoryObservation

- observation_id
- source_kind
- source_reference
- repository_root
- repository_fingerprint
- mission_id
- session_id
- content
- evidence_references
- tags
- observed_at

### MemoryRecord

- memory_id
- schema_version
- memory_kind
- statement
- normalized_statement
- confidence
- repository_scope
- module_scope
- capability_scope
- business_domain
- evidence_references
- source_references
- tags
- applicability
- status
- supersedes_memory_id
- created_at

### MemoryProvenance

- provenance_id
- memory_id
- source_kind
- source_reference
- evidence_digest
- repository_fingerprint
- actor
- captured_at

### MemoryQuery

- query_id
- repository_scope
- module_scope
- capability_scope
- business_domain
- memory_kinds
- tags
- minimum_confidence
- maximum_results
- include_superseded
- requested_by
- created_at

### MemoryMatch

- memory_id
- relevance_score
- confidence_score
- recency_score
- applicability_score
- total_score
- matched_terms
- rationale

### LearningRecord

- learning_id
- source_memory_ids
- lesson
- success_count
- failure_count
- confidence
- applicability
- last_validated_at
- created_at

## Invariants

- Memory identifiers are unique.
- Stored facts require evidence.
- Confidence is between 0.0 and 1.0.
- Superseded records remain immutable.
- A record cannot supersede itself.
- Supersession chains cannot cycle.
- Prohibited content cannot be persisted.
- Retrieval result count is bounded.
- Superseded records are excluded by default.
- Repository-scoped memory cannot cross repository boundaries without explicit policy.
- Learning records must cite source memory.
'@

Write-Utf8NoBom "$DocsRoot\MEMORY_MODEL.md" @'
# M5.5 Memory Classification Model

## Memory Kinds

- repository_fact
- architecture_constraint
- business_rule
- implementation_decision
- validation_outcome
- execution_outcome
- failure_pattern
- recovery_pattern
- engineering_lesson
- user_preference
- hypothesis
- negative_evidence

## Memory Status

- active
- superseded
- disputed
- expired
- quarantined

## Classification Rules

- Facts require direct evidence.
- Hypotheses are clearly labelled.
- Failed approaches are stored as negative evidence.
- User preferences never become architecture constraints automatically.
- Business rules require source attribution.
- Temporary runtime observations receive expiration.
- Repository-specific findings remain repository-scoped.
- Cross-project lessons require explicit applicability evaluation.
'@

Write-Utf8NoBom "$DocsRoot\RETRIEVAL_MODEL.md" @'
# M5.5 Retrieval and Ranking Model

## Retrieval Filters

- repository scope
- module scope
- capability scope
- business domain
- memory kind
- tags
- confidence threshold
- status
- age
- authority scope

## Ranking Dimensions

- semantic relevance
- repository applicability
- capability applicability
- confidence
- evidence quality
- recency
- historical success
- historical failure

## Deterministic Score

```text
total_score =
    relevance_weight * relevance_score
  + applicability_weight * applicability_score
  + confidence_weight * confidence_score
  + evidence_weight * evidence_score
  + recency_weight * recency_score
  + outcome_weight * outcome_score
```

## Tie Breaking

1. higher applicability;
2. higher confidence;
3. stronger evidence;
4. newer active record;
5. stable memory identifier.

## Required Behaviour

- Current repository evidence outranks memory.
- Superseded memory is excluded by default.
- Negative evidence is returned when relevant.
- Every match includes ranking rationale.
- Retrieval limits are enforced.
'@

Write-Utf8NoBom "$DocsRoot\LEARNING_MODEL.md" @'
# M5.5 Learning and Feedback Model

## Learning Sources

- completed mission outcomes
- failed execution attempts
- successful recovery actions
- validation regressions
- accepted and rejected decisions
- user corrections
- architecture review findings
- repeated repository patterns

## Learning Rules

- Only validated outcomes affect success and failure counts.
- A single outcome cannot establish a universal rule.
- Learning confidence increases with consistent evidence.
- Conflicting outcomes reduce confidence.
- Lessons retain source memory identifiers.
- Learning does not alter authority or policy automatically.
- Failed reused guidance is recorded as negative feedback.
- Stale lessons are revalidated before reuse.

## Feedback Loop

```text
MEMORY RETRIEVED
  -> GUIDANCE USED
  -> MISSION OUTCOME OBSERVED
  -> OUTCOME VALIDATED
  -> SUCCESS OR FAILURE ATTRIBUTED
  -> LEARNING RECORD UPDATED
  -> CONFIDENCE RECALCULATED
```
'@

Write-Utf8NoBom "$DocsRoot\RETENTION_MODEL.md" @'
# M5.5 Retention, Redaction, and Supersession Model

## Prohibited Content

- passwords
- API keys
- access tokens
- private keys
- raw environment variables
- personal data not required for engineering work
- unrestricted command output containing secrets
- unredacted customer-confidential payloads

## Retention Classes

- permanent architecture evidence
- long-lived engineering lessons
- project-lifetime repository facts
- bounded operational observations
- temporary hypotheses
- quarantined records

## Supersession

- Records are never silently overwritten.
- Corrections create new records.
- New records reference superseded records.
- Superseded records remain auditable.
- Cyclic supersession is prohibited.
- Retrieval excludes superseded records unless explicitly requested.

## Expiration

- Temporary observations may expire.
- Expiration does not destroy audit history.
- Expired records are excluded from normal retrieval.
'@

Write-Utf8NoBom "$DocsRoot\POLICY_MODEL.md" @'
# M5.5 Memory Policy Model

## Hard Policies

Reject persistence when:

- evidence is required but absent;
- prohibited data is detected;
- repository scope is missing;
- source provenance is missing;
- confidence is invalid;
- supersession would create a cycle;
- memory crosses authority boundaries;
- record attempts to overwrite immutable history.

## Default Limits

- bounded observation size
- bounded tag count
- bounded retrieval result count
- minimum fact confidence
- maximum retrieval age where applicable
- explicit inclusion of superseded records
- explicit cross-repository retrieval approval

## Default-Safe Behaviour

- retrieval is repository-scoped;
- superseded records are hidden;
- secrets are rejected;
- hypotheses remain hypotheses;
- facts require evidence;
- memory is advisory;
- current repository evidence wins.
'@

Write-Utf8NoBom "$DocsRoot\ACCEPTANCE_CRITERIA.md" @'
# M5.5 Acceptance Criteria

M5.5 is complete only when:

- [ ] Memory contracts are immutable and versioned.
- [ ] Every stored memory has provenance.
- [ ] Facts require evidence.
- [ ] Hypotheses remain explicitly labelled.
- [ ] Prohibited content is rejected.
- [ ] Exact duplicate detection works.
- [ ] Semantic duplicate handling is deterministic.
- [ ] Supersession preserves history.
- [ ] Supersession cycles are rejected.
- [ ] Retrieval is repository-scoped by default.
- [ ] Retrieval limits are enforced.
- [ ] Superseded records are excluded by default.
- [ ] Negative evidence is retrievable.
- [ ] Ranking is deterministic.
- [ ] Ranking rationale is reported.
- [ ] Current repository evidence outranks memory.
- [ ] Learning records cite source memory.
- [ ] Success and failure feedback are recorded.
- [ ] Memory cannot alter authority automatically.
- [ ] JSON and Markdown reports are produced.
- [ ] CLI inspection is read-only.
- [ ] Ruff passes.
- [ ] MyPy passes.
- [ ] M5.5 focused tests pass.
- [ ] Full repository tests pass.
'@

Write-Utf8NoBom "$DocsRoot\DECISIONS.md" @'
# M5.5 Architecture Decisions

## ADR-001 — Memory is evidence-backed

Unverified model output cannot be stored as fact.

## ADR-002 — Repository evidence outranks memory

Memory assists current analysis but cannot override fresh repository inspection.

## ADR-003 — Immutable history

Records are superseded, disputed, expired, or quarantined; they are not silently overwritten.

## ADR-004 — Repository scope by default

Cross-repository reuse requires explicit applicability and policy approval.

## ADR-005 — Negative evidence is retained

Failed approaches and failed reused guidance remain available.

## ADR-006 — Secrets are prohibited

Memory ingestion applies mandatory redaction and rejection policy.

## ADR-007 — Deterministic retrieval

Identical queries against identical stores produce identical ordering.

## ADR-008 — Learning is advisory

Learning records do not automatically change authority, approval, or execution policy.

## ADR-009 — Outcome feedback is explicit

Success and failure attribution require validated mission outcomes.
'@

$RequiredFiles = @(
    "ARCHITECTURE.md",
    "SPECIFICATION.md",
    "DATA_MODEL.md",
    "MEMORY_MODEL.md",
    "RETRIEVAL_MODEL.md",
    "LEARNING_MODEL.md",
    "RETENTION_MODEL.md",
    "POLICY_MODEL.md",
    "ACCEPTANCE_CRITERIA.md",
    "DECISIONS.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $DocsRoot $File

    if (-not (Test-Path $Path)) {
        throw "Missing M5.5 architecture document: $Path"
    }

    if ((Get-Item $Path).Length -lt 300) {
        throw "M5.5 architecture document is unexpectedly small: $Path"
    }

    $Content = Get-Content $Path -Raw

    if ($Content -match "_To be completed\._") {
        throw "Placeholder remains in M5.5 architecture document: $Path"
    }
}

Write-Host ""
Write-Host "M5.5 ARCHITECTURE DOCUMENTS WRITTEN AND CHECKED" `
    -ForegroundColor Green

Get-ChildItem $DocsRoot |
    Sort-Object Name |
    Select-Object Name, Length |
    Format-Table -AutoSize
