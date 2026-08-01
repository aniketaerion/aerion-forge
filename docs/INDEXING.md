# Incremental Project Index

The Version 0.2 Milestone 1.3 index is Forge's canonical file-level technical inventory. Discovery describes a repository at a high level; indexing records relevant files and reports what changed between stable repository states. It does not parse source semantics, imports, symbols, APIs, or dependency relationships.

## Commands

```powershell
forge index
forge index ERP
forge index "D:\Software Dev\ERP"
forge index ERP --json
forge index ERP --summary
forge index ERP --changes
forge index ERP --verbose
```

Target resolution uses an explicit workspace or path, then the active workspace, then the current directory.

## Architecture

`ProjectIndexScanner` performs a single sorted traversal using the shared discovery exclusion policy. `classifier.py` applies conservative path and extension rules. `FileFingerprinter` hashes eligible files in chunks. `IndexingService` compares complete current state with the previous successful state, renders reports, and commits through `ProjectIndexStore` only after reports succeed.

The schema version is `1.0`. Direct paths are keyed by a SHA-256 identity; registered workspaces use their immutable workspace ID. Absolute repository paths are not written to portable reports.

## Classification

File categories include source, test, configuration, manifest, lockfile, migration, schema, documentation, build, CI/CD, container, Kubernetes, infrastructure, script, asset, localization, generated, and unknown.

Engineering roles include frontend, backend, database, API, domain, service, controller, model, repository, UI, state management, test, build, deployment, infrastructure, documentation, mobile, embedded, robotics, firmware, configuration, shared library, and unknown. Weak evidence remains `unknown`.

Repository areas are inferred only from stable boundaries such as `apps/<name>`, `services/<name>`, `packages/<name>`, `libs/<name>`, and recognized top-level engineering directories.

## Fingerprints

Forge uses SHA-256 and 64 KiB chunks by default:

- `full_content`: complete files at or below 10 MiB.
- `bounded_sample`: file size plus bounded first and last chunks for larger files.
- `protected_content`: chunked hashing for protected files at or below the limit.
- `protected_bounded_sample`: protected large-file sampling.
- `none`: files explicitly skipped or unreadable.

The defaults are configured through `AERION_INDEX_MAX_HASH_BYTES`, `AERION_INDEX_HASH_CHUNK_BYTES`, and `AERION_INDEX_MAX_FILES`. No timestamp contributes to content changes or repository-state fingerprints.

Protected patterns include `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials*`, `secrets*`, `id_rsa`, and `id_ed25519`. Their contents never appear in logs or reports. This milestone does not perform secret scanning.

## Incremental Changes

Added, modified, removed, unchanged, failed, and skipped files are reported explicitly. A move is reported only when exactly one removed file and one added file share the same content fingerprint. Duplicate fingerprints remain separate added and removed changes.

Classification and engineering-role changes cause reconsideration even when content is unchanged. Timestamp-only changes do not. State fingerprints use normalized paths, content fingerprints, relevant classification, status, and schema version in deterministic order.

An unchanged repository retains its logical state generation, making second and later unchanged reports byte-identical. When state changes, `previous_generation_id` points to the prior successful state.

## Safety And Recovery

Dependency, generated-output, build, cache, Git, and Forge report directories are excluded. The configured `memory/index.json` is explicitly excluded when it is inside the target. Symlinks are never followed; file symlinks are recorded as skipped. Hashing uses bounded memory and source contents are never interpreted.

The index store is validated before use and atomically replaced with `fsync` plus rename. Missing persistence creates an empty schema. Corrupt or incompatible persistence fails explicitly. Scan, limit, or report failures leave the previous valid index intact.

## Artifacts

```text
PROJECT_INDEX.json
INDEX_SUMMARY.json
INDEX_CHANGES.json
FILE_CATALOG.json
INDEX_SUMMARY.md
INDEX_CHANGES.md
memory/index.json
```

Artifacts omit timestamps, use normalized relative paths, sort collections, and exclude absolute repository locations.

## Product Examples

- ERP and CRM: index backend services, frontend applications, database migrations, domain models, tests, manifests, and deployment configuration.
- GCS: index UI, telemetry services, native code, configuration, and infrastructure boundaries.
- Flutter: classify Dart under mobile and record Flutter manifests, assets, localization, tests, and build files.
- PX4 and embedded: classify firmware and embedded C/C++ files while using bounded hashing for large binary assets.
- ROS2: classify robotics areas, C++ or Python nodes, launch configuration, manifests, and tests.

## Deferred Scope

The index contains no AST, symbol, import, API, database-relationship, dependency, or knowledge graph. It does not build, test, edit, generate, plan, commit, embed, or invoke an LLM. Those capabilities remain deferred.
