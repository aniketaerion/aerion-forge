# M3.4 Validation and Repair Architecture

## Objective

Turn M3.3 safe edits into a bounded engineering loop that validates changes, interprets failures, plans candidate repairs and revalidates until success or an attempt limit is reached.

## Components

1. Contracts and identifiers.
2. Validation runner.
3. Output parser.
4. Repair planner.
5. Repair service.
6. CLI and release validation.

## Flow

Safe edit → targeted validation → normalized findings → bounded repair candidate → approved repair → revalidation → success or stop.

## Safety boundary

M3.4 does not allow unrestricted shell execution, unbounded retries, silent approval, autonomous Git commits or uncontrolled repository mutation.