# Aerion Forge v0.2.0 — Engineering Runtime

Aerion Forge v0.2 completes Phase 1: a deterministic local runtime for registering Aerion
software workspaces, discovering repository structure, maintaining an incremental technical
index, building a structural knowledge graph, declaring capabilities, resolving unified runtime
configuration, and diagnosing operational readiness.

## Added

- Workspace registration, activation, persistence, and consistent target resolution.
- Bounded manifest-first repository discovery and deterministic reports.
- Incremental indexing with protected/bounded fingerprints and safe rename detection.
- A validated structural Engineering Knowledge Graph with stable node and edge identities.
- A static typed Capability Registry with lifecycle, dependencies, access, and approval metadata.
- Unified typed configuration with profiles, precedence, provenance, validation, and redaction.
- Runtime health and target diagnostics with consistency, staleness, and corrective guidance.
- Phase 1 validation evidence, architecture freeze, schema inventory, and release manifest.

## Implemented capabilities

`workspace-management`, `repository-discovery`, `incremental-project-index`,
`engineering-knowledge-graph`, `capability-registry`, `runtime-configuration`,
`runtime-health-diagnostics`, and `phase-validation-release` are stable and available.

## Safety and compatibility

Repository understanding is target-read-only. Forge does not edit code, run target builds/tests,
repair state automatically, depend on a network, load external plugins dynamically, or expose
secrets. Supported repository families include ERP, CRM, websites, React/Node services, Flutter,
GCS, PX4, ROS2, firmware, embedded, Python, C/C++, Rust, Go, and Java shapes.

## Limitations

This release does not provide semantic source analysis, AST/import graphs, API extraction,
business workflow analysis, planning, execution, code editing, test generation, or ERP domain
intelligence. Manifest dependencies remain declaration-level structural evidence.

## Next phase

Phase 2 — Engineering Planning. No Phase 2 behavior is included in v0.2.
