# Papercuts — 2026-08-14

## Session

- model: deepseek-v4-flash
- date: 2026-08-14 03.30
- task: TASK-062-T3-FT-015-W1

## Notes

- `tail -2 <file>` fails on GNU coreutils ("unexpected argument '-2'"); must use `tail -n 2`. Cost one failed command in the gate-evidence save step.
- Two probe-file syntax errors in the red-verify session (stray `!` after string args) cost two extra write/edit cycles; write probes with the edit tool straight away instead of Write-then-fix.

## 2026-08-14 03.45 session (TASK-063)

- `rg` is not installed on this host; `rg` usage in AGENTS.md is a no-op (exit 127). Use `grep -E` with explicit counts for claim-token scans.
