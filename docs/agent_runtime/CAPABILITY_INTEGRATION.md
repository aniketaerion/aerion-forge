# M3.8 Capability Integration

The unified runtime coordinates these existing Forge capabilities:

1. Repository discovery
2. Incremental project index
3. Engineering knowledge graph
4. Mission planning
5. Task management
6. Impact analysis
7. Safe change planning
8. Safe code editing
9. Validation and repair planning
10. Autonomous repair
11. Mission orchestration
12. Build verification and release gating

Each capability is exposed through a typed adapter and registered by capability
identifier. Adapters translate runtime stage input into the native subsystem
contract and normalize native output into `AgentStageResult`.