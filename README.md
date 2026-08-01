# Aerion Forge

Aerion Forge Version 0.2 Milestone 1.5 is a local, multi-workspace engineering platform. Its
deterministic Capability Registry truthfully declares completed and planned functionality. Run
`forge capabilities` or `forge capability capability-registry`; see `docs/CAPABILITIES.md`.
The schema contract and hardening evidence are in `docs/contracts/` and `docs/audits/`.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Repository Discovery

```powershell
forge inspect                         # active workspace, then current directory
forge inspect ERP                     # registered workspace name or ID
forge inspect "D:\Software Dev\ERP" # direct repository path
forge inspect ERP --json              # complete structured result
forge inspect ERP --summary           # concise console summary
forge inspect ERP --verbose           # expanded console details
```

Discovery is read-only and manifest-first. Forge traverses file and directory names for statistics, but reads only recognized manifests and configuration files. It does not parse application source or perform semantic analysis.

Each inspection writes deterministic artifacts to `reports/latest/`:

```text
PROJECT.json                 TECH_STACK.json
APPLICATIONS.json            DEPENDENCIES.json
BUILD_SYSTEM.json            TEST_FRAMEWORKS.json
CONFIGURATION.json           DIRECTORY_STRUCTURE.json
PROJECT_SUMMARY.md           TECHNOLOGY_SUMMARY.md
APPLICATION_SUMMARY.md
```

The latest result per workspace or repository is atomically persisted in `memory/discovery.json` for later incremental-refresh support.

## Workspace CLI

```powershell
forge workspace add ERP "D:\Software Dev\ERP" --type ERP
forge workspace list
forge workspace search platform
forge workspace show ERP
forge workspace update ERP --description "Enterprise platform" --tag backend
forge workspace rename ERP Enterprise
forge workspace use Enterprise
forge workspace current
forge workspace validate Enterprise
forge workspace doctor Enterprise
forge workspace remove Enterprise
```

Workspace names and repository paths are unique. Removing a workspace never deletes repository files.

## Audit CLI

```powershell
forge audit D:\path\to\repository
forge show-memory
forge version
```

`python run.py` supports the same commands. `aerion-agent` remains a compatibility alias.

## Project Tree

```text
forge/
  discovery/
    errors.py             Recoverable discovery errors
    models.py             Structured discovery metadata
    renderer.py           Deterministic JSON and Markdown artifacts
    scanner.py            Manifest-first repository inspection
    service.py            Persistence and atomic report writing
  workspace/              Workspace Manager and CLI
  agents/                 Version 0.1 repository audit
  config/ core/ memory/ models/ planner/ reports/ tools/ utils/
  runtime/ plugins/ prompts/
docs/ARCHITECTURE.md
memory/discovery.json      Persisted discovery results
memory/workspaces.json     Workspace registry
reports/latest/            Current discovery and audit output
tests/
workspaces/ logs/ run.py
```

## Verification

```powershell
ruff check .
mypy forge
pytest
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the discovery architecture and data flow.

## Incremental Project Index

```powershell
forge index
forge index ERP
forge index "D:\Software Dev\ERP"
forge index ERP --json
forge index ERP --summary
forge index ERP --changes
forge index ERP --verbose
```

The index is the canonical file-level technical inventory. It classifies engineering files, hashes content without semantic parsing, detects incremental changes and safe unambiguous moves, persists stable generations in `memory/index.json`, and writes six deterministic reports to `reports/latest/`.

Default limits are 10 MiB for complete content hashing, 64 KiB hash chunks, and 250,000 files. Configure them with `AERION_INDEX_MAX_HASH_BYTES`, `AERION_INDEX_HASH_CHUNK_BYTES`, and `AERION_INDEX_MAX_FILES`.

```text
forge/indexing/           Models, classification, fingerprinting, scanning,
                          comparison, persistence, rendering, and service
forge/core/repository_policy.py
memory/index.json
reports/latest/PROJECT_INDEX.json
reports/latest/INDEX_SUMMARY.json
reports/latest/INDEX_CHANGES.json
reports/latest/FILE_CATALOG.json
reports/latest/INDEX_SUMMARY.md
reports/latest/INDEX_CHANGES.md
```

See [docs/INDEXING.md](docs/INDEXING.md) for classification rules, protected-file handling, generation semantics, deterministic guarantees, recovery behavior, examples, and limitations. See [CHANGELOG.md](CHANGELOG.md) for milestone changes.

## Engineering Knowledge Graph

```powershell
forge graph ERP --summary
forge graph ERP --changes
forge graph ERP --orphans
forge graph ERP --validate
forge graph ERP --json
forge graph ERP --verbose
```

The graph consumes existing workspace, discovery, and project-index state without rescanning source repositories. It creates stable structural nodes and edges, validates every relationship, reports graph changes and truthful orphans, and persists atomically in `memory/knowledge_graph.json`.

```text
forge/knowledge/                 Graph models, identities, resolver, builder,
                                 validation, diff, store, reports, query, service
memory/knowledge_graph.json      Latest valid graph per repository/workspace
reports/latest/KNOWLEDGE_*.json  Deterministic portable graph artifacts
reports/latest/KNOWLEDGE_*.md    Summary, changes, and orphan reports
```

Run `forge inspect <target>` and `forge index <target>` before graph construction. See [docs/KNOWLEDGE_GRAPH.md](docs/KNOWLEDGE_GRAPH.md) for identity, resolution, evidence, confidence, validation, performance, safety, and query rules.
