# Aerion Forge Architecture

Version 0.2 Milestone 1.5 preserves the audit, workspace, discovery, indexing, and graph boundaries.

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
