# Autonomous Runtime Authority Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## Authority levels

| Level | Name | Examples |
|---|---|---|
| A0 | READ | Read files, search, inspect Git |
| A1 | PLAN | Build context and plans, generate proposals |
| A2 | MODIFY | Write approved files and bounded patches |
| A3 | EXECUTE | Run approved local tools, builds, and tests |
| A4 | COMMIT | Create branches, stage, and commit locally |
| A5 | PUSH | Push approved branches or review artifacts |
| A6 | MERGE_RELEASE | Merge, tag, migrate, deploy, or release |

Default autonomous ceiling in M5.1 is A2. Allowlisted validation may receive A3. A4–A6 require explicit approval.

## Risk classes

| Risk | Description | Default handling |
|---|---|---|
| R0 | Read-only | Automatic |
| R1 | Documentation or isolated tests | Automatic with evidence |
| R2 | Bounded local implementation | Plan approval |
| R3 | API, schema, auth, finance, safety, architecture | Explicit step approval |
| R4 | Migration, deployment, push, release, destructive | Multi-stage approval |
| R5 | Production or safety-critical control | Human-controlled only |

## Approval scope

Approval may restrict mission, plan version, step, repository, paths, commands, authority ceiling, time window, attempts, network, branch, remote, or release target.

Approval becomes invalid after expiry, revocation, incompatible repository change, plan revision, scope expansion, authority increase, or risk increase.

## Mandatory explicit approval

- authentication or authorization changes;
- destructive database operations;
- public API changes;
- financial or safety-critical logic;
- weakening tests or validation;
- dependency installation;
- network access;
- commit, push, merge, tag, deploy, migrate, or release.

## Separation of duties

For R4 and R5, planner and approver are distinct roles, reviewer is read-only, and release approval is separate from implementation approval.