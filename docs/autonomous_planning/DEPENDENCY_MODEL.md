# M5.6 Dependency Model

Planning dependencies are explicit and directional.

Supported kinds:

- requires
- blocks
- orders_after
- optional

The dependency subsystem shall:

1. preserve step traceability;
2. reject self-dependencies;
3. reject references to unknown steps;
4. detect dependency cycles;
5. produce deterministic ordering;
6. expose eligibility based on prerequisite completion;
7. prevent execution consumers from treating blocked steps as ready.

M5.7 must preserve these dependency relationships when projecting a plan into an execution run.