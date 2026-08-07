# M5.6 Approval and Risk Model

## Planning Risk

Supported levels:

- low
- medium
- high
- critical

Risk may be assigned at both plan and step level.

## Approval Requirements

Supported approval requirements:

- none
- plan
- code
- release

Destructive steps cannot use `none`.

A plan may also carry an aggregate `requires_approval` flag.

M5.6 records approval requirements but does not grant authority to execute. Execution authority is enforced downstream by M5.7 and the mission runtime.