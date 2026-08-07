# M5.6 Planning State Machine

Planning states:

- created
- analysing
- generating
- validating
- awaiting_approval
- approved
- rejected
- ready
- failed
- cancelled

Typical lifecycle:

created
→ analysing
→ generating
→ validating
→ awaiting_approval or ready
→ approved
→ ready

Alternative terminal paths:

- rejected
- failed
- cancelled

State changes must occur through explicit planning services and must preserve plan/session traceability.