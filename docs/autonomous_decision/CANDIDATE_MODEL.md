# M5.4 Candidate Generation and Filtering Model

## Candidate Sources

- approved mission plan
- current orchestration state
- previous execution outcome
- validation findings
- recovery policy
- unresolved blockers
- repository evidence
- architecture constraints
- approval requirements
- budget state

## Candidate Categories

- execute_next_step
- retry_current_step
- rollback_current_step
- replan_remaining_work
- request_approval
- pause_mission
- escalate_mission
- complete_mission
- cancel_mission

## Candidate Generation Rules

- Candidate generation is deterministic.
- Candidate generation is bounded.
- Candidates must reference supporting evidence.
- Duplicate semantic actions are collapsed.
- Completed steps are not generated again.
- Unsupported action kinds are rejected.
- Candidate scope must remain within the mission.
- Candidate authority must not exceed configured policy.
- Candidate approval requirements are preserved.

## Rejection Reasons

- duplicate
- infeasible
- missing_dependency
- insufficient_authority
- approval_required
- scope_violation
- risk_threshold_exceeded
- confidence_below_threshold
- evidence_insufficient
- completed_step_replay
- budget_exhausted
- policy_violation