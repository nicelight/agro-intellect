# План исправления `/autopilot` workflow

## Цель

Устранить противоречия и неоднозначность scheduler lifecycle без новых
canonical artifacts, schemas, registries или отдельной scheduler state machine.

## План правок

1. Сделать `.memory-bank/workflows/tier-policy.md` единственным владельцем
   closure, retry, failure-budget и evidence semantics. Остальные workflows и
   skills должны ссылаться на него и не повторять собственные closure rules.
2. Оставить `scripts/mb-lint.mjs` structural validator: schema shape, task IDs,
   dependencies, links и task-record consistency. Удалить из lint hard checks
   наличия protocol/PASS/FAIL artifacts.
3. Синхронизировать JSON Schema и lint для `gates`: запретить дополнительные
   поля и требовать непустые `name`/`command`.
4. Формализовать report numbering: суффикс `-NN` — execution attempt; reports
   не перезаписываются; `/execute`, `/verify` и `/red-verify` одной попытки
   используют один номер.
5. Проверять verdict последней попытки, а не любой исторический PASS/FAIL.
6. Добавить в `/autopilot` компактный recovery-first порядок для уже
   `in_progress` task на основе существующих protocol/report artifacts. При
   неоднозначности scheduler останавливается и ничего не угадывает.
7. Заменить двусмысленный `max_retries_per_task: 2` на
   `max_attempts_per_task: 2`: initial attempt + один bounded retry.
8. После исчерпания attempts фиксировать `failed`, блокировать dependents и
   останавливать `/autopilot`. Follow-up создаётся только отдельным normal
   planning flow.
9. Держать `.protocols/AUTONOMOUS-RUN/status.md` как snapshot только текущего
   run; история остаётся в task protocols, immutable reports и Git.
10. Для T3 запускать `/verify` и `/red-verify` в разных fresh sessions.
11. Уточнить, что `wave` feature-local и boundary определяется парой
    `(feature, wave)`; новых полей не добавлять.
12. Удалить unconditional final `/review-tasks-plan`; повторять review только
    после изменения planning surface.
13. Добавить минимальные regression fixtures для structural lint, latest
    attempt selection и queue recovery edge cases.

## Не входит в scope

- `current.json` или другая новая persisted scheduler state machine;
- отдельный state helper/daemon;
- canonical review manifest или новый fingerprint artifact;
- global wave/batch identifier;
- автоматическое создание follow-up task внутри `/autopilot`;
- изменение маточного DevRails/generator flow.

## Проверка

- Node fixture tests;
- `node scripts/mb-lint.mjs`;
- `node scripts/mb-doctor.mjs --strict --json`;
- schema-aligned validation текущих task records через `mb-lint` и fixtures;
- синхронность `.agents/skills` и `.claude/skills` для изменённых skills;
- `git diff --check`.
