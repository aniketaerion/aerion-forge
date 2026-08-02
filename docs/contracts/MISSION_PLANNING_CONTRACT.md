# Mission Planning Contract

## Identity

- Product: Aerion Forge
- Subsystem: `forge.planning`
- Capability: `mission-planning`
- Forge version: `0.3`
- Phase: `2`
- Milestone: `2.1`
- Schema: `1.0`
- Access mode: `read_only`

## Objective

Convert an engineering request into a deterministic mission-level plan using
persisted Phase 1 evidence.

## Public Command

    forge mission plan <request> [OPTIONS]

Supported options:

- `--target`
- `--json`
- `--summary`
- `--context`
- `--risks`
- `--assumptions`
- `--questions`
- `--strict`
- `--no-persist`

## Public Models

- `EngineeringRequest`
- `NormalizedEngineeringRequest`
- `MissionPlan`
- `MissionPlanGeneration`
- `MissionPlanChangeSet`
- `MissionPlanResult`
- `MissionPlanningConfiguration`
- `MissionValidationResult`
- `PlanningContext`

## Context Contract

Mission Planning must not:

- Traverse the target repository
- Reopen source files
- Parse source code
- Execute subprocesses
- Access the network
- Automatically invoke another capability
- Modify the target repository

## Graph Freshness

A graph is current only when:

1. Its source index generation matches the current index generation.
2. Its source index fingerprint matches the current repository-state fingerprint.

## Persistence

Canonical store:

    memory/missions.json

Persistence requirements:

- Atomic replacement
- Schema validation
- Explicit corruption handling
- Explicit schema mismatch handling
- Bounded history
- Previous-state restoration on report failure
- No writes under `--no-persist`

## Reports

Canonical reports:

- `MISSION_PLAN.json`
- `MISSION_SUMMARY.json`
- `MISSION_CONTEXT.json`
- `MISSION_RISKS.json`
- `MISSION_ASSUMPTIONS.json`
- `MISSION_QUESTIONS.json`
- `MISSION_CHANGES.json`
- `MISSION_PLAN.md`
- `MISSION_SUMMARY.md`

## Change Semantics

- First persisted plan: `created`
- Repeated identical plan: `unchanged`
- Same mission identity with changed fingerprint: `updated`

## CLI Exit Codes

- `0`: ready or successful informational command
- `2`: invalid request or target
- `3`: ready with conditions
- `4`: blocked
- `5`: invalid plan
- `6`: planning disabled
- `7`: context failure
- `8`: general planning failure
- `9`: validation failure
- `10`: persistence failure
- `11`: report failure
- `12`: corrupt store
- `13`: schema mismatch

## Frozen Boundary

Milestone 2.1 does not perform task execution, source editing, target builds,
target tests, migrations, Git mutation, deployment, automatic remediation,
multi-agent coordination, or cloud synchronization.

## Compatibility

Historical Forge v0.2 Phase 1 inventory:

- 8 implemented
- 23 planned

Current Forge v0.3 Milestone 2.1 inventory:

- 9 implemented
- 22 planned
