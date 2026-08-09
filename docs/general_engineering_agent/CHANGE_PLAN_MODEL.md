# M5.9 Change Plan Model

A ChangePlan is the authoritative structured implementation proposal presented to Forge policy and approval systems.

## Required Properties

A ChangePlan contains plan ID, engineering request ID, objective, requirements, ordered file changes, dependencies, expected effect, validation plan, aggregate risk, repository evidence references, and timestamp.

## FileChangePlan

Each FileChangePlan identifies target path, relevant symbols, path-selection rationale, supporting evidence, intended operations, dependencies, expected local effect, and risk.

## Plan Validity

A plan is invalid when a target has no supporting evidence, a target is forbidden, acceptance criteria are omitted, dependencies contain an unresolved cycle, code-changing validation is absent, or scope exceeds the approved request.

## Approval Boundary

PLAN approval authorizes the structured plan scope. It does not authorize arbitrary mutation outside that plan. Material scope changes require replanning or renewed approval.