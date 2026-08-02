# Aerion Forge Architecture

Version 0.2 Phase 1 freezes the Engineering Runtime subsystem boundaries.

## Runtime readiness

```text
Unified Runtime Configuration
             ↓
Capability Registry
             ↓
Runtime Health & Diagnostics
             ↓
Readiness Evidence for Future Planning
```

Diagnostics consumes safe Workspace, Discovery, Index, Knowledge Graph, Capability, and
Configuration stores plus report paths and shared repository policy. It does not regenerate or
repair state and never executes target code. Phase 2 may consume readiness later.

The frozen contract, schema inventory, legacy-scaffolding boundary, and compatibility policy are
defined in `contracts/PHASE_1_ENGINEERING_RUNTIME_CONTRACT.md`. Phase validation creates release
evidence but performs no Git, packaging, publishing, or deployment automation.

```text
Workspace Manager -> Repository Discovery -> Incremental Project Index
                  -> Engineering Knowledge Graph -> Capability Registry
```

Unified Runtime Configuration is the typed Forge-local foundation beneath capability and repository
services. It exposes safe immutable snapshots and never inspects target repositories.

The registry is a global control-plane metadata service, not a downstream analysis stage. It does
not traverse repositories or execute capabilities. Future systems consult it before operations.
Its IDs, schema, public models, lifecycle and dependency semantics, queries, CLI, persistence path,
and report names follow the migration policy in the capability registry contract.

## Package Diagram

```text
run.py / forge.cli
        |
        +--> forge.agents       --> Version 0.1 audit
        +--> forge.workspace    --> workspace CRUD and selection
        +--> forge.discovery
                 |
                 +--> scanner   --> names, stats, recognized manifests
                 +--> models    --> validated discovery result
                 +--> renderer  --> 8 JSON + 3 Markdown artifacts
                 +--> service   --> atomic reports + discovery memory

forge.memory.JsonMemoryStore
        +--> memory/workspaces.json
        +--> memory/discovery.json
```

## Discovery Flow

1. `forge inspect` resolves an explicit workspace name or ID through `WorkspaceManager`.
2. A direct existing path is accepted when no workspace matches.
3. With no argument, Forge uses the active workspace, then the current directory.
4. `RepositoryDiscoveryScanner` validates the root and performs sorted traversal while excluding generated and dependency directories.
5. File extensions provide language counts; paths provide directory, application, infrastructure, CI/CD, environment, documentation, and license metadata.
6. Only recognized manifests and configuration files are read for dependencies, scripts, frameworks, databases, build systems, tests, linting, and formatting.
7. Pydantic validates the complete `DiscoveryResult`.
8. `DiscoveryRenderer` creates stable JSON with sorted keys and Markdown without volatile timestamps.
9. `DiscoveryService` atomically writes reports and persists the latest result under a stable workspace ID or repository-path hash.

## Discovery Boundaries

Traversal gathers names, sizes, and aggregate directory statistics. Source files are never opened. Large manifests are bounded to one megabyte. Generated trees such as `.git`, virtual environments, caches, `node_modules`, build output, vendor trees, and Rust targets are excluded.

This is repository discovery, not repository audit. It does not emit findings, analyze control flow, resolve imports, understand symbols, build a knowledge graph, or modify the inspected repository.

## Artifact Contract

- `PROJECT.json`: identity, type, size, counts, Git, license, and workspace compatibility.
- `TECH_STACK.json`: languages, technologies, frameworks, databases, package managers, containers, and CI/CD.
- `APPLICATIONS.json`: applications, frontend/backend services, libraries, workers, schedulers, CLI, and infrastructure classifications.
- `DEPENDENCIES.json`: sorted manifest dependencies with source and scope.
- `BUILD_SYSTEM.json`: build systems and declared scripts.
- `TEST_FRAMEWORKS.json`: test, lint, and formatting tools.
- `CONFIGURATION.json`: configuration, environment, documentation, and Kubernetes files.
- `DIRECTORY_STRUCTURE.json`: deterministic direct-child directory statistics.
- Markdown summaries: project, technology, and application views.

## Workspace Integration

Discovery consumes workspace identity and repository path without changing workspace records. Registered project types now include ERP, CRM, GCS, PX4, ROS2, Python, React, Node, NextJS, Express, NestJS, Flutter, Embedded, C++, Rust, Go, Java, Website, and Generic.

## Persistence

`memory/discovery.json` stores results under `results`, keyed by immutable workspace ID when available or a SHA-256 hash of the normalized repository root. `latest_result_id` identifies the most recent successful inspection. The existing thread-safe atomic JSON store is used; no database or cache layer is introduced.

## Existing Systems

Workspace lifecycle, health, and doctor behavior remain unchanged. The Version 0.1 audit still performs its independent read-only source inspection and report generation. The runtime and disabled plugin manifests are not involved in discovery.

## Incremental Index Architecture

```text
forge index / active workspace / direct path
        |
        +--> shared repository policy
        +--> ProjectIndexScanner
                 +--> deterministic classifier
                 +--> chunked FileFingerprinter
        +--> IndexingService
                 +--> previous ProjectIndex comparison
                 +--> repository-state fingerprint
                 +--> logical IndexGeneration
                 +--> deterministic IndexRenderer
                 +--> atomic ProjectIndexStore
```

