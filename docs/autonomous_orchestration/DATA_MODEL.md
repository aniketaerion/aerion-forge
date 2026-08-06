# M5.3 Autonomous Mission Orchestration Data Model

## Core Models

### OrchestrationRequest

- request_id
- mission_id
- repository_root
- dry_run
- maximum_cycles
- requested_by
- created_at

### MissionSession

- session_id
- mission_id
- plan_id
- plan_version
- repository_root
- state
- current_step_id
- completed_step_ids
- failed_step_ids
- cycle_count
- execution_count
- retry_count
- rollback_count
- replan_count
- checkpoint_id
- stop_reason
- version
- created_at
- updated_at

### OrchestrationIteration

- iteration_id
- session_id
- sequence
- mission_version_before
- mission_version_after
- selected_step_id
- execution_request_id
- execution_id
- outcome
- recovery_action
- evidence_ids
- event_ids
- started_at
- completed_at

### SessionCheckpoint

- checkpoint_id
- session_id
- mission_id
- session_version
- mission_snapshot_version
- plan_version
- repository_fingerprint
- current_step_id
- completed_step_ids
- verified
- created_at

### OrchestrationStop

- stop_id
- session_id
- stop_kind
- reason
- approval_required
- resumable
- created_at

## Invariants

- One active session per mission.
- Session plan version must match the approved mission plan.
- Cycle count never exceeds the request or runtime budget.
- Completed steps cannot execute again.
- One iteration creates at most one execution request.
- Session updates require matching optimistic version.
- Resume requires a verified checkpoint.
- Terminal missions and sessions cannot resume.