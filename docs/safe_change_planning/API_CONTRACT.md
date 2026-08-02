# Safe Change Planning API Contract

## Commands

### forge change plan

Build and persist a deterministic Safe Change Plan.

### forge change validate

Validate the latest persisted Safe Change Plan.

### forge change show

Show the latest plan or one selected planning artifact.

### forge change list

List persisted Safe Change Planning artifacts.

## Inputs and outputs

### Inputs

- Change request
- Mission ID
- Task IDs
- Source fingerprints
- Repository state
- Index state
- Knowledge graph state
- Impact Assessment
- Engineering Memory
- Mission Report
- Configuration

### Outputs

- `memory/safe-change-plan.json`
- `reports/latest/SAFE_CHANGE_PLAN.json`
- `reports/latest/SAFE_CHANGE_SUMMARY.json`
- `reports/latest/SAFE_CHANGE_TARGETS.json`
- `reports/latest/SAFE_CHANGE_RISKS.json`
- `reports/latest/SAFE_CHANGE_VERIFICATION.json`
- `reports/latest/SAFE_CHANGE_ROLLBACK.json`
- `reports/latest/SAFE_CHANGE_TRACEABILITY.json`
- `reports/latest/SAFE_CHANGE_PLAN.md`

## Service API

The service must expose methods for:

- request creation
- input validation
- plan construction
- plan validation
- report rendering
- report persistence
- plan loading
- plan querying

## Error contract

The API must use typed errors for:

- disabled configuration
- invalid request
- missing lineage
- invalid dependency data
- impossible plan
- risk policy violation
- persistence failure
- report failure
- missing plan
- corrupted plan

## Exit codes

- 0: success
- 1: general failure
- 4: report or persistence failure
- 5: validation failure
- 6: planning failure
