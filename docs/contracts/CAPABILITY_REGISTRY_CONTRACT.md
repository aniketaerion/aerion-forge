# Capability Registry Contract

Status: technically frozen by Milestone 1.5.4 validation. Schema version: `1.0`.

## Purpose And Boundaries

The registry is trusted, checked-in control-plane metadata describing Forge functionality. A
definition states intended behavior; implementation status states whether code exists; evaluation
states current availability. Registry construction executes no capability and performs no target
traversal, source reads, arbitrary imports, plugin loading, command execution, or network access.

## Frozen Contracts

The ID format is lowercase kebab-case. These implemented IDs are stable:
`workspace-management`, `repository-discovery`, `incremental-project-index`,
`engineering-knowledge-graph`, and `capability-registry`.

The registry identity is `aerion-forge-capability-registry`; schema `1.0`, persistence path
`memory/capabilities.json`, and the eight `CAPABILIT*`/`CAPABILITY_*` report names are stable.

Existing meanings of all `CapabilityCategory`, `CapabilityMaturity`, `CapabilityLifecycle`,
`CapabilityImplementationStatus`, `CapabilityAccessMode`, `CapabilityApprovalPolicy`,
`CapabilityAvailabilityScope`, `CapabilityInputType`, `CapabilityOutputType`,
`CapabilityChangeType`, and `CapabilityValidationSeverity` members are frozen. Additive members are
permitted.

Externally consumed fields of `CapabilityDefinition`, `CapabilityEvaluation`,
`CapabilityRegistry`, `CapabilityRegistryGeneration`, `CapabilityRegistryStatistics`,
`CapabilityRegistryChange`, `CapabilityRegistryChangeSet`, and `CapabilityRegistryResult` are
frozen for schema `1.0`.

The read-only query names and deterministic tuple-return behavior are frozen:
`get_capability`, `list_capabilities`, `list_available_capabilities`,
`list_planned_capabilities`, `get_capabilities_by_category`,
`get_capabilities_for_project_type`, `get_required_capabilities`,
`get_optional_capabilities`, `get_dependents`, `is_available`, `get_missing_requirements`,
`get_capability_outputs`, `get_capability_commands`, and `get_registry_summary`.

The commands `forge capabilities` and `forge capability <capability-id>` are frozen. Existing JSON,
availability, planning, category, project-type, and verbose filters remain backward compatible.

## Semantics

Required dependencies block availability; optional dependencies do not. Dependencies must exist,
must not be removed, and must form an acyclic directed graph. Implemented, enabled capabilities
become available only when every required dependency is available. Planned and removed capabilities
are unavailable. Disabled state propagates through required dependencies. Deprecated capabilities
may remain available and must report their lifecycle.

Fingerprints hash canonical schema, registry identity, sorted definitions, sorted evaluations, and
material configuration. Generation IDs are content-addressed from that fingerprint. Timestamps,
absolute paths, report destinations, process state, and declaration order are excluded.

## Failure And Migration Policy

Invalid definitions, dependency graphs, statistics, fingerprints, and generations prevent
persistence. Corrupt or unsupported store schemas fail explicitly; no implicit reset or executable
deserialization is permitted. Reports are staged before store replacement.

Frozen contracts may change only through a backward-compatible extension, explicit schema-version
increment with migration logic, a documented deprecation period, or a documented breaking release.

Private builders, renderer helpers, catalogue construction helpers, internal caching, private
utilities, and test fixture organization are not frozen.
