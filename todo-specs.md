# FT-001 SDD Findings

Дата аудита: 2026-06-27

## Итог

Структурно SDD routing полный. По решению KISS сейчас добавляются только
спецификации, без которых ближайшая задача должна угадывать security-sensitive
storage behavior. Остальные пункты являются отложенными review triggers, а не
текущими блокерами.

## RESOLVED - TASK-005 KISS Storage Contract

`/spec-improve FT-001` добавил минимальный обязательный storage contract:

- `password_hash` хранится как unbounded text с Argon2id PHC;
- active Account обязан иметь hash;
- Account, отключённый до активации, может иметь `password_hash=null`;
- `token_hash` имеет длину 64, lowercase SHA-256 hex, `NOT NULL`, unique lookup;
- raw session token не имеет storage column;
- определены edge cases и verification targets для `TASK-005`/`TASK-006`.

Более широкие SQL/Pydantic types, ID/timestamp conventions, API DTO и callable
interfaces намеренно не добавлялись: они не требуются для этого KISS repair.

Затронутые источники:

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`:
  `Data Model`, `Migration And Indexing Targets`.
- `.memory-bank/tasks/TASK-005-T3-FT-001-W1.task.json`.
- `.memory-bank/tasks/TASK-007-T3-FT-001-W2.task.json`.
- `.memory-bank/tasks/TASK-009-T3-FT-001-W2.task.json`.

## DEFERRED REVIEW TRIGGER - API Contract TASK-009

FT-001 описывает endpoints, request/response fields, cookie transport и error
codes, но не фиксирует точные типы, обязательность, validation и serialization
rules.

Неопределённые части:

- `plant_scope_summary` описан как пример safe summary без окончательной схемы;
- bearer token может возвращаться в response field или header, но конкретный
  transport contract не выбран;
- не определены wire formats для timestamps и identifiers;
- отсутствуют точные validation constraints для `login_name` и `password`;
- не зафиксирована обязательность/nullable policy всех response fields.

Затронутые источники:

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`:
  `Session Cookie And Bearer Transport Contract`, `API Surface`,
  `Error Contract`.
- `.memory-bank/tasks/TASK-009-T3-FT-001-W2.task.json`.
- `.memory-bank/tasks/TASK-011-T3-FT-001-W3.task.json`.

## DEFERRED REVIEW TRIGGER - Component Contracts TASK-006 - TASK-010

Гарантии компонентов описаны семантически, но отсутствуют точные Python-level
contracts для handoff между задачами:

- `TASK-006`: функции password hash/verify и session token generate/hash/verify;
- `TASK-007`: repository/session/credential service inputs, outputs, exceptions
  и transaction boundary;
- `TASK-008`: callable protocol для `plant_permission_resolver`;
- `TASK-010`: точная структура результата context builder и
  `authorization_scope`.

Это оставляет выбор function signatures, DTO/result types, sync/async behavior,
exception mapping и transaction ownership на этапе реализации.

Затронутые источники:

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`:
  `Credential And Session Primitive Contract`, `Session Lifecycle`,
  `ActorContext`, `Context Builder Rules`, internal activation primitive.
- `.memory-bank/tasks/TASK-006-T3-FT-001-W1.task.json`.
- `.memory-bank/tasks/TASK-007-T3-FT-001-W2.task.json`.
- `.memory-bank/tasks/TASK-008-T3-FT-001-W2.task.json`.
- `.memory-bank/tasks/TASK-010-T3-FT-001-W3.task.json`.

## Coverage Matrix

| Scope | Состояние |
|---|---|
| FT-001 Architecture Specification | Покрыта global architecture и feature hub |
| FT-001 Event Contract | `not_applicable`: event publication явно вне ownership FT-001 |
| TASK-005 | Минимальный security-sensitive storage contract добавлен |
| TASK-006 | Security semantics полные; callable contract частичный |
| TASK-007 | Lifecycle полный; service/transaction contract частичный |
| TASK-008 | ActorContext shape полный; resolver protocol частичный |
| TASK-009 | API/Data DTO contract неполный |
| TASK-010 | Authz rules полные; context-builder output contract неполный |
| TASK-011 | Integration gate покрыт, но зависит от устранения пробелов выше |

## Не является пробелом

- Отдельный SDD-файл для каждой задачи не требуется: проект использует
  `single-file` feature-design strategy.
- Event Contract для FT-001 не требуется: feature не публикует собственные Bus,
  MessageEnvelope или UI Feed events; соответствующие global contracts нужны
  только как ограничения context hygiene.
- Architecture Specification покрыта сочетанием
  `.memory-bank/architecture/system-architecture.md`,
  `.memory-bank/architecture/foundation-runtime-substrate.md` и FT-001 feature
  design.

## Repair Route

1. Обновить существующий `TASK-005` record и packet через
   `/prd-to-tasks FT-001`.
2. Повторить `/review-tasks-plan FT-001` и conditional `/mb-doctor`.
3. Проверять deferred API/component пункты непосредственно перед их задачами и
   добавлять только те решения, без которых реализация действительно должна
   угадывать публичный или cross-task contract.
