# Runtime Diagnostics Contract — Schema 1.0

Canonical contracts cover definitions, evidence, actions, results, statistics, summaries,
generations, changes, snapshots, stores, result sets, configuration, and validation.

Check IDs are stable lowercase kebab-case. Definitions are immutable, explicit, sorted, and
contain no callable. Prerequisites must exist and be acyclic. Sensitive evidence is exactly
`********`; child IDs are unique; actions are manual and non-destructive.

Deterministic artifacts exclude timestamps, exact duration, users, hosts, process IDs, private
paths, environment dumps, source, secrets, and temporary names. Overall status, statistics,
generation counts, and fingerprints match results. Generation IDs use `diagnostics-` plus the
first 20 fingerprint characters.

Validation precedes atomic persistence/report replacement. Corrupt JSON and unsupported schemas
are distinct failures. History is bounded and keys isolated. Write probes are confined to
Forge-controlled directories and always cleaned. Checks perform no network, subprocess, plugin,
target-source, or remedial work. The bootstrap uses static `runtime-configuration` and
`capability-registry`; diagnostics does not depend on its own result.
