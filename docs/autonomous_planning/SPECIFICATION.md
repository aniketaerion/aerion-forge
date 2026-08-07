# M5.6 Autonomous Planning Specification

The planning engine shall:

1. accept a repository-grounded engineering objective;
2. classify the planning intent;
3. bind planning to one repository root;
4. accept explicit target paths and constraints;
5. consume only known/registered capabilities;
6. synthesize ordered planning steps;
7. synthesize explicit step dependencies;
8. reject cyclic dependency graphs;
9. assign risk to plans and individual steps;
10. require explicit approval for destructive work;
11. validate generated plans before readiness;
12. allow approval, rejection, and bounded revision;
13. persist planning sessions and plan versions through an explicit repository;
14. expose deterministic reporting and CLI behavior;
15. remain execution-free;
16. pass Ruff, MyPy, focused tests, and the full repository suite.