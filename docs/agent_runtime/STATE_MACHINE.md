# M3.8 Unified Agent Runtime State Machine

Primary lifecycle:

`created -> planning -> awaiting_approval -> executing -> validating`

Repair path:

`validating -> repairing -> validating`

Release path:

`validating -> verifying -> completed`

Control paths:

- any non-terminal state -> paused
- paused -> prior resumable state
- any non-terminal state -> cancelled
- required-stage failure -> failed