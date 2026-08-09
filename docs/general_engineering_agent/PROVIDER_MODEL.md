# M5.9 Engineering Provider Model

## Purpose
EngineeringProvider separates reasoning and code-generation services from Forge authority and execution.

## Provider Responsibilities
A provider may normalize intent from supplied context, propose a ChangePlan, synthesize structured EditOperation proposals, analyze ValidationOutcome evidence, and propose a bounded RepairProposal.

## Provider Non-Authority
A provider must not write repository files, invoke arbitrary shell commands, persist approvals, change policy, mark a mission complete, bypass validation, or expand repository scope without Forge authorization.

## Protocol Shape
The provider contract exposes typed operations conceptually equivalent to understand_request(...), propose_change_plan(...), synthesize_edits(...), and propose_repair(...).

## Provider Implementations
Possible adapters include OpenAIEngineeringProvider, OllamaEngineeringProvider, deterministic FakeEngineeringProvider, and future enterprise providers.

Core general_engineering models, policies, and protocols must not import provider SDKs.

## Output Validation
All provider output is untrusted structured data until parsed and validated against Forge contracts, repository evidence, approved scope, and policy.