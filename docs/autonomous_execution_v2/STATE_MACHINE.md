# M5.7 State Machine

Execution run states:

- created
- validating
- ready
- running
- paused
- recovering
- awaiting_approval
- succeeded
- failed
- cancelled

Step states:

- pending
- eligible
- running
- succeeded
- failed
- skipped
- blocked
- cancelled

Invalid transitions must raise explicit execution state errors.