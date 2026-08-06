# M5.5 Retrieval and Ranking Model

## Retrieval Filters

- repository scope
- module scope
- capability scope
- business domain
- memory kind
- tags
- confidence threshold
- status
- age
- authority scope

## Ranking Dimensions

- semantic relevance
- repository applicability
- capability applicability
- confidence
- evidence quality
- recency
- historical success
- historical failure

## Deterministic Score

```text
total_score =
    relevance_weight * relevance_score
  + applicability_weight * applicability_score
  + confidence_weight * confidence_score
  + evidence_weight * evidence_score
  + recency_weight * recency_score
  + outcome_weight * outcome_score
```

## Tie Breaking

1. higher applicability;
2. higher confidence;
3. stronger evidence;
4. newer active record;
5. stable memory identifier.

## Required Behaviour

- Current repository evidence outranks memory.
- Superseded memory is excluded by default.
- Negative evidence is returned when relevant.
- Every match includes ranking rationale.
- Retrieval limits are enforced.