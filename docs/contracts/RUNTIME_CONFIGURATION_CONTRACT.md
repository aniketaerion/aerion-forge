# Runtime Configuration Contract

Schema `1.0` defines canonical dotted keys, profiles, precedence, safe resolved fields, fingerprint
and generation semantics, `memory/configuration.json`, six report names, `ConfigurationQuery`, and
the `forge config` command group.

Existing keys and enum meanings require compatible extension, deprecation, migration, or a schema
increment. Canonical environment variables override aliases and CLI overrides are command-local and
highest precedence. Fingerprints exclude timestamps, machines, raw secrets, and private paths.

Sources are read-only and invalid resolution blocks persistence. The system cannot enable target
mutation, unrestricted networks, plugin injection, arbitrary execution, or dynamic loading.
