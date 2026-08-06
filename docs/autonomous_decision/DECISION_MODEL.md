# M5.4 Decision Model

## Decision Dispositions

- select_action
- retry
- rollback
- replan
- pause
- escalate
- complete
- cancel
- no_safe_action

## Evaluation Dimensions

### Feasibility

Can the action be performed with the available repository state, dependencies, tools, and prerequisites?

### Policy Compliance

Does the action comply with authority, approval, scope, architecture, security, and runtime policy?

### Risk

What is the probability and impact of failure, data loss, scope drift, security exposure, or irreversible mutation?

### Confidence

How strongly does available evidence support the candidate and its expected outcome?

### Evidence Quality

Are the supporting sources current, relevant, complete, and traceable?

### Utility

What expected progress does the action provide relative to cost, risk, delay, and reversibility?

### Reversibility

Can the action be safely undone using a verified checkpoint or rollback procedure?

## Deterministic Scoring

Each accepted candidate receives normalized scores from 0.0 to 1.0.

```text
total_score =
    utility_weight * utility_score
  + confidence_weight * confidence_score
  + evidence_weight * evidence_score
  + reversibility_weight * reversibility_score
  - risk_weight * risk_score
```

Hard policy rejection occurs before scoring.

Ties are resolved using:

1. lower risk;
2. higher confidence;
3. higher evidence quality;
4. greater reversibility;
5. stable candidate identifier.