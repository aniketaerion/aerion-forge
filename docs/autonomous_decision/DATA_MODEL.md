# M5.4 Autonomous Decision Engine Data Model

## Core Models

### DecisionRequest

- request_id
- mission_id
- session_id
- plan_id
- plan_version
- repository_root
- decision_kind
- maximum_candidates
- dry_run
- requested_by
- created_at

### DecisionContext

- context_id
- mission_id
- session_id
- mission_state
- orchestration_state
- current_step_id
- completed_step_ids
- failed_step_ids
- retry_count
- rollback_count
- replan_count
- authority_level
- approval_state
- repository_fingerprint
- evidence_references
- unresolved_findings
- policy_version
- created_at

### CandidateAction

- candidate_id
- action_kind
- target_step_id
- description
- required_authority
- approval_required
- risk_class
- expected_effects
- expected_cost
- reversible
- dependencies
- evidence_references
- source
- created_at

### CandidateAssessment

- assessment_id
- candidate_id
- feasible
- policy_allowed
- risk_score
- confidence_score
- evidence_score
- utility_score
- reversibility_score
- total_score
- rejection_reasons
- warnings
- created_at

### DecisionRecord

- decision_id
- request_id
- context_id
- selected_candidate_id
- decision_kind
- disposition
- rationale
- alternative_candidate_ids
- rejected_candidate_ids
- assessment_ids
- evidence_references
- approval_required
- confidence
- context_fingerprint
- created_at

### DecisionStop

- stop_id
- request_id
- stop_kind
- reason
- resumable
- approval_required
- evidence_references
- created_at

## Invariants

- Candidate count never exceeds the request or policy limit.
- Candidate identifiers are unique.
- Rejected candidates cannot be selected.
- Selected candidate must have an assessment.
- Selected candidate must be feasible and policy-allowed.
- Selected candidate must satisfy the configured risk threshold.
- Selected candidate must satisfy the configured confidence threshold.
- Decision context fingerprint must match the evaluated context.
- Identical context fingerprints cannot produce conflicting committed decisions.
- Stop decisions cannot contain a selected candidate.
- Decision records are immutable.