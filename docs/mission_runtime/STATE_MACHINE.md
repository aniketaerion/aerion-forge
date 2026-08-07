# M5.8 Mission State Machine

Mission states:

- created
- resolving_workspace
- understanding_repository
- selecting_capabilities
- retrieving_context
- planning
- validating_plan
- awaiting_plan_approval
- approved
- executing
- verifying
- recovering
- documenting
- generating_review
- awaiting_final_approval
- completed
- failed
- cancelled
- paused

Terminal states:

- completed
- failed
- cancelled

Invalid transitions must raise explicit mission state errors.

The runtime must support safe pause and resume from approved checkpoints.