# Aerion Forge M5.3 — Autonomous Mission Orchestrator Architecture

## Status

Architecture Draft

## Purpose

M5.3 coordinates complete engineering missions across the M5.1 autonomous runtime and the M5.2 autonomous execution engine.

M5.1 governs mission state, authority, approval, events, and recovery.

M5.2 executes one approved step through a controlled tool gateway.

M5.3 is the orchestration layer that repeatedly selects, executes, validates, records, and advances bounded mission steps until the mission reaches a terminal state or requires human intervention.

## Architectural Boundary

M5.3 may:

- start or resume one mission;
- load the approved mission plan;
- select the next eligible step;
- create one execution request;
- invoke M5.2 for one bounded execution attempt;
- record outcomes and evidence;
- advance mission and step states;
- apply bounded retry, rollback, replan, pause, or escalation decisions;
- stop at approvals, policy boundaries, or exhausted budgets;
- persist orchestration checkpoints;
- resume safely after interruption.

M5.3 may not:

- bypass M5.1 authority or approval controls;
- invoke tools directly;
- execute multiple mutating steps concurrently;
- create unbounded autonomous loops;
- silently alter an approved plan;
- continue after invariant, scope, or rollback failure;
- push, merge, release, deploy, or migrate without explicit approval.

## Core Components

1. Mission Orchestration Request
2. Mission Session
3. Orchestration State Machine
4. Plan Loader
5. Step Coordinator
6. Execution Request Factory
7. Outcome Processor
8. Mission Progress Tracker
9. Budget Monitor
10. Recovery Coordinator
11. Approval Stop Gate
12. Session Checkpoint Store
13. Resume Service
14. Orchestration Journal
15. Mission Orchestrator Service
16. Reporting and CLI

## Orchestration Flow

```text
MISSION START OR RESUME
  -> LOAD MISSION SNAPSHOT
  -> VERIFY MISSION STATE
  -> LOAD APPROVED PLAN
  -> VERIFY PLAN VERSION
  -> SELECT NEXT ELIGIBLE STEP
  -> CHECK AUTHORITY AND APPROVAL
  -> CREATE EXECUTION REQUEST
  -> EXECUTE ONE STEP THROUGH M5.2
  -> PROCESS EXECUTION OUTCOME
  -> RECORD EVIDENCE AND EVENTS
  -> UPDATE STEP AND MISSION PROGRESS
  -> CHECK BUDGETS AND STOP CONDITIONS
  -> CONTINUE, RETRY, ROLLBACK, REPLAN, PAUSE, ESCALATE, OR COMPLETE
```

## Safety Principles

- One mission session per mission.
- One active step execution per mission.
- One repository writer at a time.
- Every iteration consumes an execution-cycle budget.
- Every state change is journaled.
- Approved plan versions are immutable.
- Resumption requires a verified session checkpoint.
- Human approval gates are hard stops.
- Terminal missions never resume.
- Failure is explicit; no silent continuation.