# M5.6 Autonomous Planning Data Model

## PlanningRequest

Immutable request describing:

- request ID;
- objective;
- repository root;
- intent;
- target paths;
- constraints;
- acceptance criteria;
- requested capabilities;
- creator;
- creation timestamp.

## PlanningStep

Immutable unit of planned engineering work.

Fields include:

- step ID;
- sequence;
- name and description;
- step kind;
- target paths;
- required capabilities;
- required tools;
- expected outputs;
- acceptance criteria;
- risk;
- approval requirement;
- destructive flag.

## PlanningDependency

Explicit relation between two planning steps.

Supported dependency kinds:

- requires;
- blocks;
- orders_after;
- optional.

Self-dependencies are invalid.

## PlanningPlan

Immutable versioned plan containing:

- plan ID;
- request ID;
- version;
- planning state;
- summary;
- ordered steps;
- dependencies;
- aggregate risk;
- approval requirement;
- warnings;
- timestamps.

A plan must contain at least one step, unique step identifiers, sequence-ordered steps, and dependencies referencing known steps.

## PlanningSession

Tracks request state, current plan identity/version, failure reason, and timestamps.

## PlanningValidationFinding

Records severity, code, message, optional step reference, and blocking status.

## PlanningValidationResult

A valid plan may not contain blocking findings.