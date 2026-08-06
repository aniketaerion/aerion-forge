# M5.5 Memory Policy Model

## Hard Policies

Reject persistence when:

- evidence is required but absent;
- prohibited data is detected;
- repository scope is missing;
- source provenance is missing;
- confidence is invalid;
- supersession would create a cycle;
- memory crosses authority boundaries;
- record attempts to overwrite immutable history.

## Default Limits

- bounded observation size
- bounded tag count
- bounded retrieval result count
- minimum fact confidence
- maximum retrieval age where applicable
- explicit inclusion of superseded records
- explicit cross-repository retrieval approval

## Default-Safe Behaviour

- retrieval is repository-scoped;
- superseded records are hidden;
- secrets are rejected;
- hypotheses remain hypotheses;
- facts require evidence;
- memory is advisory;
- current repository evidence wins.