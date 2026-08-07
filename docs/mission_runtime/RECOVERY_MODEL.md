# M5.8 Recovery Model

M5.8 coordinates existing recovery capabilities.

Permitted actions:

- retry within bounded policy;
- return to planning;
- request revised approval;
- restore checkpoint;
- rollback through existing rollback capability;
- pause for human intervention;
- abort safely.

Recovery must never expand mission scope without approval.

Repeated failure beyond configured limits must terminate or pause the mission.