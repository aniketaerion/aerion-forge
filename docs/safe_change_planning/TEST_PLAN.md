# Safe Change Planning Test Plan

## Test layers

### Model tests

Validate normalization, immutability, canonical serialization, invariants, statistics, and rejection of invalid plans.

### Identifier tests

Validate deterministic IDs and fingerprints.

### Risk tests

Validate deterministic scoring, risk escalation, mandatory approval rules, and conservative unknown handling.

### Validator tests

Validate lineage, target scope, dependency integrity, verification coverage, rollback coverage, and strict-mode behaviour.

### Builder tests

Validate deterministic construction, ordering, phase creation, traceability, verification generation, and rollback generation.

### Renderer tests

Validate canonical JSON, Markdown, report suites, atomic writes, overwrite behaviour, and rollback on failure.

### Service tests

Validate orchestration, dependency injection, persistence, validation, error propagation, and non-mutation.

### CLI tests

Validate help contract, registration, plan creation, validation, display, listing, JSON output, exit codes, and missing or corrupted artifacts.

### Capability tests

Validate catalogue truth, implemented status, commands, inputs, outputs, documentation, and counts.

### Repository regression tests

Run the complete existing Forge suite.

## Safety tests

- Planner performs no source mutation.
- Planner performs no tool dispatch.
- Planner performs no Git mutation.
- Planner performs no build or test execution.
- High and critical risk rules cannot be bypassed.
- Unknown dependencies increase risk.
- Missing verification prevents a valid executable plan.
- Missing rollback is surfaced.
- Approval requirements are deterministic.
- Existing persisted artifacts are preserved on report failure.

## Minimum evidence

- Ruff clean
- MyPy clean
- All M3.2 tests passing
- Full repository tests passing
- Architecture validation passing
- Git diff check clean
