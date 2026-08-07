# M5.8 Approval Model

M5.8 has two primary approval gates.

## Plan Approval

Required before execution when:

- the plan is high risk;
- the plan includes destructive changes;
- the plan includes migrations;
- the plan affects authentication, finance, infrastructure, credentials, release, or production systems;
- policy explicitly requires approval.

## Final Approval

Required before:

- merge-worthy completion;
- local commit where policy requires approval;
- release or deployment;
- destructive cleanup;
- externally visible publication.

Approval decisions must include:

- approver;
- decision;
- rationale;
- scope;
- timestamp;
- related mission and plan references.