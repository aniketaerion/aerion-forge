# Aerion Forge M5.4 — Autonomous Decision Engine Architecture

## Status

Architecture Draft

## Purpose

M5.4 determines the next safe engineering decision for an active mission.

M5.1 governs mission state, authority, approval, events, and recovery.

M5.2 executes one approved engineering step through a controlled tool gateway.

M5.3 coordinates complete mission progress across bounded execution cycles.

M5.4 evaluates mission context, candidate actions, risk, confidence, policy, evidence, and expected utility to select one justified next action or an explicit stop decision.

## Architectural Boundary

M5.4 may:

- inspect mission, plan, orchestration, execution, validation, and repository evidence;
- generate bounded candidate actions;
- reject infeasible, unauthorized, unsafe, duplicate, or out-of-scope candidates;
- score remaining candidates using explicit factors;
- compare alternatives deterministically;
- select one next action;
- produce a structured decision rationale;
- request approval when required;
- choose retry, rollback, replan, pause, escalate, complete, or cancel;
- emit decision evidence for M5.3;
- support deterministic simulation.

M5.4 may not:

- invoke tools directly;
- mutate repository content;
- bypass M5.1 authority or approval controls;
- override M5.2 tool safety;
- execute unbounded reasoning loops;
- invent unsupported repository facts;
- select actions outside the active mission scope;
- silently modify an approved plan;
- conceal uncertainty or missing evidence.

## Core Components

1. Decision Request
2. Decision Context
3. Candidate Action
4. Candidate Generator
5. Feasibility Filter
6. Policy Filter
7. Risk Assessor
8. Confidence Assessor
9. Evidence Evaluator
10. Utility Scorer
11. Candidate Ranker
12. Decision Selector
13. Decision Rationale
14. Decision Journal
15. Decision Service
16. Reporting and CLI

## Decision Flow

```text
DECISION REQUEST
  -> LOAD DECISION CONTEXT
  -> VERIFY MISSION AND SESSION STATE
  -> GENERATE BOUNDED CANDIDATES
  -> REMOVE DUPLICATES
  -> FILTER INFEASIBLE CANDIDATES
  -> FILTER UNAUTHORIZED CANDIDATES
  -> ASSESS RISK
  -> ASSESS CONFIDENCE
  -> ASSESS EVIDENCE QUALITY
  -> SCORE EXPECTED UTILITY
  -> RANK DETERMINISTICALLY
  -> SELECT ONE ACTION OR STOP
  -> RECORD RATIONALE AND EVIDENCE
  -> RETURN DECISION TO M5.3
```

## Safety Principles

- No tool execution inside M5.4.
- Candidate generation is bounded.
- Every rejection has a reason.
- Every score is explainable.
- Every selected action has supporting evidence.
- Missing evidence lowers confidence.
- Policy violations are hard rejections.
- Ties are resolved deterministically.
- Approval requirements propagate unchanged.
- High-risk low-confidence actions stop or escalate.
- No decision is treated as fact without evidence provenance.
- Decision records are immutable.