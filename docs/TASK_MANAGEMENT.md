# Aerion Forge Task Management

## Purpose

Milestone 2.2 converts a persisted Mission Plan into a deterministic,
validated engineering task graph.

## Commands

    forge task build <mission-id>
    forge task list
    forge task show <task-id>

## Inputs

- Persisted Mission Plan
- Task Management configuration

## Outputs

- `memory/tasks.json`
- `reports/latest/TASK_PLAN.json`
- `reports/latest/TASK_SUMMARY.json`
- `reports/latest/TASK_CHANGES.json`
- `reports/latest/TASK_PLAN.md`
- `reports/latest/TASK_SUMMARY.md`

## Safety Boundary

Task Management does not execute tasks, modify source code, run builds or
tests, perform migrations, mutate Git, deploy software, schedule work,
automatically assign owners, or perform autonomous remediation.

## Milestone Identity

- Forge version: `0.3`
- Phase: `2`
- Milestone: `2.2`
- Capability ID: `task-management`
