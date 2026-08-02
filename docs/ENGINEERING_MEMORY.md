# Engineering Memory

Milestone: 2.4
Forge version: 0.3

Engineering Memory preserves verified and deterministic lineage across
Mission Planning, Task Management, and Impact Decision artifacts.

## Inputs

- Persisted Mission Plan
- Persisted Task Set
- Persisted Impact Assessment
- Engineering Memory configuration

## Outputs

- `memory/engineering-memory.json`
- `reports/latest/ENGINEERING_MEMORY.json`
- `reports/latest/ENGINEERING_MEMORY_SUMMARY.json`
- `reports/latest/ENGINEERING_MEMORY_LINEAGE.json`
- `reports/latest/ENGINEERING_MEMORY.md`

## Commands

```text
forge memory build MISSION_ID
forge memory list
forge memory show MEMORY_ID
```

## Structured filters

```text
--mission
--task
--assessment
--capability
--milestone
--type
--tag
--json
```

## Stored knowledge

Engineering Memory stores verified:

- mission lineage;
- deterministic task lineage;
- impact assessments and decisions;
- capability and milestone associations;
- evidence references;
- relationships between memory records;
- bounded historical record versions.

## Safety boundary

Engineering Memory does not store chat transcripts, private reasoning,
arbitrary prompts, embeddings, or unverified model output.

It does not execute tasks, modify source code, run builds or tests, mutate
Git, perform migrations, deploy software, grant approvals, or perform
autonomous remediation.
