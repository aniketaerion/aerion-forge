# Aerion Forge Mission Planning

## Purpose

The Mission Planning Engine converts an engineering request into a deterministic,
reviewable, evidence-grounded mission plan.

Milestone 2.1 is planning-only. It does not modify source code, run target tests,
execute builds, perform migrations, mutate Git, deploy software, or perform
automatic remediation.

## Command

    forge mission plan "Complete Procurement Module" --target ERP

Options:

- `--target`
- `--json`
- `--summary`
- `--context`
- `--risks`
- `--assumptions`
- `--questions`
- `--strict`
- `--no-persist`

## Inputs

Mission Planning consumes persisted Forge-owned evidence:

- Workspace state
- Repository discovery
- Incremental project index
- Engineering knowledge graph
- Runtime configuration
- Capability Registry
- Runtime diagnostics
- Engineering request

It does not independently traverse or parse the target repository.

## Outputs

When persistence is enabled:

- `memory/missions.json`
- `reports/latest/MISSION_PLAN.json`
- `reports/latest/MISSION_SUMMARY.json`
- `reports/latest/MISSION_CONTEXT.json`
- `reports/latest/MISSION_RISKS.json`
- `reports/latest/MISSION_ASSUMPTIONS.json`
- `reports/latest/MISSION_QUESTIONS.json`
- `reports/latest/MISSION_CHANGES.json`
- `reports/latest/MISSION_PLAN.md`
- `reports/latest/MISSION_SUMMARY.md`

With `--no-persist`, no mission files or reports are written.

## Planning Status

Controlled statuses:

- `ready`
- `ready_with_conditions`
- `blocked`
- `invalid`
- `draft`
- `superseded`

A mission is blocked when required evidence is missing, stale, inconsistent, or
unavailable.

## Readiness

The planner checks:

- Target resolution
- Discovery availability
- Index availability
- Knowledge-graph freshness
- Target diagnostic identity
- Runtime health
- Required capability availability

A graph is current only when its source index generation and source index
fingerprint match the current project index.

## Risk and Approvals

Mission Planning assigns a controlled risk level and may require:

- Review approval
- Architecture approval
- Security approval
- Domain-owner approval
- Data-migration approval
- High-risk approval
- Release approval

It identifies approval requirements but cannot grant approval.

## Determinism

Equivalent normalized requests with identical persisted context produce the same:

- Mission ID
- Mission fingerprint
- Generation ID
- Plan content

The first persisted result is `created`. Repeated identical results are
`unchanged`.

## Safety Boundary

Milestone 2.1 excludes:

- Source-code modification
- Patch generation
- Target build execution
- Target test execution
- Database migration execution
- Git mutation
- Deployment
- Automatic remediation

## Milestone Identity

- Forge version: `0.3`
- Phase: `2`
- Milestone: `2.1`
- Capability ID: `mission-planning`
