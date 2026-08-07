# M5.8 Forge Mission Runtime Architecture

## Purpose

M5.8 integrates the existing Forge platform into one controlled end-to-end software engineering mission runtime.

It does not create another planning engine, execution engine, memory system, or multi-agent platform.

Its purpose is to connect:

- repository understanding;
- project and technology detection;
- capability selection;
- engineering memory;
- autonomous planning;
- human approval;
- controlled execution;
- build and verification;
- recovery and retry;
- documentation and review generation;
- final human approval.

## Product Boundary

Forge remains a general-purpose software engineering platform.

ERP is the first production proving ground, but M5.8 must support any repository for which Forge has suitable technology and domain capabilities, including:

- ERP;
- CRM;
- websites and web services;
- Flutter applications;
- GCS software;
- PX4 and ROS2 projects;
- embedded and firmware projects.

## Architectural Position

M5.8 sits above existing Forge capabilities.

Inputs:

- workspace and repository context;
- natural-language mission;
- project index and knowledge graph;
- capability registry;
- domain intelligence;
- M5.5 memory context;
- M5.6 approved planning output;
- M5.7 execution output;
- human approval decisions.

Outputs:

- mission session;
- mission state transitions;
- approved engineering plan;
- controlled execution run;
- validation evidence;
- recovery decisions;
- documentation updates;
- review package;
- final mission report.

## Components

1. Mission contracts
2. Mission state machine
3. Mission/session repository
4. Project and capability context adapter
5. Memory context adapter
6. Planning adapter
7. Approval gateway
8. Execution adapter
9. Verification adapter
10. Recovery controller
11. Mission loop
12. Reporting and CLI integration

## Execution Flow

1. Accept mission.
2. Resolve workspace and repository.
3. Understand repository.
4. Detect technologies and domain.
5. Load required capabilities.
6. Retrieve relevant memory and knowledge.
7. Generate engineering plan.
8. Validate risk and dependencies.
9. Pause for human approval when required.
10. Execute approved work through M5.7.
11. Run build and verification.
12. Diagnose and recover within authority.
13. Update documentation.
14. Generate evidence and review package.
15. Pause for final human approval.
16. Complete mission.

## Safety Boundary

M5.8 may orchestrate only existing governed subsystems.

It may not:

- bypass approval requirements;
- bypass the controlled tool gateway;
- perform unrestricted Git operations;
- perform destructive actions without explicit authority;
- invent capabilities that are not registered;
- modify repositories outside the active workspace;
- continue after a blocking validation failure.

## Determinism

For identical mission input and repository state, M5.8 shall produce deterministic:

- identifiers;
- context selection;
- state transitions;
- plan references;
- execution references;
- approval requirements;
- completion reports.

## Deferred to Forge v2

The following are explicitly out of scope:

- multi-agent coordination;
- autonomous agent marketplace;
- cloud mission synchronization;
- self-modifying Forge;
- unrestricted long-running autonomy;
- business process automation unrelated to software engineering;
- team collaboration platform;
- general AI research features.