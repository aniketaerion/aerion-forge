# Safe Change Planning Data Model

## Entities

### ChangeRequest

Defines the requested engineering change, mission lineage, task scope, constraints, requested outcomes, and source fingerprints.

### ChangeTarget

Represents one file, module, package, service, database object, interface, configuration item, document, or test target.

### ChangeAction

Describes a planned action without performing it.

### DependencyImpact

Records direct and transitive dependency effects.

### RiskFactor

Represents one evidence-backed contributor to risk.

### ChangeRiskAssessment

Contains aggregate risk level, score, reasons, approval requirements, and mitigations.

### VerificationStep

Defines a planned static check, test, build, inspection, review, or acceptance action.

### RollbackStep

Defines how a proposed change can be safely reverted.

### ChangePhase

Groups ordered actions into preparation, implementation, verification, and release phases.

### SafeChangePlan

The immutable top-level planning artifact.

### PlanningValidationFinding

Represents an error or warning discovered during validation.

### PlanningValidationResult

Represents the deterministic validation outcome.

## Invariants

- All identity fields are non-blank.
- All collections are normalized and deterministically ordered.
- Duplicate targets, actions, dependencies, verification steps, and rollback steps are forbidden.
- Every action must reference a declared target.
- Every high-risk action must reference at least one mitigation.
- Every mutating action must have at least one verification step.
- Every destructive or irreversible action must have a rollback limitation or rollback step.
- Plan statistics must match contained entities.
- Final fingerprints must exclude their own existing fingerprint values.
- Source fingerprints must be immutable.
- Planned actions must never contain claims of completed execution.
- The plan must preserve Mission, Task, Impact, Memory, Reporting, and repository lineage.

## Serialization

Models serialize to canonical JSON with sorted mapping keys and stable tuple ordering.

## Immutability

All domain models are frozen after validation.
