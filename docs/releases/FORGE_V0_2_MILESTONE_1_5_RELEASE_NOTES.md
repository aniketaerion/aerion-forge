# Aerion Forge v0.2 Milestone 1.5 Release Notes

## Added

- Static, typed Capability Registry and approved roadmap catalogue
- Capability dependency validation and fail-closed availability evaluation
- Deterministic schema `1.0` persistence, generation identity, fingerprints, changes, and reports
- Read-only typed query API
- `forge capabilities` and `forge capability <capability-id>` CLI contracts
- Shared exclusion of Forge-controlled `memory/` and `reports/` artifacts
- Contract, architecture-freeze, audit, hardening, and compatibility documentation

## Implemented And Available

`workspace-management`, `repository-discovery`, `incremental-project-index`,
`engineering-knowledge-graph`, and `capability-registry`.

## Planned And Unavailable

The remaining 26 approved roadmap capabilities are visible for planning but remain explicitly
unimplemented and unavailable. Planned capabilities expose no executable commands or generated
outputs. Future mutating capabilities declare approval requirements.

## Safety

The registry performs no dynamic loading, arbitrary imports, capability execution, target traversal,
source mutation, command execution, network access, plugin loading, Git mutation, or external
catalogue ingestion. Portable state and reports exclude secrets, raw environment data, timestamps,
and private absolute paths.

## Compatibility

Workspace management, discovery, indexing, structural knowledge graph, audit, runtime, plugins,
tools, memory, and existing CLI behavior remain compatible. The complete 118-test suite passes.

## Deferred

Runtime configuration and diagnostics remain Milestone 1.6 work. Mission planning, task management,
execution, code editing, build/test automation, ERP intelligence, dynamic plugins, agent frameworks,
and cloud services remain later roadmap scope.
