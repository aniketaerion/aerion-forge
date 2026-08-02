# Mission Reporting

Milestone: 2.5
Forge version: 0.3

Mission Reporting converts verified Mission Planning, Task Management,
Impact Decision, and Engineering Memory artifacts into deterministic
engineering reports.

## Inputs

- Persisted Mission Plan
- Persisted Task Set and Task Generation
- Persisted Impact Assessment and Impact Generation
- Persisted Engineering Memory
- Mission Reporting configuration

## Outputs

- `reports/latest/MISSION_REPORT.json`
- `reports/latest/MISSION_SUMMARY.json`
- `reports/latest/MISSION_TRACEABILITY.json`
- `reports/latest/MISSION_RISKS.json`
- `reports/latest/MISSION_REPORT.md`

## Commands

```text
forge report build MISSION_ID
forge report build MISSION_ID --json
forge report build MISSION_ID --no-reports
forge report show
forge report show --json
forge report show --sections
```

## Report contents

- Executive summary
- Mission objective and deliverables
- Task status and blocked-task summary
- Impact decision and findings
- Engineering Memory lineage
- Included engineering risks
- Mission-to-task traceability
- Input validation results

## Determinism

For identical frozen inputs and configuration, Mission Reporting produces
the same report identity, fingerprint, sections, risks, traceability, and
rendered output.

## Safety boundary

Mission Reporting is a reporting and documentation capability.

It does not execute tasks, edit source code, run builds or tests, mutate
Git, perform migrations, deploy software, grant approvals, or perform
autonomous remediation.
