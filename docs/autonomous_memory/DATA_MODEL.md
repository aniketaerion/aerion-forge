# M5.5 Autonomous Memory Data Model

## Core Models

### MemoryObservation

- observation_id
- source_kind
- source_reference
- repository_root
- repository_fingerprint
- mission_id
- session_id
- content
- evidence_references
- tags
- observed_at

### MemoryRecord

- memory_id
- schema_version
- memory_kind
- statement
- normalized_statement
- confidence
- repository_scope
- module_scope
- capability_scope
- business_domain
- evidence_references
- source_references
- tags
- applicability
- status
- supersedes_memory_id
- created_at

### MemoryProvenance

- provenance_id
- memory_id
- source_kind
- source_reference
- evidence_digest
- repository_fingerprint
- actor
- captured_at

### MemoryQuery

- query_id
- repository_scope
- module_scope
- capability_scope
- business_domain
- memory_kinds
- tags
- minimum_confidence
- maximum_results
- include_superseded
- requested_by
- created_at

### MemoryMatch

- memory_id
- relevance_score
- confidence_score
- recency_score
- applicability_score
- total_score
- matched_terms
- rationale

### LearningRecord

- learning_id
- source_memory_ids
- lesson
- success_count
- failure_count
- confidence
- applicability
- last_validated_at
- created_at

## Invariants

- Memory identifiers are unique.
- Stored facts require evidence.
- Confidence is between 0.0 and 1.0.
- Superseded records remain immutable.
- A record cannot supersede itself.
- Supersession chains cannot cycle.
- Prohibited content cannot be persisted.
- Retrieval result count is bounded.
- Superseded records are excluded by default.
- Repository-scoped memory cannot cross repository boundaries without explicit policy.
- Learning records must cite source memory.