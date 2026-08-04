# M3.5 Security Model

Controls include:

- repository-relative paths only;
- protected-path rejection;
- source-fingerprint verification;
- maximum attempts;
- maximum files and changed bytes;
- explicit approval;
- no arbitrary shell;
- no Git mutation;
- no dependency changes;
- rollback on failed validation;
- stop on unexpected repository-state change.