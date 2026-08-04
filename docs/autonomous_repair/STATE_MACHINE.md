# M3.5 State Machine

`CREATED → VALIDATED → PROPOSED → DRY_RUN_COMPLETE → AWAITING_APPROVAL → APPLYING → REVALIDATING`

From `REVALIDATING`:

- pass → `SUCCEEDED`
- fail → `ROLLING_BACK`
- restored and attempts remain → `RETRY_READY`
- no attempts remain → `FAILED`

Invalid transitions must be rejected.