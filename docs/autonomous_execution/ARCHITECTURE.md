# Aerion Forge M5.2 — Autonomous Execution Engine Architecture

## Status

Architecture Draft

## Purpose

M5.2 converts the governed M5.1 autonomous-runtime control plane into a bounded execution engine that can execute approved engineering mission steps without unrestricted autonomy.

## Architectural Boundary

M5.2 may:

- execute one approved step at a time;
- invoke registered tools through a controlled gateway;
- create and verify checkpoints;
- collect structured execution evidence;
- stop, retry, replan, roll back, pause, or escalate;
- persist execution state and events;
- support dry-run and simulation modes.

M5.2 may not:

- bypass M5.1 authority checks;
- execute arbitrary shell commands;
- mutate files outside approved scope;
- push, merge, deploy, release, or migrate without explicit approval;
- run unbounded autonomous loops;
- conceal tool inputs, outputs, or affected files.

## Core Components

1. Execution Request
2. Step Eligibility Evaluator
3. Execution Lease Manager
4. Controlled Tool Gateway
5. Tool Registry
6. Step Executor
7. Evidence Collector
8. Checkpoint Coordinator
9. Execution Journal
10. Failure Classifier
11. Recovery Coordinator
12. Autonomous Execution Service
13. Read-only CLI and reporting

## Execution Flow

```text
MISSION APPROVED
  -> STEP SELECTED
  -> ELIGIBILITY CHECKED
  -> AUTHORITY CHECKED
  -> APPROVAL CHECKED
  -> EXECUTION LEASE ACQUIRED
  -> CHECKPOINT VERIFIED
  -> TOOL INVOCATION PREPARED
  -> TOOL EXECUTED
  -> EFFECTS VERIFIED
  -> EVIDENCE RECORDED
  -> STEP COMPLETED OR RECOVERY SELECTED
```

## Safety Principles

- Single active writer per mission repository.
- One tool invocation at a time.
- Every mutation has an approved scope.
- Every mutating step requires a verified checkpoint.
- Every tool invocation has a deterministic identifier.
- Every result records affected files and evidence.
- Every retry consumes a finite budget.
- Every failure maps to an explicit recovery decision.
- Execution is offline by default.
- Dry-run is the default mode for CLI operations.