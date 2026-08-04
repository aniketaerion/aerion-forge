# M3.3 Data Model

## EditOperation

Describes one bounded text mutation with operation type, repository-relative path, offsets, expected text, replacement text and source fingerprint.

## FileEditPlan

Groups ordered operations for one source file and binds them to one source fingerprint.

## SafeEditRequest

Groups file plans, references an approved M3.2 change plan and distinguishes dry-run from approved apply mode.

## LoadedTextFile and FileSnapshot

Capture encoding, newline convention, content and fingerprints required for safe processing and rollback.

## Results

`FileEditResult`, `EditTransactionResult` and `SafeEditReport` provide immutable evidence including unified diffs, resulting fingerprints, rollback state and validation messages.