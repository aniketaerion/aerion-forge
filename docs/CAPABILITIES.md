# Capability Registry

Phase 1 release validation promotes `phase-validation-release` to stable and available. The
registry remains 31 total: 8 implemented/available and 23 planned/unavailable. Release validation
produces deterministic evidence only; it cannot commit, tag, push, publish, or deploy.

The Capability Registry is Forge's deterministic control-plane contract. It describes what Forge
can do; it never executes capabilities, traverses targets, loads plugins, or infers features from
installed modules.

Each static `CapabilityDefinition` declares a canonical ID, version and milestone, category,
lifecycle, implementation status, maturity, supported workspace project types, dependencies, typed
inputs and outputs, CLI metadata, access mode, approval policy, availability scope, documentation,
and limitations. A separate `CapabilityEvaluation` records current availability and reasons without
mutating its definition.

Lifecycle values are `planned`, `implemented`, `available`, `partially_available`, `disabled`,
`deprecated`, and `removed`. Implementation status is independent. Access modes distinguish
read-only behavior, Forge-controlled persistence, target mutation, and external side effects.
Planned mutating features declare approval requirements, but no approval workflow is implemented.

Completed entries are `workspace-management`, `repository-discovery`,
`incremental-project-index`, `engineering-knowledge-graph`, and `capability-registry`. Planned,
unavailable examples include `mission-planning`, `safe-code-editing`, and `erp-module-analysis`.

## Evaluation And Validation

Evaluation checks implementation, lifecycle, local disable configuration, then required
dependencies. An unavailable required dependency makes its dependent unavailable; optional
dependencies do not. Uncertain states fail closed. Validation rejects malformed or duplicate IDs,
unknown/self dependencies, cycles, inconsistent availability, unsafe approval metadata, incorrect
statistics, schema mismatches, and fingerprint inconsistencies.

Definitions, configuration, and evaluations are canonically sorted and hashed with SHA-256.
Fingerprints and generation IDs exclude timestamps, absolute paths, and process state.

## Configuration And Persistence

The existing `AERION_` namespace provides registry enablement, comma-separated disabled IDs,
planned-entry inclusion, strict validation, and bounded history. Unknown disabled IDs fail in strict
mode. Disabling a required capability propagates unavailability.

The global registry is atomically stored at `memory/capabilities.json`. Corrupt or unknown-schema
state raises an explicit error and is never reset silently. Validation and report failures occur
before store replacement. Reports under `reports/latest/` include capability, summary, change,
dependency, and roadmap JSON and Markdown views.

## CLI And Query API

Use `forge capabilities` with `--json`, `--available`, `--planned`, `--category`,
`--project-type`, or `--verbose`. Use `forge capability <canonical-id>` for details.
`CapabilityRegistryQuery` provides typed lookup, filtering, dependency, dependent, missing
requirement, output, command, and summary operations.

Future planners and execution controllers may consult this registry. Mission planning, code editing,
test generation, ERP analysis, dynamic plugins, networks, and capability execution remain out of
scope.

The final v0.2 inventory is eight implemented/available and 23 planned/unavailable.

## Errors And Contract Stability

Explicit exception types cover definition, dependency, cycle, configuration, validation,
persistence, reporting, corruption, disabled, and unknown-ID failures. Unsupported schemas are never
silently reset. Report staging completes before persistence, preserving the prior valid store.

Schema `1.0`, public model fields, query behavior, CLI compatibility, and migration policy are frozen
in `docs/contracts/CAPABILITY_REGISTRY_CONTRACT.md`. The registry remains global, the catalogue is
trusted checked-in code, and availability is target-independent.

## Errors And Contract Stability

Explicit exception types cover definition, dependency, cycle, configuration, validation,
persistence, reporting, corruption, disabled, and unknown-ID failures. Unsupported schemas are never
silently reset. Report staging completes before persistence, preserving the prior valid store.

Schema `1.0`, public model fields, query behavior, CLI compatibility, and migration policy are frozen
in `docs/contracts/CAPABILITY_REGISTRY_CONTRACT.md`. The registry remains global, the catalogue is
trusted checked-in code, and availability is target-independent.

## Errors And Contract Stability

Definition, dependency, cycle, configuration, validation, persistence, report, corruption, disabled,
and unknown-ID failures use explicit exception types. Corrupt and unsupported schemas are never
silently reset. Report staging completes before registry persistence, preserving the previous valid
store when rendering fails.

Schema `1.0` stability, public model fields, query behavior, CLI compatibility, and migration policy
are frozen in `docs/contracts/CAPABILITY_REGISTRY_CONTRACT.md`. Known limitations remain: the
registry is global, the catalogue is trusted checked-in code, and availability is target-independent.
