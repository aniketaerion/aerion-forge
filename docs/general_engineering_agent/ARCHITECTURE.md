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