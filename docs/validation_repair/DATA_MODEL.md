# M3.4 Data Model

Core immutable contracts:

- `ValidationCommand`
- `ValidationFinding`
- `ValidationRun`
- `RepairCandidate`
- `RepairAttempt`
- `RepairSession`
- `RepairReport`

A repair session is bounded by `max_attempts`. Every attempt records its candidate, state, validation runs and errors.