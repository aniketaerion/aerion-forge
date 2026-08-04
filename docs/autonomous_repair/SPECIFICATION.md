# M3.5 Autonomous Repair Specification

Supported providers:

- `exact_patch`
- `ruff_fix`

Every proposal must identify exact target paths, source fingerprints, bounded operations, risk notes and required validation commands.

Dry-run is mandatory before mutation. Apply mode requires explicit approval. Repository state must be reverified before each attempt. Failed validation triggers rollback when policy requires it.