Discovery remains the high-level repository inventory. Indexing is the canonical file-level inventory and consumes only paths, metadata, and file bytes for hashing. It does not consume or rewrite `memory/discovery.json`, and it introduces no semantic or dependency graph.

The current state is built completely before comparison. Reports are prepared and atomically replaced before the validated store is committed. Scan, limit, classification, fingerprint, or report failures cannot replace the previous successful index. Corrupt and schema-incompatible stores fail explicitly rather than resetting.

Logical generations represent stable repository states. The generation ID derives from the repository-state fingerprint, which derives from schema version, normalized relative path, content fingerprint strategy and value, category, engineering role, repository area, and index status. Absolute paths, traversal order, timestamps, Forge reports, and the index store itself do not affect state.

CLI exits are `0` for success, `2` for invalid targets, `3` for indexing failures, `4` for persistence failures, and `5` for report failures. Full classification, fingerprint, safety, and recovery rules are documented in [INDEXING.md](INDEXING.md).

## Knowledge Graph Architecture

```text
workspace + discovery + project index
                  |
                  +--> input consistency validation
                  +--> StructuralResolver
                  +--> KnowledgeGraphBuilder
                  +--> full-state graph diff
                  +--> KnowledgeGraphValidator
                  +--> deterministic renderer
                  +--> atomic knowledge graph repository
                  +--> read-only KnowledgeGraphQuery
```

The graph layer never invokes repository discovery or indexing and performs no filesystem traversal. Stable canonical IDs derive from controlled type, repository or workspace identity, normalized relative path, and canonical technology names. Edge IDs hash one directional source/type/target tuple. Typed dictionaries deduplicate entities before strict referential validation.

A bounded structural module groups major paths beneath discovered component roots; it does not represent source-language modules. Full deterministic rebuild plus incremental comparison is the Milestone 1.4 update strategy. See [KNOWLEDGE_GRAPH.md](KNOWLEDGE_GRAPH.md) for the complete contract.

## Phase 2 Mission Planning Architecture

Milestone 2.1 introduces the `forge.planning` subsystem.

### Components

- `models.py` - typed mission models and controlled enums
- `normalizer.py` - deterministic engineering-request normalization
- `context.py` - read-only loading of persisted Forge state
- `policies.py` - planning policy and milestone exclusions
- `planner.py` - prerequisite, risk, approval, scope, and readiness logic
- `validator.py` - plan contract validation
- `store.py` - atomic persistence and bounded history
- `renderer.py` - deterministic JSON and Markdown reports
- `query.py` - immutable read-only mission queries
- `service.py` - orchestration, rollback, persistence, and reporting
- `cli.py` - `forge mission plan`

### Data Flow

    Engineering request
        -> normalization
        -> persisted context loading
        -> prerequisite evaluation
        -> risk and approval classification
        -> readiness evaluation
        -> validated mission plan
        -> persistence and reports

### Safety Boundary

The subsystem reads Forge-owned persisted evidence only. It does not traverse
source files, edit target code, execute subprocesses, run target builds or
tests, perform migrations, mutate Git, deploy software, or remediate issues.

The historical Phase 1 release manifest remains frozen at 8 implemented and
23 planned capabilities. The live Milestone 2.1 registry contains 9 implemented
and 22 planned capabilities.

## Phase 2 Task Management Architecture

Milestone 2.2 introduces the `forge.tasks` subsystem.

### Components

- `models.py` - immutable typed task contracts and controlled enums
- `errors.py` - Task Management exception hierarchy
- `identifiers.py` - deterministic task and task-set identities
- `policies.py` - lifecycle transitions, risk ordering and milestone exclusions
- `validator.py` - task-set, hierarchy, dependency and fingerprint validation
- `decomposer.py` - deterministic Mission Plan to Task Set transformation
- `store.py` - atomic persistence, snapshots, restoration and bounded history
- `query.py` - immutable read-only task queries
- `renderer.py` - deterministic JSON and Markdown reports
- `service.py` - decomposition, validation, persistence, reporting and rollback
- `cli.py` - `forge task build`, `forge task list` and `forge task show`

### Data Flow

    Persisted Mission Plan
        -> mission lookup
        -> deterministic decomposition
        -> task hierarchy and dependency construction
        -> validation
        -> task-set fingerprinting
        -> persistence
        -> deterministic reports

### Persistence Boundary

Task Management writes only Forge-owned state and reports:

- `memory/tasks.json`
- `reports/latest/TASK_*.json`
- `reports/latest/TASK_*.md`

It does not mutate the target repository.

### Safety Boundary

Milestone 2.2 excludes task execution, scheduling, automatic assignment,
source-code editing, target builds, target tests, migrations, Git mutation,
deployment and autonomous remediation.

The live Forge v0.3 catalogue contains 10 implemented capabilities and
21 planned capabilities. The historical Phase 1 release manifest remains
frozen at 8 implemented capabilities and 23 planned capabilities.
