# M5.9 Edit Model

## Principle
Provider output is a proposed edit, never direct write authority.

## EditOperation Types
CREATE_FILE, INSERT, REPLACE, DELETE, and RENAME are the initial contract categories. Unsupported operations fail explicitly.

## EditOperation Fields
Operation ID, operation type, target path, optional target symbol, optional source fingerprint, proposed content or structured patch information, rationale, originating requirement, evidence references, and ordering metadata.

## Safety Requirements
Every operation must be checked for repository containment, forbidden-path policy, approved plan scope, current fingerprint where applicable, operation eligibility, content and size limits, self-modification policy, and conflicts with other operations.

## GeneratedChangeSet
A GeneratedChangeSet contains ordered EditOperation objects and is validated as one bounded unit before mutation begins.

## Execution
Approved operations flow through Forge-controlled editing and transaction services. Provider adapters expose no direct filesystem mutation authority.