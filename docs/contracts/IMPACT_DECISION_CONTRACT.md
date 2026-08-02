# Impact Decision Contract

Capability: impact-decision-engine
Milestone: 2.3
Forge version: 0.3

## Objective

Convert a persisted Mission Plan and persisted Task Set into a deterministic,
validated Impact Assessment and controlled engineering recommendation.

## Preconditions

- Mission Plan exists in persistence.
- Task Set exists for the same mission.
- Mission identifiers and fingerprints match.
- Task identifiers are unique.
- At least one engineering task exists.
- Task data satisfies the Task Management contract.

## Processing Contract

1. Load the persisted Mission Plan.
2. Load the persisted Task Set.
3. Reconstruct the Task Set without rebuilding it.
4. Generate deterministic findings.
5. Derive severity and decision status.
6. Generate controlled decision options.
7. Generate approval and validation requirements.
8. Calculate deterministic statistics.
9. Generate deterministic identifiers and fingerprints.
10. Validate the assessment.
11. Persist and report transactionally when enabled.

## Persistence

Store: memory/impact-decisions.json

Persistence uses canonical UTF-8 JSON, deterministic ordering, atomic
replacement, bounded history, post-write verification, and rollback.

## Reports

- IMPACT_ASSESSMENT.json
- IMPACT_DECISION.json
- IMPACT_EVIDENCE.json
- IMPACT_SUMMARY.md

## Safety Boundary

The capability performs analysis and Forge-internal persistence only. It
does not execute engineering work, modify target source files, run builds
or tests, mutate Git, deploy software, or grant approvals.
