# M5.6 Autonomous Planning Engine Architecture

## Purpose

M5.6 converts an engineering objective into a deterministic, validated, dependency-aware engineering plan that can later be approved and executed by M5.7.

M5.6 is a planning subsystem. It does not directly edit source files, execute tools, perform Git operations, or bypass approval controls.

## Architectural Position

Inputs:

- repository root and repository fingerprint;
- engineering objective;
- planning intent;
- repository-grounded capabilities;
- architecture and operational constraints;
- evidence and memory references.

Outputs:

- immutable planning request;
- immutable planning plan;
- ordered planning steps;
- dependency graph;
- risk and approval requirements;
- validation findings;
- approved/rejected plan lifecycle state.

## Core Components

1. Planning contracts
2. Deterministic identifiers
3. Planning state model
4. Planning policy
5. Repository/context analysis
6. Step synthesis
7. Dependency synthesis
8. Dependency graph and cycle detection
9. Ordering and eligibility
10. Plan generation
11. Plan validation
12. Approval and revision
13. Planning repository
14. Planning service
15. Reporting and CLI integration

## Safety Boundary

M5.6 may describe code-changing, release, migration, test, validation, documentation, and approval work, but it may not execute that work.

Destructive steps must carry an explicit approval requirement.

Plans with blocking validation findings are not executable.

## Determinism

For identical planning request and planning context, M5.6 must produce deterministic:

- request identifiers;
- plan identifiers;
- step identifiers;
- dependency identifiers;
- dependency ordering;
- risk classification;
- approval requirements;
- validation findings.

## Compatibility

M5.6 must preserve existing Forge repository understanding, capability, memory, decision, orchestration, and tool-safety contracts.

M5.7 consumes approved M5.6 plans as its source of executable work.