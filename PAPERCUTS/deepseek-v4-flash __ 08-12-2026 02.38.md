# Papercuts

## Task cards live under `.memory-bank/tasks/`, not `.tasks/`
Indexed `*.task.json` cards are stored in `.memory-bank/tasks/` (per
`.memory-bank/tasks/index.json` file entries), while task evidence/protocols
live under `.tasks/TASK-<id>/`. Globbing `.tasks/TASK-059*/**` or
`**/TASK-059-T2-FT-014-W6.task.json` finds nothing, which reads like the card
is missing; only `find` (or reading the index first) reveals the card path.
Fix for a Reviewer/executor: resolve `.memory-bank/tasks/index.json` first,
then read `.memory-bank/tasks/<id>.task.json`.
