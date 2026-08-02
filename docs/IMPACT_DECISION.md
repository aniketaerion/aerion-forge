# Impact Decision Engine

Milestone: 2.3
Forge version: 0.3

The Impact Decision Engine converts an existing persisted Mission Plan and
Task Set into a deterministic, validated engineering impact assessment.

## Purpose

The engine evaluates engineering impact before execution begins. It produces
structured findings, severity, decision status, recommendations, approval
requirements, validation obligations, persistence records, and reports.

## Inputs

- Persisted Mission Plan
- Persisted Task Set
- Impact Decision configuration

## Outputs

- memory/impact-decisions.json
- reports/latest/IMPACT_ASSESSMENT.json
- reports/latest/IMPACT_DECISION.json
- reports/latest/IMPACT_EVIDENCE.json
- reports/latest/IMPACT_SUMMARY.md
- CLI output

## Commands

forge impact assess MISSION_ID
forge impact list
forge impact show ASSESSMENT_ID

## Deterministic Behaviour

For identical Mission Plans and Task Sets, the engine produces identical
identifiers, fingerprints, findings, severity, status, recommendations,
statistics, persistence records, and reports.

## Safety Boundary

The engine does not execute tasks, edit source code, run builds or tests,
perform migrations, mutate Git, deploy software, grant approvals, or
perform autonomous remediation.
