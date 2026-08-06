# M5.3 Resume and Restart Model

## Resume Preconditions

- Session is resumable.
- Session checkpoint exists.
- Checkpoint is verified.
- Mission identifier matches.
- Mission snapshot version is compatible.
- Approved plan version matches.
- Repository fingerprint is acceptable.
- No conflicting active session exists.
- No active execution lease exists.
- Mission is not terminal.

## Resume Behaviour

- Restore session state.
- Revalidate budgets.
- Revalidate approval and authority.
- Re-evaluate the current step.
- Never replay a completed iteration.
- Never repeat a completed step.
- Emit a resume event.