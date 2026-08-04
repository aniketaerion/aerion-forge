# M3.5 Provider Contract

A provider must:

1. Declare supported findings.
2. Produce bounded proposals only.
3. Never write directly to the real repository.
4. Never invoke a shell.
5. Declare affected paths.
6. Include expected source fingerprints.
7. Produce deterministic patches.
8. Fail closed when safety cannot be proven.