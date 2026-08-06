# M5.7 Recovery Model

Recovery actions:

- retry with bounded count;
- pause for approval;
- skip only when policy permits;
- rollback using an existing checkpoint;
- replan through M5.6;
- abort safely.

Recovery decisions must be deterministic, journaled, evidence-backed, and policy constrained.