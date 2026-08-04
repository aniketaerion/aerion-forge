# M3.5 Autonomous Repair Architecture

## Objective

Take an approved M3.4 repair candidate, generate a bounded proposal, dry-run it through M3.3 Safe Code Editing, require explicit approval, apply atomically, revalidate through M3.4 and roll back on failure.

## Components

1. Immutable contracts and identifiers.
2. Repair-provider registry.
3. Exact-patch provider.
4. Isolated Ruff-fix provider.
5. Execution state machine.
6. Repair executor.
7. Service and reporting.
8. CLI and release validators.

## Safety boundary

M3.5 v1 forbids unrestricted LLM code generation, arbitrary shell execution, Git mutation, dependency installation, silent approval and unbounded retry loops.