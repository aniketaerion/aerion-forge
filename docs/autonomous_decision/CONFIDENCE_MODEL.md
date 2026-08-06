# M5.4 Confidence and Evidence Model

## Confidence Inputs

- direct repository evidence
- test and validation evidence
- execution outcome consistency
- architecture alignment
- dependency completeness
- source freshness
- source agreement
- unresolved uncertainty
- historical decision performance

## Confidence Rules

- Confidence ranges from 0.0 to 1.0.
- Unsupported assumptions reduce confidence.
- Conflicting evidence reduces confidence.
- Missing required evidence may force rejection.
- High-risk actions require higher confidence.
- Confidence cannot be increased by candidate popularity.
- Confidence rationale must be recorded.

## Evidence Quality

Evidence is assessed for:

- relevance
- provenance
- completeness
- recency
- consistency
- reproducibility
- integrity

## Required Behaviour

When evidence is inadequate, M5.4 must:

- request clarification;
- request additional inspection;
- pause;
- escalate;
- or return no_safe_action.

It must not invent missing facts.