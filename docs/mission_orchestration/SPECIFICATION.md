# M3.6 Engineering Mission Orchestration Specification

M3.6 coordinates existing Forge subsystems rather than duplicating them.

A mission contains an immutable request, deterministic workflow, stage runs, checkpoints, approval evidence and a final report.

Execution must remain bounded by repository fingerprints, stage dependencies, maximum attempts, protected paths, approval requirements and checkpoint persistence.