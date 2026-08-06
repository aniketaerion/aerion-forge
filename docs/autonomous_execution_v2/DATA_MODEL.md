# M5.7 Data Model

## ExecutionRequest

Links an approved planning plan to an execution run.

## ExecutionRun

Tracks run identity, plan identity, lifecycle state, risk, current step, timestamps, failure reason, and completion summary.

## ExecutionStep

Represents the executable projection of a planning step.

## ExecutionAttempt

Represents one bounded attempt to execute one step.

## ExecutionDependency

Preserves the prerequisite relation from the planning plan.

## ExecutionEvidence

Stores references proving the observed effect of an attempt.

## RecoveryDecision

Records retry, skip, rollback, pause, or abort decisions.

## ExecutionValidationResult

Records completion checks and blocking findings.