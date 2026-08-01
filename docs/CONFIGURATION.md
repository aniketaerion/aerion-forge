# Unified Runtime Configuration

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
health diagnostics and live reload remain Milestone 1.7 scope.
