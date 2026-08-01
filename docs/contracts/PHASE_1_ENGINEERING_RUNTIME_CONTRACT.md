# Phase 1 Engineering Runtime Contract

## Mission and boundary

Aerion Forge v0.2 is a local Engineering Runtime for deterministic, read-only repository
understanding and operational-readiness evidence. Phase 1 does not plan missions, edit code,
execute builds or target tests, perform ERP analysis, repair state, orchestrate agents, load
external plugins, or provide cloud/remote services.

## Stable architecture

```text
Workspace → Discovery → Incremental Index → Knowledge Graph → Diagnostics
                    Configuration and Capability Registry
             Shared Repository Policy, Persistence, Reporting
```

Each subsystem owns its models, service, persistence, renderer, errors, and public query surface.
Stores never overwrite another subsystem's file. Generated `memory/` and `reports/` artifacts
are excluded from discovery, indexing, and graph inputs.

## Frozen public contracts

- Workspace: workspace IDs and fields, `ProjectType`, explicit/active/current resolution order,
  `memory/workspaces.json`, and `forge workspace` behavior.
- Discovery: `DiscoveryResult`, deterministic direct/workspace identity, bounded manifest-first
  inspection, `memory/discovery.json`, report names, and `forge inspect` behavior.
- Index: schema 1.0, file/index statuses, change meanings, bounded fingerprint strategies,
  `memory/index.json`, report names, and `forge index` behavior.
- Knowledge graph: schema 1.0, public node/edge types and stable IDs, structural-only semantics,
  query names, `memory/knowledge_graph.json`, report names, and `forge graph` behavior.
- Capability Registry: schema 1.0, canonical 31-entry catalogue, lifecycle/availability/access/
  approval semantics, query names, `memory/capabilities.json`, and capability CLI behavior.
- Configuration: schema 1.0, dotted keys, profiles, precedence, provenance, `********` redaction,
  query names, `memory/configuration.json`, report names, and `forge config` behavior.
- Diagnostics: schema 1.0, kebab-case check IDs, statuses, severity, criticality, aggregation,
  advisory actions, query names, `memory/diagnostics.json`, reports, `health`, and `diagnose`.
- Repository policy: the shared excluded-directory set and refusal to follow external symlinks.

## Schema and persistence inventory

| Subsystem | Schema | Persistence | Compatibility |
|---|---:|---|---|
| Workspace | legacy 1.0 | `memory/workspaces.json` | Existing shape frozen; breaking changes require migration |
| Discovery | legacy 1.0 | `memory/discovery.json` | Existing shape frozen; breaking changes require migration |
| Index | 1.0 | `memory/index.json` | Unsupported schema/corruption is explicit |
| Knowledge Graph | 1.0 | `memory/knowledge_graph.json` | Unsupported schema/corruption is explicit |
| Capabilities | 1.0 | `memory/capabilities.json` | Unsupported schema/corruption is explicit |
| Configuration | 1.0 | `memory/configuration.json` | Unsupported schema/corruption is explicit |
| Diagnostics | 1.0 | `memory/diagnostics.json` | Unsupported schema/corruption is explicit |

Workspace and Discovery predate explicit top-level schema fields. Their current persisted shapes
are treated as legacy 1.0 for v0.2 compatibility; adding explicit version envelopes is deferred to
a migration milestone rather than risk a release-time compatibility break.

All writes are Forge-controlled and atomic where the owning subsystem writes state. Previous
valid state is preserved on validation, rendering, or replacement failure. History is bounded
where the subsystem contract provides history.

## Stable report and CLI families

Report families are Discovery, Index, Knowledge Graph, Capabilities, Configuration, Diagnostics,
and the Phase 1 release manifest. Stable CLI families are `workspace`, `inspect`, `index`,
`graph`, `capabilities`, `capability`, `config`, `health`, and `diagnose`.

## Security and determinism guarantees

Repository understanding is local and target-read-only. Sensitive files are protected; secrets,
environment dumps, source content, private portable paths, clocks, host/user/process identity,
and temporary probe names are excluded from deterministic evidence. Understanding workflows do
not use network, subprocesses, arbitrary imports, or external plugins.

Equivalent safe input produces stable identities, fingerprints, generations, ordering, and
reports. Exact timing is never part of a deterministic contract.

## Private and unfrozen implementation

Internal helper names, traversal implementation, private renderer layout, logging text, and
performance tuning are unfrozen provided public behavior remains compatible. Legacy `agents`,
`planner`, `runtime`, `tools`, `plugins`, and `prompts` modules remain compatibility scaffolding;
they are not Phase 1 capabilities and cannot be activated implicitly by Phase 1 workflows.

Phase 2 may consume only documented, read-only Phase 1 contracts. Any breaking schema or public
contract change requires explicit versioning, migration guidance, compatibility validation, and
release authorization.
