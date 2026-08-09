# M5.9 General Engineering Agent Specification

The General Engineering Agent shall:

1. accept a natural-language engineering objective and repository root;
2. normalize the objective into a validated EngineeringRequest;
3. preserve constraints, acceptance criteria, allowed paths, and forbidden paths;
4. inspect repository evidence before selecting change targets;
5. identify relevant files and symbols using repository-grounded evidence;
6. construct an EngineeringContext with traceable provenance;
7. produce a structured ChangeSpecification and ChangePlan;
8. prevent planning from silently expanding beyond request or policy scope;
9. expose plans for PLAN approval when required;
10. request structured edit proposals through a provider-independent protocol;
11. treat provider output as untrusted proposal data;
12. validate every edit operation before execution;
13. require source fingerprints for destructive or replacement operations where applicable;
14. reject edits outside approved repository scope;
15. reject edits targeting forbidden paths;
16. execute approved mutations only through governed Forge editing services;
17. support bounded coordinated multi-file changes;
18. preserve rollback or safe failure semantics for partial execution;
19. run repository-specific validation after editing;
20. record validation evidence and affected scope;
21. generate bounded repair proposals from validation evidence;
22. enforce configured repair-attempt limits;
23. require REPAIR approval where policy requires it;
24. prevent unbounded correction loops;
25. require RELEASE approval where policy requires it;
26. record end-to-end EngineeringEvidence;
27. support deterministic fake-provider testing;
28. avoid provider-specific dependencies in core contracts;
29. avoid acceptance-task-specific logic in Forge implementation;
30. pass architecture, Ruff, MyPy, focused, integration, real-project, and full-suite validation.

## Functional Input

A request may contain objective, repository root, constraints, acceptance criteria, explicit target paths, forbidden paths, code-change authority, repair limit, and provider selection through configuration.

## Functional Output

A successful mission produces EngineeringRequest, RepositoryEvidence, EngineeringContext, ChangeSpecification, approved ChangePlan, GeneratedChangeSet, edit transaction evidence, ValidationOutcome, zero or more RepairProposal records, approval evidence, final EngineeringEvidence, and terminal mission status.

## Fail-Closed Requirements

The agent must fail or pause when repository root is invalid, required evidence is unavailable, target relevance cannot be established, proposed edits exceed scope, fingerprints conflict, provider output is malformed or unsafe, required approval is missing, validation remains unsuccessful beyond the repair-attempt limit, or a required execution capability is unavailable.