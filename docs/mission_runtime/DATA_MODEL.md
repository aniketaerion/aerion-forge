# M5.8 Mission Runtime Data Model

## MissionRequest

Represents the user instruction and repository scope.

Fields include:

- mission request ID;
- workspace ID;
- repository root;
- mission statement;
- requested by;
- risk tolerance;
- approval policy;
- created timestamp.

## MissionSession

Represents one end-to-end engineering mission.

Fields include:

- session ID;
- request ID;
- state;
- repository fingerprint;
- detected technologies;
- selected capabilities;
- memory query references;
- planning request and plan references;
- approval references;
- execution run references;
- verification references;
- review package reference;
- failure reason;
- timestamps.

## MissionCheckpoint

Records resumable mission progress.

## MissionApproval

Records planning or final approval decisions.

## MissionEvidence

Aggregates evidence from understanding, planning, execution, verification, documentation, and review.

## MissionResult

Represents terminal mission outcome.