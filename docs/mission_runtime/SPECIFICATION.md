# M5.8 Mission Runtime Specification

The Forge Mission Runtime shall:

1. accept a natural-language engineering mission;
2. bind the mission to one active workspace and repository;
3. use existing repository understanding and capability discovery;
4. retrieve relevant M5.5 memory;
5. invoke M5.6 planning without reimplementing planning;
6. enforce human approval before high-risk execution;
7. invoke M5.7 execution without bypassing its authority model;
8. run project-specific verification;
9. support bounded recovery and retry;
10. stop safely on blocking failure;
11. generate evidence, documentation, and a review package;
12. request final approval before merge-worthy completion;
13. support multiple project types through registered capabilities;
14. expose deterministic CLI and reports;
15. pass architecture, Ruff, MyPy, focused, integration, and full-suite validation.