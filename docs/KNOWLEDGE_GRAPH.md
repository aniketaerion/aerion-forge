# Engineering Knowledge Graph Foundation

Version 0.2 Milestone 1.4 converts persisted workspace, discovery, and project-index state into a deterministic structural engineering graph. Discovery remains the high-level inventory, indexing remains the canonical file inventory, and the graph relates those existing facts without rescanning or interpreting source code.

## CLI

```powershell
forge graph
forge graph ERP
forge graph "D:\Software Dev\ERP"
forge graph ERP --json
forge graph ERP --summary
forge graph ERP --changes
forge graph ERP --orphans
forge graph ERP --validate
forge graph ERP --verbose
```

Run `forge inspect <target>` and `forge index <target>` first. Graph construction never triggers either operation silently.

## Input Flow

```text
workspace metadata ----+
memory/discovery.json --+--> builder --> validator --> reports
memory/index.json ------+                     +-----> memory/knowledge_graph.json
```

The loader verifies the target root, workspace identity, repository identity, index generation, index state fingerprint, and input schemas. A missing or inconsistent input fails with corrective CLI guidance.

## Identity

Paths use forward slashes, omit empty segments, and are case-folded consistently across Windows, Linux, and macOS. Repository and workspace nodes use their stable identities. Structural nodes use repository identity plus normalized relative path. Technology nodes use normalized canonical names. Edges use SHA-256 over source ID, edge type, and target ID. Renamed files receive new path-derived IDs.

## Structural Resolution

Discovery application, service, and library boundaries are authoritative structural candidates. Indexed files use longest matching boundaries. Modules are bounded path groupings beneath known components or major repository directories, limited by `AERION_GRAPH_MAX_MODULE_DEPTH`. They are not Python packages, Java packages, namespaces, or semantic modules.

Root-level files are not forced into a generic root application. Uncertain ownership is reported as unassigned.

## Nodes And Edges

Nodes cover workspaces, repositories, applications, services, libraries, modules, directories, files, languages, frameworks, package managers, build systems, test frameworks, databases, manifests, declared dependencies, configuration, documentation, containers, Kubernetes, CI/CD, infrastructure, migrations, schemas, and unknown structural entities.

Edges express containment, file and module membership, application/service/library ownership, technology usage, manifest ownership, infrastructure/configuration association, and declared dependencies. Every edge records controlled evidence origin and confidence. Path rules are moderate; discovery boundaries are strong; manifest declarations and indexed file facts are explicit.

Declared dependencies contain only name, declared version, scope, ecosystem source manifest, and safe normalized metadata. Forge performs no registry access, transitive resolution, vulnerability analysis, or source-usage inference.

## Generations And Diffing

Milestone 1.4 performs a complete deterministic rebuild from persisted inputs, followed by canonical node and edge comparison. Changes include added, modified, removed, and unchanged nodes and edges. This is intentionally simpler and safer than partial graph mutation.

The graph-state fingerprint includes schema version, sorted node and edge representations, the portable discovery fingerprint, and the source index state fingerprint. It excludes timestamps, traversal order, absolute paths, reports, and persistence metadata. Unchanged states retain a logical generation ID and produce byte-identical second and later reports.

## Validation And Recovery

Validation rejects duplicate IDs, missing edge endpoints, self-edges, repository or workspace mismatches, stale index generation or state, missing roots, file/index mismatches, absolute portable paths, and incorrect statistics. Validation and report failures occur before atomic persistence, preserving the previous valid graph. Corrupt or incompatible persistence is never silently reset.

## Orphans

Reports identify disconnected nodes, files without a confident component, unknown-role files, manifests without application/service/library ownership, and components without manifests. Forge prefers incomplete truthful structure over speculative relationships.

## Query API

`KnowledgeGraphQuery` provides deterministic typed operations for node lookup, type filtering, incoming and outgoing edges, neighbors, component files, file ownership, component technologies, component manifests, declared dependencies, and orphan retrieval. It is internal and read-only; there is no query language, HTTP API, natural-language interface, or graph mutation.

## Performance And Limits

Graph construction is `O(N + E)` after sorting, with typed dictionaries for deduplication. Defaults are 100,000 nodes, 300,000 edges, module depth 2, and directory nodes enabled. Configure `AERION_GRAPH_MAX_NODES`, `AERION_GRAPH_MAX_EDGES`, `AERION_GRAPH_MAX_MODULE_DEPTH`, and `AERION_GRAPH_INCLUDE_DIRECTORY_NODES`.

## Safety

The graph uses persisted metadata only. It does not scan directories, reopen source files, parse protected files, expose fingerprints as contents, run tools, access networks, or modify target repositories. Portable reports contain normalized relative paths and no absolute user directories.

## Examples

- ERP and CRM monorepos: applications, backend services, shared libraries, manifests, dependencies, migrations, databases, CI/CD, and deployment configuration.
- GCS: frontend UI, backend/telemetry services, native modules, infrastructure, and configuration.
- Website: React or NextJS application structure, manifests, frameworks, tests, and deployment files.
- Flutter: mobile application, Dart files, assets, localization, tests, and manifests.
- PX4 or embedded: firmware and embedded areas, C/C++ files, build and infrastructure configuration.
- ROS2: robotics areas, indexed C++ or Python files, manifests, modules, and configuration without semantic ROS package parsing.

## Deferred Scope

No ASTs, imports, symbols, functions, classes, call graphs, API endpoints, database tables, ORM relationships, business workflows, semantic search, embeddings, LLMs, planning, execution, editing, generation, builds, tests, Git mutation, graph visualization, or external graph database are implemented.
