## Aerion Forge v0.3 - Milestone 2.2

### Added

- Deterministic `forge.tasks` subsystem
- Typed Task Management schema `1.0`
- Mission Plan to Task Set decomposition
- Parent-child task hierarchy
- Deterministic dependency mapping
- Task lifecycle and risk policies
- Dependency-cycle and parent-cycle validation
- Deterministic task and task-set fingerprints
- Atomic `memory/tasks.json` persistence
- Bounded task history and store restoration
- Read-only Task Query API
- Deterministic JSON and Markdown reports
- Report-failure rollback
- `forge task build`
- `forge task list`
- `forge task show`
- Nine `tasks.*` configuration settings
- Task Management documentation and contract

### Changed

- Promoted `task-management` to implemented, stable and available
- Live capability inventory is now 10 implemented and 21 planned
- Runtime configuration catalogue increased from 49 to 58 settings
- Preserved the historical Phase 1 inventory at 8 implemented and 23 planned

### Validation

- Ruff passed
- mypy passed across 174 source files
- pytest: 244 passed
- `git diff --check` passed

### Safety

Milestone 2.2 performs task planning and Forge-owned persistence only. It does
not execute tasks, edit source code, run builds or tests, perform migrations,
mutate Git, deploy software, schedule work, automatically assign owners or
perform autonomous remediation.

## Aerion Forge v0.3 - Milestone 2.1

### Added

- Deterministic `forge.planning` subsystem
- Typed Mission Planning schema `1.0`
- Engineering-request normalization
- Persisted Phase 1 context loading
- Prerequisite and graph-freshness validation
- Risk and approval classification
- Ready, ready-with-conditions, and blocked states
- Atomic mission persistence with bounded history and rollback
- Deterministic JSON and Markdown reports
- Read-only Mission Planning query API
- `forge mission plan` CLI
- Nine `planning.*` configuration settings
- Mission Planning documentation and contract

### Changed

- Promoted `mission-planning` to implemented, stable, and available
- Current capability inventory is 9 implemented and 22 planned
- Runtime configuration catalogue increased to 49 settings
- Preserved the historical Phase 1 inventory at 8 implemented and 23 planned

### Validation

- Ruff passed
- mypy passed across 152 source files
- pytest: 176 passed
- `git diff --check` passed

### Safety

Milestone 2.1 performs planning only. It does not edit source code, execute
target builds or tests, run migrations, mutate Git, deploy software, execute
tasks, or perform automatic remediation.

# Changelog

## Version 0.2.0 - Phase 1 Engineering Runtime

- Completed and froze Workspace Manager, Repository Discovery, Incremental Project Index,
  Engineering Knowledge Graph, Capability Registry, Runtime Configuration, and Runtime Health &
  Diagnostics contracts.
- Added deterministic release validation, schema/persistence/report/CLI inventories,
  architecture contract, release notes, manifest, integration tests, and security evidence.
- Promoted `phase-validation-release`: 8 of 31 capabilities are available and 23 remain planned.
- Confirmed target-read-only understanding, secret protection, deterministic artifacts, and no
  Phase 2 planning, editing, execution, ERP intelligence, monitoring, or remediation.

## Version 0.2 - Milestone 1.7

- Added typed runtime health and target readiness with a static 30-check catalogue.
- Added safe evidence/actions, cross-store consistency/freshness, deterministic fingerprints,
  atomic state/reports, query API, and `health`/`diagnose` commands.
- Promoted `runtime-health-diagnostics`: 7 capabilities are available and 24 remain planned.

## Version 0.2 - Milestone 1.6

- Added unified typed runtime configuration with profiles, TOML, canonical environment variables,
  aliases, CLI overrides, provenance, validation, redaction, snapshots, persistence, reports, query
  API, CLI, compatibility migration, tests, and documentation.
- Promoted only `runtime-configuration`; diagnostics and release automation remain planned.

## Version 0.2 - Milestone 1.5.4

- Independently reproduced catalogue, determinism, persistence, exclusion, CLI, query, security,
  dependency, documentation, and compatibility evidence.
- Added final release validation and release notes and technically froze the schema `1.0` contract.
- Recorded a conditional release-administration pass because Git metadata is absent; no commit or
  tag was created.

## Version 0.2 - Milestone 1.5.3

- Audited all 31 entries and documented the schema `1.0` contract freeze candidate.
- Added focused truthfulness, dependency, determinism, rollback, exclusion, query, CLI, security,
  and compatibility tests.
- Canonicalized nested declarations, completed removed/replacement validation, centralized `memory`
  exclusion, aligned roadmap versions, and removed duplicate dead CLI code.
- Added contract and audit documents without release tagging or later capability functionality.

## Version 0.2 - Milestone 1.5

- **1.5.1 foundation:** added typed models, enums, canonical IDs, static catalogue, and explicit
  definition/evaluation separation.
- **1.5.2 registry engine:** added dependency validation, availability evaluation, deterministic
  identities, diffs, statistics, atomic persistence, bounded history, reports, query API,
  configuration, CLI commands, and tests.
- **1.5.3 hardening:** audited catalogue truthfulness, expanded failure/determinism/compatibility
  coverage, centralized exclusions, and documented the freeze candidate.
- **1.5.4 release validation:** independently reproduced release evidence, finalized documentation,
  and technically froze schema `1.0` pending authorized Git administration.
- Registered roadmap features as planned and unavailable; no planning, execution, code editing,
  test generation, ERP analysis, dynamic plugin loading, or runtime configuration overhaul was added.

## Version 0.2 - Milestone 1.4

- Added the validated structural engineering knowledge graph.
- Added stable canonical node and edge identities with evidence and confidence.
- Added discovery/index input consistency checks and bounded structural resolution.
- Added deterministic graph generations, graph diffs, orphan analysis, and nine reports.
- Added atomic `memory/knowledge_graph.json` persistence and corruption handling.
- Added the typed read-only graph query API and `forge graph` CLI modes.
- Added graph construction, validation, determinism, persistence, query, safety, and CLI tests.
## Version 0.2 - Milestone 1.3

- Added the schema-versioned incremental project index.
- Added deterministic file classification and engineering-role inference.
- Added chunked full, bounded-sample, and protected SHA-256 fingerprint strategies.
- Added added, modified, removed, unchanged, renamed, failed, and skipped change detection.
- Added stable repository-state generations and atomic `memory/index.json` persistence.
- Added six deterministic JSON and Markdown index reports.
- Added `forge index` workspace, path, JSON, summary, changes, and verbose modes.
- Shared repository traversal exclusions between discovery and indexing.
- Added indexing determinism, safety, persistence, recovery, CLI, and compatibility tests.

