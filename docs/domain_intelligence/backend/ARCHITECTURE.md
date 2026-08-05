# M4.2 Backend Domain Intelligence Architecture

M4.2 provides read-only backend discovery and analysis through typed contracts,
framework detectors, service topology analysis, dependency inspection,
reporting, and CLI integration.

Package 0 establishes the immutable contracts and safety boundary. It does not
execute backend code, access the network, inspect secrets, or modify source.