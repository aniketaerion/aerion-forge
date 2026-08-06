# M5.7 Specification

The autonomous execution engine shall:

1. accept only validated, executable planning plans;
2. create immutable execution runs;
3. preserve plan and step traceability;
4. evaluate dependencies before scheduling;
5. enforce authority and policy checks;
6. record every attempt and state transition;
7. capture evidence for each completed step;
8. support bounded retries and governed recovery;
9. stop safely on blocking failure;
10. produce deterministic reports;
11. expose a non-conflicting CLI namespace;
12. pass Ruff, MyPy, focused tests, and the full repository suite.