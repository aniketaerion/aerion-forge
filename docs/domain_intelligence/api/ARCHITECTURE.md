# M4.4 API Domain Intelligence Architecture

M4.4 provides read-only API discovery and contract analysis through typed
contracts, REST and OpenAPI inspection, GraphQL analysis, dependency mapping,
versioning checks, authentication and security findings, reporting, and CLI
integration.

Package 0 establishes the immutable contracts and safety boundary. It does not
make network calls, invoke endpoints, fetch remote schemas, inspect secrets, or
modify source files.