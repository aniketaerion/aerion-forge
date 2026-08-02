# Execution Controller API Contract

Milestone: 3.1

## Commands

    forge execution request MISSION_ID
    forge execution validate REQUEST_ID
    forge execution approve REQUEST_ID
    forge execution reject REQUEST_ID
    forge execution start SESSION_ID
    forge execution cancel SESSION_ID
    forge execution show SESSION_ID
    forge execution list

Initial implementation may expose only non-mutating request, validate, show,
and list commands until tool dispatch is explicitly enabled.

## Inputs and outputs

### Inputs

- Mission ID
- Optional task filters
- Requested operation declarations
- Dry-run flag
- Approval decision
- Approver identity
- Approval evidence

### Outputs

- Execution request
- Validation result
- Approval record
- Execution session
- State history
- Evidence bundle
- Deterministic reports

## Persistence

- Store: `memory/execution-controller.json`
- Reports: `reports/latest/`
- Writes must be atomic.
- Failed writes must restore the previous valid state.

## Reports

- `EXECUTION_CONTROLLER.json`
- `EXECUTION_CONTROLLER_SUMMARY.json`
- `EXECUTION_CONTROLLER_EVIDENCE.json`
- `EXECUTION_CONTROLLER_TRANSITIONS.json`
- `EXECUTION_CONTROLLER.md`
