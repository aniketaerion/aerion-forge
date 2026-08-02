# Engineering Memory Contract

Contract version: 1.0
Milestone: 2.4
Forge version: 0.3

## Purpose

This contract freezes the deterministic interfaces, persistence model,
reports, query behaviour, safety boundaries, and CLI surface of Engineering Memory.

## Required upstream capabilities

- `mission-planning`
- `task-management`
- `impact-decision-engine`

## Public commands

```text
forge memory build MISSION_ID
forge memory list
forge memory show MEMORY_ID
```

## Canonical store

```text
memory/engineering-memory.json
```

The store uses schema version `1.0`, canonical UTF-8 JSON, atomic replacement,
post-write verification, bounded history, corruption detection, and rollback.

## Deterministic reports

```text
reports/latest/ENGINEERING_MEMORY.json
reports/latest/ENGINEERING_MEMORY_SUMMARY.json
reports/latest/ENGINEERING_MEMORY_LINEAGE.json
reports/latest/ENGINEERING_MEMORY.md
```

Identical validated inputs must produce identical report content.

## Identity contract

Memory IDs, evidence IDs, relationship IDs, generation IDs, record fingerprints,
and store fingerprints are derived from canonical validated content.

## Query contract

Queries are read-only, exact, deterministic, and ordered by memory ID.

Supported query fields:

- memory ID;
- mission ID;
- task ID;
- assessment ID;
- capability ID;
- milestone;
- memory type;
- normalized tag.

## Transaction contract

If report generation fails after persistence, the previous store and previous
report suite must be restored. Partial report suites are prohibited.

## Safety boundary

Milestone 2.4 provides no:

- semantic or fuzzy search;
- embeddings or vector database;
- chat transcript storage;
- hidden reasoning storage;
- source modification;
- task execution;
- build or test execution;
- migration execution;
- Git mutation;
- deployment;
- approval granting;
- autonomous remediation.
