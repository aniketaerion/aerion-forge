# M5.9 Validation and Repair Model

## Validation
Validation is repository-specific and uses approved project tooling or registered Forge capabilities. Evidence includes command or capability, working directory, exit status, structured failures where available, output summary, scope, and timestamp.

## ValidationOutcome States
passed, failed, blocked, and skipped_by_approved_exception.

A code-changing mission cannot complete without required validation passing or an explicitly approved exception supported by policy.

## RepairProposal
A failed ValidationOutcome may produce a RepairProposal containing repair ID, failure evidence, diagnosis, bounded affected requirements, proposed corrective plan or edits, target paths, risk, and attempt number.

## Repair Limits
Repair is bounded. Default maximum repair attempts: 3. Request or policy may impose a stricter limit but may not exceed platform authority limits.

## Repair Authority
Repair may not silently expand mission scope. Material expansion requires replanning and renewed approval. REPAIR approval is required where policy requires it.

## Terminal Failure
When validation remains unsuccessful after permitted attempts, Forge stops or pauses and preserves evidence.