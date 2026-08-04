# M3.3 Security and Transaction Model

## Security controls

- Repository-relative paths only.
- Parent traversal and absolute paths are rejected.
- Protected directories are rejected.
- Resolved paths must remain within the repository.
- Symlink escapes are rejected.
- Binary and oversized files will be rejected by the loader.
- Apply requests require explicit approval.

## Transaction rules

1. Load and fingerprint all target files.
2. Validate every operation before any write.
3. Produce all edited contents and diffs in memory.
4. Snapshot every target.
5. Write through temporary files.
6. Replace targets atomically where supported.
7. On any failure, restore every file already changed.
8. Report both the original failure and any rollback failure.