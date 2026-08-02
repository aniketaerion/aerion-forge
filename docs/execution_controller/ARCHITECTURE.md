# Execution Controller Architecture

Milestone: 3.1
Forge version: 0.4

## Purpose

The Execution Controller coordinates explicitly approved engineering execution
through registered tools while preserving deterministic lineage, evidence,
state transitions, and failure records.

## Components

1. Execution Request Validator
2. Approval Gate
3. Execution Session Builder
4. State Machine
5. Tool Dispatch Boundary
6. Evidence Recorder
7. Atomic Store
8. Deterministic Renderer
9. CLI Adapter

## Inputs

- Mission Plan
- Task Set
- Impact Assessment
- Engineering Memory
- Mission Report
- Explicit approval record
- Registered tool declarations
- Execution configuration

## Outputs

- Execution request
- Execution session
- State-transition history
- Approval evidence
- Operation records
- Evidence bundle
- Deterministic reports

## Safety boundary

The controller must not independently edit files, run commands, execute tests,
mutate Git, deploy software, perform migrations, or grant approval.

Target-affecting operations may only be coordinated through registered tools
after explicit approval, lineage validation, and policy validation.
