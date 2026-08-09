# M5.9 General Engineering Agent Data Model

## EngineeringRequest
Canonical user engineering request with request ID, objective, repository root, constraints, acceptance criteria, explicit target paths, forbidden paths, code-change authority, repair limit, and timestamp.

## RepositoryEvidence
Traceable repository fact with evidence ID, path, symbol, evidence type, relevance, fingerprint, rationale, and provenance.

## RelevantFile
Repository file selected for possible change with relevance rationale and evidence references.

## RelevantSymbol
Class, function, method, schema, route, component, configuration key, or other repository symbol relevant to the request.

## EngineeringContext
Normalized request plus selected repository evidence supplied to planning or synthesis.

## ChangeRequirement
One verifiable requirement derived from the EngineeringRequest.

## ChangeSpecification
Normalized requirements, constraints, invariants, and acceptance conditions.

## ChangePlan
Structured implementation plan containing ordered FileChangePlan entries, validation intent, expected effect, risk, and evidence references.

## FileChangePlan
One file-level planned change with path, symbols, rationale, dependencies, operations, risk, and evidence.

## EditOperation
One proposed mutation with operation ID, type, target path, optional symbol, source fingerprint, proposed content or patch data, rationale, requirement reference, and evidence references.

## GeneratedChangeSet
Ordered bounded collection of EditOperation proposals plus plan and evidence references.

## ValidationPlan
Approved commands or registered validation capabilities.

## ValidationOutcome
Validation status, commands, failures, scope, and evidence.

## RepairProposal
Bounded response to failed validation referencing failure evidence and necessary corrective changes.

## EngineeringEvidence
Traceability object linking request, repository evidence, plan, approvals, edits, validation, repairs, and final result.