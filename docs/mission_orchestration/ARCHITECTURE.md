# M3.6 Engineering Mission Orchestration Architecture

## Objective

Connect the released M3.1–M3.5 capabilities into one deterministic, resumable and auditable engineering mission workflow.

## Pipeline

1. Mission validation.
2. Execution request.
3. Safe Change Planning.
4. Impact assessment.
5. Approval gate.
6. Safe-edit dry-run.
7. Safe-edit apply.
8. Validation.
9. Autonomous repair when required.
10. Final validation.
11. Mission reporting.

## Safety boundary

M3.6 v1 does not permit autonomous Git commits, Git merges, dependency installation, arbitrary shell execution, silent approval or unbounded retry loops.