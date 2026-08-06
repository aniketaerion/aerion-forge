# M5.7 Autonomous Execution Engine Architecture

## Purpose

M5.7 converts validated autonomous plans into governed execution runs. It does not replace the M5.2 tool gateway or M5.3 mission orchestrator. It coordinates them through explicit execution contracts, policy checks, leases, evidence, recovery, and completion reporting.

## Architectural Position

Inputs:

- approved M5.6 planning plans;
- M5.4 decision outputs;
- M5.5 memory context;
- M5.3 orchestration sessions;
- M5.2 controlled tool execution.

Outputs:

- immutable execution runs;
- step attempts;
- evidence records;
- recovery decisions;
- execution reports;
- validated completion state.

## Components

1. Execution contracts
2. Run lifecycle
3. Step scheduler
4. Execution coordinator
5. Policy and authority checks
6. Attempt journal
7. Evidence capture
8. Retry and recovery controller
9. Completion validator
10. CLI and reporting integration

## Safety Boundary

The engine may execute only approved planning steps. Every tool invocation must pass through the existing controlled tool gateway. Destructive execution remains forbidden unless policy and authority explicitly allow it.

## Determinism

Identifiers, ordering, dependency evaluation, retry decisions, and reports must be deterministic for identical inputs.

## Compatibility

M5.7 must preserve all existing M5.1-M5.6 contracts and CLI namespaces.