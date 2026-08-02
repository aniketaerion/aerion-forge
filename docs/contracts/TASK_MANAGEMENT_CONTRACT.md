# Task Management Contract

## Identity

- Product: Aerion Forge
- Subsystem: `forge.tasks`
- Capability: `task-management`
- Forge version: `0.3`
- Phase: `2`
- Milestone: `2.2`
- Schema: `1.0`
- Access mode: `forge_internal_write`

## Objective

Convert a persisted Mission Plan into a deterministic, validated and
reviewable engineering task graph.

## Public Commands

    forge task build <mission-id>
    forge task list
    forge task show <task-id>

## Persistence

Canonical store:

    memory/tasks.json

Persistence must use schema validation, atomic replacement, bounded history
and rollback when report generation fails.

## Reports

- `TASK_PLAN.json`
- `TASK_SUMMARY.json`
- `TASK_CHANGES.json`
- `TASK_PLAN.md`
- `TASK_SUMMARY.md`

## Frozen Boundary

Milestone 2.2 does not perform task execution, scheduling, automatic
assignment, source editing, target builds, target tests, database migration,
Git mutation, deployment or autonomous remediation.
