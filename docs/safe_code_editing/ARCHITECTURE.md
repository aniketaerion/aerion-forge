# M3.3 Safe Code Editing Architecture

## Objective

Convert an approved M3.2 change plan into deterministic, reviewable and reversible text edits.

## Components

1. **Identifiers** generate stable SHA-256-based IDs and fingerprints.
2. **Models** define immutable requests, plans, operations, snapshots and results.
3. **Policies** enforce repository containment, protected paths, size limits and approval.
4. **Loader** will safely load text while preserving encoding and newline conventions.
5. **Operations** will apply bounded insert, replace and delete edits in memory.
6. **Transaction** will snapshot files, write atomically and roll back on failure.
7. **Service** will orchestrate dry-run and apply execution.
8. **CLI** will expose explicit dry-run and approved apply commands.

## Flow

Approved change plan → policy validation → safe load → fingerprint check → in-memory edits → diff → dry-run or atomic transaction → report.

## Boundaries

M3.3 v1 does not perform semantic refactoring, repository-wide renames, Git commits, shell execution or autonomous merges.