# Safe Change Planning Risk Model

## Risk levels

- Low
- Medium
- High
- Critical

## Risk factors

- Number of affected files
- Number of affected modules
- Transitive dependency depth
- Public API impact
- Database schema impact
- Data migration impact
- Authentication impact
- Authorization impact
- Financial logic impact
- Infrastructure impact
- Deployment impact
- External integration impact
- Configuration impact
- Test coverage gap
- Missing rollback path
- Missing lineage
- Unknown dependency
- Concurrency impact
- Security impact
- Regulatory or compliance impact

## Scoring principles

Risk scoring is deterministic and evidence-based.

Low risk is allowed only when:

- the change is local,
- dependencies are known,
- no public contract changes,
- no persistent data changes,
- no security or financial impact,
- verification is available,
- rollback is straightforward.

Critical risk applies when the change may cause:

- irreversible data loss,
- privilege escalation,
- major production outage,
- uncontrolled deployment,
- financial corruption,
- regulatory breach,
- unsafe autonomous execution.

## Approval policy

- Low: approval may be optional according to configuration.
- Medium: explicit engineering review required.
- High: explicit approval required.
- Critical: approval required and execution must remain blocked unless all mandatory controls exist.

## Risk reduction

Risk may be reduced by:

- narrowing scope,
- adding tests,
- adding feature flags,
- adding staged rollout,
- adding backups,
- adding rollback automation,
- isolating migrations,
- separating contracts from implementation,
- adding manual approval gates.

## Conservative rule

Unknown information never reduces risk.
