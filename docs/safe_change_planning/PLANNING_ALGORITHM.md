# Safe Change Planning Algorithm

## Inputs

- Change request
- Mission Plan
- Task Set
- Impact Assessment
- Engineering Memory
- Mission Report
- Execution Controller policies
- Repository discovery state
- Project index
- Knowledge graph
- Runtime configuration

## Planning sequence

1. Normalize the change request.
2. Validate source lineage.
3. Resolve selected tasks and objectives.
4. identify direct repository targets.
5. expand structural dependencies.
6. identify contracts, tests, documentation, configuration, and data impacts.
7. classify each target by action type.
8. calculate deterministic risk factors.
9. assign aggregate risk level.
10. determine approval requirements.
11. generate ordered implementation phases.
12. generate verification steps.
13. generate rollback steps.
14. generate traceability links.
15. validate plan invariants.
16. calculate plan identity and fingerprint.
17. render canonical artifacts.

## Target ordering

Targets are ordered by:

1. architecture and contract prerequisites,
2. data model changes,
3. backend implementation,
4. integration boundaries,
5. frontend or client changes,
6. tests,
7. documentation,
8. release and deployment preparation.

## Dependency expansion

Dependency expansion must be conservative and bounded. Unknown relationships are recorded as uncertainty and increase risk.

## Verification planning

Verification may include:

- Ruff
- MyPy
- unit tests
- integration tests
- contract tests
- migration dry runs
- build checks
- security checks
- regression tests
- manual acceptance tests

The planner describes verification. It does not execute it.

## Rollback planning

Rollback must identify:

- files or artifacts to restore,
- migrations to reverse or compensate,
- feature flags to disable,
- releases to revert,
- data backups required,
- irreversible operations.

## Failure handling

Invalid lineage, empty scope, impossible ordering, missing mandatory verification, and contradictory constraints must fail planning.
