# Runtime Health & Diagnostics

Milestone 1.7 adds local, on-demand diagnosis of Forge and persisted repository-understanding
state. It never repairs state, traverses target source, executes target code, loads plugins, uses
the network, or invokes `inspect`, `index`, or `graph` automatically.

`forge health` checks the Python runtime, Forge root, approved imports, configuration,
Forge-controlled directories, capability registry, workspace store, exclusions, and redaction.
`forge diagnose [TARGET]` resolves an explicit workspace/path, active workspace, then current
directory and checks discovery, index, graph, identities, fingerprints, freshness, and required
capabilities. Both accept `--json`, `--summary`, `--verbose`, `--category`, `--check`, and
`--strict`.

Statuses are `healthy`, `degraded`, `unhealthy`, `unknown`, `not_applicable`, and `skipped`.
Severity is independent; criticality is required, recommended, or optional. Required unhealthy
or blocking results make a run unhealthy; required unknown results make it unknown; recommended
non-healthy results degrade it. Skipped checks never improve status.

Exit codes are 0 healthy/non-blocking, 2 invalid input, 3 degraded, 4 unhealthy, 5 strict
unknown, 6 disabled, 7 execution failure, 8 validation failure, 9 persistence failure,
10 report failure, 11 corrupt store, and 12 unsupported schema.

The 30 checks are explicit in `forge/diagnostics/definitions.py`. Prerequisites form a validated
acyclic graph. Evidence is safe and sorted; sensitive evidence is redacted. Corrective actions
are manual, advisory, non-destructive, and never executed. Graph staleness requires a persisted
index generation/fingerprint mismatch; other freshness remains unknown unless state proves it.
Repository and workspace identities are compared across stores.

Schema 1.0 state is atomically stored in `memory/diagnostics.json` with bounded, isolated
runtime/target history. Reports are `RUNTIME_HEALTH.json`, `RUNTIME_HEALTH_SUMMARY.md`,
`DIAGNOSTIC_RESULTS.json`, `DIAGNOSTIC_SUMMARY.json`, `DIAGNOSTIC_SUMMARY.md`,
`DIAGNOSTIC_ACTIONS.json`, and `DIAGNOSTIC_CHANGES.json`. Artifacts exclude timestamps, secrets,
source, probe names, and private paths; shared policy excludes `memory/` and `reports/`.

Settings are `diagnostics.enabled`, `diagnostics.strict`, `diagnostics.history_limit`,
`diagnostics.include_optional`, and `diagnostics.write_probe_enabled`. Disabled probes make write
health unknown. `DiagnosticQuery` provides immutable typed access to checks, results, filters,
actions, summary, statistics, fingerprint, generation, changes, and readiness.

Diagnostics bootstraps through static configuration and capability definitions and does not need
its own prior health result. This milestone excludes remediation, monitoring, telemetry,
alerting, external probes, planning, editing, execution, test generation, Phase 1.8 automation,
and Phase 2 behavior.
