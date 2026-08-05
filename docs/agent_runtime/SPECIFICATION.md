# M3.8 Unified Agent Runtime Specification

The runtime shall:

- accept one explicit engineering objective;
- create one deterministic agent request and session;
- orchestrate existing Forge capabilities through adapters;
- enforce stage dependencies and bounded execution;
- require human approval for plan, edit, repair, and release operations;
- persist recoverable checkpoints;
- emit structured telemetry;
- stop safely after required-stage failure;
- deny network access and self-modification by default;
- produce a final release recommendation backed by build-verification evidence.