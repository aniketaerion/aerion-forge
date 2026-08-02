# Unified Runtime Configuration

Diagnostics adds `diagnostics.enabled` (true), `diagnostics.strict` (true),
`diagnostics.history_limit` (5), `diagnostics.include_optional` (true), and
`diagnostics.write_probe_enabled` (true). Diagnostics never parses the environment directly.

Forge resolves typed settings through one precedence chain: defaults, profile, Forge TOML,
compatibility aliases, canonical `FORGE_` environment variables, then command-local `--set`
overrides. It never searches parent or target repositories, edits sources, loads plugins, executes
capabilities, or accesses networks.

Namespaces are `core`, `workspace`, `discovery`, `indexing`, `knowledge_graph`, `capabilities`,
`reporting`, `persistence`, `logging`, `security`, and `cli`. Profiles are `development`, `test`,
`production`, and `ci`. Explicit TOML tables match namespaces.

Parsing supports booleans, numbers, enums, lists, paths, byte sizes, durations, and optional values.
Bounds and cross-setting safety checks run before persistence. Writable paths remain Forge-relative;
production cannot disable redaction; fixed execution safety cannot be bypassed.

Resolved settings record safe value, provenance, profile, override state, sensitivity, validity,
restart requirement, and determinism impact. Sensitive raw values are excluded from representations,
serialization, reports, persistence, errors, and fingerprints and display as `********`.

Safe state is atomically stored at `memory/configuration.json`; six deterministic
`CONFIGURATION_*` reports are written under `reports/latest/`. Failures preserve prior valid state.

Use `forge config show`, `get`, `explain`, `validate`, `profiles`, and `fingerprint`. The immutable
`ConfigurationQuery` provides typed lookup and filtering. Existing `AERION_` variables remain
aliases; canonical `FORGE_` variables win. `Settings` remains the compatibility facade. Runtime
Live reload remains deferred; runtime health diagnostics are implemented in Phase 1.

## Mission Planning Settings

Milestone 2.1 adds the `planning` namespace.

| Key | Type | Default | Constraint |
|---|---|---:|---|
| `planning.enabled` | boolean | `true` | - |
| `planning.strict` | boolean | `false` | - |
| `planning.history_limit` | integer | `5` | 0-100 |
| `planning.max_affected_areas` | integer | `25` | 1-1000 |
| `planning.max_workstreams` | integer | `8` | 1-50 |
| `planning.max_assumptions` | integer | `12` | 1-100 |
| `planning.max_questions` | integer | `12` | 1-100 |
| `planning.require_current_graph` | boolean | `true` | - |
| `planning.allow_degraded_runtime` | boolean | `true` | - |

The runtime configuration catalogue now contains 49 settings, including
9 Mission Planning settings.

## Task Management Settings

Milestone 2.2 adds the `tasks` namespace.

| Key | Type | Default | Constraint |
|---|---|---:|---|
| `tasks.enabled` | boolean | `true` | - |
| `tasks.strict` | boolean | `false` | - |
| `tasks.history_limit` | integer | `5` | 0-100 |
| `tasks.max_tasks_per_mission` | integer | `250` | 1-5000 |
| `tasks.max_dependencies_per_task` | integer | `25` | 0-250 |
| `tasks.max_acceptance_criteria_per_task` | integer | `25` | 1-250 |
| `tasks.max_validation_requirements_per_task` | integer | `25` | 1-250 |
| `tasks.require_approved_mission` | boolean | `true` | - |
| `tasks.allow_blocked_tasks` | boolean | `true` | - |

The runtime configuration catalogue now contains 58 settings, including
9 Task Management settings.
