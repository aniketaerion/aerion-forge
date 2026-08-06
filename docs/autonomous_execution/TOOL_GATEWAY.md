# M5.2 Controlled Tool Gateway

## Responsibilities

- Resolve tools from an explicit registry.
- Validate action kind.
- Validate required authority.
- Validate approval requirement.
- Validate checkpoint requirement.
- Validate arguments.
- Enforce timeout.
- Redact secrets.
- Record invocation metadata.
- Capture affected files.
- Reject out-of-scope effects.

## Prohibited Behavior

- Arbitrary command passthrough
- Dynamic import of unknown tools
- Network access by default
- Shell expansion without explicit contract
- Unrecorded filesystem mutation
- Silent retries