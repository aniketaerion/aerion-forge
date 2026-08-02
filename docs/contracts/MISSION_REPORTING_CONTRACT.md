# Mission Reporting Contract

Milestone: 2.5
Schema version: 1.0

## Purpose

This contract defines the deterministic boundary of the Aerion Forge
Mission Reporting capability.

## Required inputs

1. A valid persisted Mission Plan.
2. A valid persisted Task Set associated with the Mission.
3. A valid Task Generation matching the Task Set fingerprint.
4. A valid persisted Impact Assessment associated with the Mission.
5. A valid Impact Decision Generation matching the assessment.
6. A valid Engineering Memory store with an active generation.
7. An enabled Mission Reporting configuration.

## Lineage requirements

- Mission IDs must match across all source artifacts.
- Mission fingerprints must match between Mission and Task artifacts.
- Task Set fingerprints must match the Impact Assessment.
- Assessment task IDs must match the persisted Task Set in strict mode.
- Engineering Memory must contain the required Mission and assessment lineage.

## Deterministic outputs

- `MISSION_REPORT.json`
- `MISSION_SUMMARY.json`
- `MISSION_TRACEABILITY.json`
- `MISSION_RISKS.json`
- `MISSION_REPORT.md`

All JSON outputs use deterministic ordering and UTF-8 encoding.

## Report status

The report status is derived from the persisted Impact Decision status.
Mission Reporting does not independently grant engineering approval.

## Persistence

Report files are written using atomic file replacement.
If report writing fails, existing report files are restored.

## Immutability

Mission Reporting must not mutate Mission Plans, Task Sets, Impact
Assessments, Engineering Memory records, or their generation metadata.

## Safety boundary

Mission Reporting may read Forge-owned persisted artifacts and write
Forge-owned reporting outputs.

It must not execute engineering tasks, modify target repositories, edit
source code, run builds or tests, mutate Git, deploy software, grant
approvals, or perform autonomous remediation.

## Failure behaviour

- Missing persisted artifacts must produce a controlled failure.
- Invalid lineage must produce a validation failure.
- Disabled configuration must prevent report generation.
- Corrupt or unreadable persisted reports must produce a report error.
- Partial report suites must not be accepted as complete.
