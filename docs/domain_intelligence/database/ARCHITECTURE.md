# M4.3 Database Domain Intelligence Architecture

M4.3 provides read-only database discovery and structural analysis through
typed contracts, PostgreSQL schema inspection, migration analysis, constraint
and index analysis, relationship mapping, query inspection, risk reporting,
and CLI integration.

Package 0 establishes the immutable contracts and safety boundary. It does not
connect to a live database, execute SQL, inspect secrets, or modify schemas.