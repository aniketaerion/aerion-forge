# M5.5 Retention, Redaction, and Supersession Model

## Prohibited Content

- passwords
- API keys
- access tokens
- private keys
- raw environment variables
- personal data not required for engineering work
- unrestricted command output containing secrets
- unredacted customer-confidential payloads

## Retention Classes

- permanent architecture evidence
- long-lived engineering lessons
- project-lifetime repository facts
- bounded operational observations
- temporary hypotheses
- quarantined records

## Supersession

- Records are never silently overwritten.
- Corrections create new records.
- New records reference superseded records.
- Superseded records remain auditable.
- Cyclic supersession is prohibited.
- Retrieval excludes superseded records unless explicitly requested.

## Expiration

- Temporary observations may expire.
- Expiration does not destroy audit history.
- Expired records are excluded from normal retrieval.