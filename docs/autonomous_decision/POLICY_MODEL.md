# M5.4 Decision Policy Model

## Hard Policies

The following conditions reject a candidate before scoring:

- authority is insufficient;
- approval is missing;
- action is outside scope;
- action violates architecture constraints;
- action exceeds configured risk class;
- action would replay completed work;
- required dependency is absent;
- required checkpoint is absent;
- runtime budget is exhausted;
- action is prohibited by security policy.

## Threshold Policies

- maximum candidate count
- maximum accepted risk
- minimum confidence
- minimum evidence quality
- minimum utility
- minimum reversibility for mutating actions

## Default-Safe Behaviour

- Dry-run is the default.
- No candidate is selected when all candidates fail policy.
- High-risk and low-confidence decisions escalate.
- Irreversible actions require approval.
- Ties are resolved deterministically.
- Policy versions are recorded in every decision.