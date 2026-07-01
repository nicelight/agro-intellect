# План миграции спецификаций на subject-based SDD

Дата подготовки: 2026-06-30  
Статус: implementation repaired after review; fresh-context re-review required
Основание:

- `/home/serg/Projects/DevRails 26/IDEAS/DONE/packet-reformation.md`
- `/home/serg/Projects/DevRails 26/IDEAS/DONE/specs_without_owners.md`

## 1. Цель

Перевести активный Memory Bank проекта с двух старых моделей:

1. `task card + persisted Execution Packet`;
2. `feature -> FT-* tech-spec hub -> concrete blocks`;

на целевую модель:

1. единственная authoritative task card без persisted packet;
2. feature как composition root;
3. предметные canonical specs без `FT-*` в имени и без file-owner routing;
4. direct task-to-spec links только на применимый к задаче subset specs.

Итоговая миграция не должна менять product scope, task identity, tier, wave,
dependencies, lifecycle status, acceptance semantics или реализованный код.

## 2. Зафиксированный baseline

На момент подготовки плана:

- worktree чистый;
- активны три feature-design hub:
  - `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`;
  - `.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md`;
  - `.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md`;
- FT-001 уже частично вынесен в пять отдельных документов, но они всё ещё
  содержат `feature_id`, FT-привязанные descriptions, `owner` и
  `## Ownership`;
- FT-002 и FT-003 остаются монолитными feature hubs;
- `spec-index.md` всё ещё содержит `Owner command`, `feature_design` и planned
  family `.memory-bank/tech-specs/FT-<NNN>-<slug>.md`;
- существуют 11 persisted packets для `TASK-001`--`TASK-011`;
- 11 task cards содержат `runtime_context.packet_required` и `packet_ref`;
- все семь FT-001 task cards `TASK-005`--`TASK-011` ссылаются на FT hubs;
- ни одна из этих task cards пока не использует выделенные FT-001 subject specs
  как полный direct task context;
- найдено 24 активных раздела `## Ownership` и 34 `owner:` в spec/router tree.

Сравнение всех 11 task/packet пар подтвердило:

- `packet.verification.commands == task.verification_targets`;
- packet evidence совпадает с `task.evidence_required`;
- packet stop conditions совпадают с task stop conditions;
- allowed/forbidden scope совпадает с task runtime context.

Следовательно, сохраняемая packet surface уже находится в task cards. Перед
удалением packets остаётся только semantic review их `success_checks` против
`success_outcome`, constraints, invariants и verification targets task card.

## 3. Инварианты миграции

- Один concrete concern имеет один active canonical path.
- Feature не владеет spec-файлами и не является их source of truth.
- В новых canonical specs нет `feature_id`, `FT-*` в имени или `used_by`.
- `spec-index.md` не хранит reverse usage, readiness или feature status.
- `Change route` означает допустимый workflow изменения, а не владельца файла.
- Не выполнять механическую замену всех слов `owner`/`ownership`.
- Domain/runtime authority, human responsibility, task closure ownership и
  scheduler ownership не относятся к удаляемой file-owner модели.
- Existing global subject specs не перемещаются только ради красивой taxonomy.
- Новый каталог создаётся только при фактической необходимости.
- Для каталога с более чем тремя документами создаётся `index.md` router.
- Старые hubs удаляются только после создания новых specs и переключения всех
  активных ссылок.
- `.memory-bank/archive/mvp-v1/**`, закрытые `.tasks/**` reports и завершённые
  `.protocols/**` не переписываются как будто они были созданы новой системой.
- Task cards остаются единственным authoritative execution context.
- Не создавать replacement packet, nested packet или второй task registry.

## 4. Целевая предметная карта

Пути ниже являются рекомендуемой минимальной taxonomy. Перед созданием файлов
нужно выполнить discovery по актуальному `spec-index.md`, folder indexes,
filenames и descriptions. При найденном конфликтующем canonical path создание
нового файла блокируется до reconciliation.

### 4.1 FT-001: identity, sessions и ActorContext

#### Текущие источники

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
- `.memory-bank/domains/local-identity-session-data.md`
- `.memory-bank/contracts/local-session-security.md`
- `.memory-bank/contracts/local-session-api.md`
- `.memory-bank/contracts/actor-context.md`
- `.memory-bank/testing/ft-001-access-auth.md`

#### Целевые canonical specs

1. `.memory-bank/domains/identity/account-membership.md`
   - `Account` и `FarmMembership` relational shape;
   - UUID, status/role checks, login normalization и indexes;
   - Account-to-membership relation;
   - deferred `farm_memberships.farm_id` FK boundary.

2. `.memory-bank/domains/auth/session-storage.md`
   - `LocalSession` relational shape;
   - `token_hash` storage и indexes;
   - timestamps, account relation и отсутствие raw token storage.

3. `.memory-bank/contracts/auth/session-security.md`
   - Argon2id credentials;
   - opaque session-token generation/hashing/comparison;
   - cookie и optional bearer security/transport rules;
   - redaction requirements для auth material.

4. `.memory-bank/states/auth/session-lifecycle.md`
   - activation, active, expiry и revocation;
   - login/logout behavior;
   - disabled Account/Membership effect;
   - отсутствие refresh-token lifecycle.

5. `.memory-bank/contracts/auth/session-http.md`
   - login/logout/me routes;
   - request/response/error catalog;
   - cookie emission/clearing behavior;
   - no-account-enumeration и no-leak rules.

6. `.memory-bank/contracts/access/actor-context.md`
   - role presets;
   - `ActorContext` shape;
   - `PlantPermissionContext` shape;
   - protected entrypoint и context-builder rules;
   - concrete Plant resolver semantics из FT-002 после их reconciliation.

7. `.memory-bank/testing/auth/session-and-access.md`
   - cross-contract verification matrix без FT/task ownership;
   - storage, security, lifecycle, HTTP и authorization checks;
   - executable evidence expectations.

#### Решения по текущему hub

- Перенести только composition/use-case/non-goal информацию в feature doc.
- Не сохранять compatibility facade как active canonical spec.
- После переключения ссылок удалить FT-001 hub.

### 4.2 FT-002: Farm, Plant и PlantAccessGrant

#### Текущий источник

- `.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md`

#### Целевые canonical specs

1. `.memory-bank/domains/farm/farm-plant-access-storage.md`
   - `Farm`, `Plant`, `PlantAccessGrant` relational shape;
   - constraints и indexes;
   - single-Farm seed;
   - `tomato_001` seed;
   - final `farm_memberships.farm_id -> farms.farm_id RESTRICT` migration;
   - zero/one/conflicting Farm UUID migration behavior.

2. `.memory-bank/states/plants/plant-and-access-lifecycle.md`
   - Plant create/archive/restore;
   - retained-history effects;
   - PlantAccessGrant grant/update/revoke;
   - interaction между archived Plant и retained active grant.

3. Расширение `.memory-bank/contracts/access/actor-context.md`
   - authorization matrix;
   - concrete PlantPermissionContext resolver;
   - Boss/granted Engineer/granted Consultant semantics;
   - archived/retained-history behavior;
   - denied/no-existence-leak behavior.

   Отдельный competing `plant-permission-context.md` не создавать, пока
   discovery не докажет, что ActorContext и PlantPermissionContext имеют разные
   consumers/change cadence и действительно требуют split.

4. `.memory-bank/contracts/plants/plant-http.md`
   - Plant list/create/read/archive/restore routes;
   - retained-history entrypoint;
   - PlantAccessGrant routes;
   - payloads и stable error catalog.

5. `.memory-bank/testing/plants/lifecycle-and-access.md`
   - migration/storage checks;
   - lifecycle checks;
   - resolver compatibility;
   - route authorization и retained-history integration;
   - Boss/Engineer/Consultant e2e expectations.

#### Cross-feature handoff

- Admin audit write requirement ссылается на canonical admin-audit spec FT-003.
- FT-002 не определяет второй AdminAuditRecord contract.
- После переключения ссылок удалить FT-002 hub.

### 4.3 FT-003: Boss admin, local invite и admin audit

#### Текущий источник

- `.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md`

#### Целевые canonical specs

1. `.memory-bank/domains/identity/local-invite-storage.md`
   - `LocalInviteCredential` relational shape;
   - status, identity refs, hash и timestamps;
   - one-time secret persistence boundary.

2. `.memory-bank/states/auth/local-invite-lifecycle.md`
   - pending/accepted/revoked/expired;
   - Account/Membership transition effects;
   - revoke/expiry/activation guards;
   - last-active-Boss protection where applicable.

3. `.memory-bank/contracts/auth/local-invite.md`
   - secret generation/validation/redaction;
   - public invite activation HTTP boundary;
   - constrained activation context;
   - handoff к session security/lifecycle;
   - `AUTH_ACTIVATION_INVALID` и связанные errors.

4. `.memory-bank/domains/admin/admin-audit.md`
   - `AdminAuditRecord` shape;
   - action/target taxonomy;
   - same-transaction write semantics;
   - compact safe before/after summaries;
   - cross-feature use из Plant/access mutations.

5. `.memory-bank/contracts/admin/boss-admin-http.md`
   - account/personnel list;
   - local invite creation;
   - disable/role operations;
   - admin Plant projection;
   - admin audit read;
   - Boss-only authorization и safe responses.

6. `.memory-bank/testing/admin/boss-admin-and-audit.md`
   - Boss-only policy;
   - invite lifecycle/security;
   - last-active-Boss guard;
   - exactly-one audit write;
   - admin/context-isolation integration;
   - first-demo Boss-to-Engineer path.

#### Feature-local content

Минимальный UI composition, use cases, acceptance criteria и non-goals остаются
в `FT-003` feature doc. Отдельная UI spec создаётся только если будущая task
decomposition требует самостоятельного UI boundary с собственными consumers и
verification contract.

После переключения ссылок удалить FT-003 hub.

## 5. Нормализация существующих global subject specs

Следующие документы уже имеют предметные имена и в большинстве случаев не
требуют move/split:

```text
.memory-bank/architecture/foundation-runtime-substrate.md
.memory-bank/contracts/agent-chat-bus.md
.memory-bank/contracts/api-guidelines.md
.memory-bank/contracts/evidence-redaction.md
.memory-bank/contracts/foundation-smoke-api.md
.memory-bank/contracts/message-envelope.md
.memory-bank/contracts/timeline-event.md
.memory-bank/contracts/ui-feed.md
.memory-bank/domains/foundation-data-substrate.md
.memory-bank/domains/photo-artifacts.md
.memory-bank/domains/runtime-data-model.md
.memory-bank/states/companion-governance.md
.memory-bank/states/dataset-governance.md
.memory-bank/states/plant-state-trust.md
.memory-bank/states/safety-action-lifecycle.md
.memory-bank/testing/foundation-test-harness.md
.memory-bank/runbooks/foundation-local-runtime.md
```

Для каждого документа выполнить semantic cleanup:

1. Сохранить path и behavioral contract, если discovery не выявил конфликт.
2. Заменить file-routing `## Ownership` на:
   - `## Scope`;
   - `## Out of scope` при необходимости;
   - `## Related specs` при необходимости.
3. Заменить `authoritative owner`/`natural owner` только в значении
   file-routing на `canonical spec`, `canonical path`, `spec scope`.
4. Не менять выражения о runtime/domain authority.
5. Удалить `owner:` только если это старый workflow/file-routing marker.
6. Если `owner:` является осмысленным human maintainer metadata, можно
   сохранить его, но он не должен участвовать в discovery/readiness.
7. Обновить `source_of_truth` и relative links после moves.

Отдельно проверить metadata-only документы без `## Ownership`:

```text
.memory-bank/adrs/ADR-000-template.md
.memory-bank/architecture/system-architecture.md
.memory-bank/contracts/boundary-map.md
.memory-bank/contracts/index.md
.memory-bank/domains/core-domain.md
.memory-bank/domains/index.md
.memory-bank/states/index.md
.memory-bank/states/lifecycle-map.md
.memory-bank/testing/index.md
```

Здесь нельзя автоматически удалять domain ownership или human responsibility.
Меняется только старое file-owner/spec-routing значение.

## 6. Registry и folder routers

### 6.1 `.memory-bank/spec-index.md`

Перестроить registry на таблицу:

```text
| Type | Path | Status | Scope | Change route |
```

Удалить:

- колонку `Spec` как отдельную canonical identity, если она дублирует path;
- `Owner command`;
- все строки `feature_design` для FT-001/002/003 hubs;
- planned family `.memory-bank/tech-specs/FT-<NNN>-<slug>.md`;
- wording про feature owner/hub;
- `feature_id`/`used_by`-подобную reverse usage информацию.

Добавить отдельную строку для каждого нового subject path. `Change route`
должен описывать допустимый workflow, например `/spec-design or
/prd-to-tasks`, но не ownership.

### 6.2 Folder indexes

Обновить:

```text
.memory-bank/contracts/index.md
.memory-bank/domains/index.md
.memory-bank/states/index.md
.memory-bank/testing/index.md
```

Добавить nested `index.md` только для подкаталогов, в которых окажется более
трёх документов. Не создавать пустые routers заранее.

### 6.3 Global routing descriptions

Обновить descriptions и routing в:

```text
.memory-bank/index.md
.memory-bank/spec-backbone.md
.memory-bank/invariants.md
.memory-bank/glossary.md
.memory-bank/architecture/system-architecture.md
.memory-bank/foundation.md
.memory-bank/contracts/boundary-map.md
.memory-bank/changelog.md
```

Основные замены:

- feature hub/owning feature design -> subject-spec discovery;
- feature-local schema/spec owner -> canonical spec path/scope;
- packet/spec readiness -> single-card + linked-spec readiness;
- feature design remains a process/status, но не тип FT hub-файла.

Исторические changelog записи сохранить по смыслу. Если удаляемый hub path был
Markdown-ссылкой, заменить ссылку на feature doc/new canonical specs либо
превратить старый path в code literal с отметкой `removed during migration`,
чтобы не оставлять broken links и не переписывать историю события.

## 7. Feature docs как composition roots

Обновить:

```text
.memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
.memory-bank/features/FT-002-farm-plant-lifecycle-access-grants.md
.memory-bank/features/FT-003-boss-admin-surface-admin-audit.md
.memory-bank/features/index.md
.memory-bank/epics/EP-001-local-farm-access-admin.md
```

Для каждой feature:

1. Сохранить use cases, acceptance criteria, edge cases, behavior specs,
   verification targets и non-goals.
2. Сохранить `spec_design_status`.
3. Заменить `spec_design_links` на direct canonical subject paths.
4. Удалить hub path из `spec_design_links` и `source_of_truth`.
5. Удалить тексты `feature hub`, `feature owns`, `authoritative owner`.
6. Добавить короткий composition summary: какая spec зачем применима.
7. Не копировать concrete fields, DB indexes, endpoint schemas, error catalog
   или state transitions из linked specs.

Предлагаемые composition links:

### FT-001

```text
domains/identity/account-membership.md
domains/auth/session-storage.md
contracts/auth/session-security.md
states/auth/session-lifecycle.md
contracts/auth/session-http.md
contracts/access/actor-context.md
testing/auth/session-and-access.md
```

### FT-002

```text
domains/farm/farm-plant-access-storage.md
states/plants/plant-and-access-lifecycle.md
contracts/access/actor-context.md
contracts/plants/plant-http.md
domains/admin/admin-audit.md
testing/plants/lifecycle-and-access.md
```

### FT-003

```text
domains/identity/account-membership.md
contracts/auth/session-security.md
states/auth/session-lifecycle.md
contracts/auth/session-http.md
contracts/access/actor-context.md
domains/identity/local-invite-storage.md
states/auth/local-invite-lifecycle.md
contracts/auth/local-invite.md
domains/admin/admin-audit.md
contracts/admin/boss-admin-http.md
testing/admin/boss-admin-and-audit.md
```

## 8. Single-card task migration

Этот шаг выполняется после развёртывания framework с новой task schema, но до
нового `/review-tasks-plan FT-001`.

### 8.1 Удалить packet fields

Из `TASK-001`--`TASK-011` удалить:

```json
"packet_required"
"packet_ref"
```

Сохранить в `runtime_context`:

- `allowed_write_scope`;
- `forbidden_scope`;
- `stop_conditions`.

Не менять:

- task ID;
- tier;
- feature;
- wave;
- dependencies;
- lifecycle status;
- purpose/success outcome;
- gates/evidence/verification;
- closure evidence уже завершённых FT-000 tasks.

### 8.2 Удалить persisted packets

После schema-valid task migration удалить:

```text
.memory-bank/packets/TASK-001-T2-FT-000-W0.packet.json
.memory-bank/packets/TASK-002-T2-FT-000-W0.packet.json
.memory-bank/packets/TASK-003-T3-FT-000-W0.packet.json
.memory-bank/packets/TASK-004-T2-FT-000-W0.packet.json
.memory-bank/packets/TASK-005-T3-FT-001-W1.packet.json
.memory-bank/packets/TASK-006-T3-FT-001-W1.packet.json
.memory-bank/packets/TASK-007-T3-FT-001-W2.packet.json
.memory-bank/packets/TASK-008-T3-FT-001-W2.packet.json
.memory-bank/packets/TASK-009-T3-FT-001-W2.packet.json
.memory-bank/packets/TASK-010-T3-FT-001-W3.packet.json
.memory-bank/packets/TASK-011-T3-FT-001-W3.packet.json
```

Удалить каталог `.memory-bank/packets/`, если он пуст.

### 8.3 Обновить local framework/control surfaces

Новая framework deployment должна согласовать:

```text
AGENTS.md
.memory-bank/schemas/task.schema.json
.memory-bank/roles/general.md
.memory-bank/workflows/tier-policy.md
.memory-bank/workflows/execute-loop.md
.memory-bank/workflows/mb-sync.md
.memory-bank/workflows/autonomy-policy.md
scripts/mb-lint.mjs
scripts/mb-doctor.mjs
.memory-bank/tasks/plans/IMPL-FT-000.md
.memory-bank/tasks/plans/IMPL-FT-001.md
```

Не править generated skill copies как canonical source.

## 9. Direct spec links в FT-001 task cards

Во всех task cards заменить hub links в `source_artifacts` и
`normative_inputs`. Каждая T3 task получает только применимый subset.

### TASK-005 — schema baseline

Direct specs:

```text
.memory-bank/domains/identity/account-membership.md
.memory-bank/domains/auth/session-storage.md
.memory-bank/domains/runtime-data-model.md
.memory-bank/domains/foundation-data-substrate.md
.memory-bank/contracts/evidence-redaction.md
```

Удалить ссылки на FT-001/FT-002 hubs. Deferred Farm FK должен ссылаться на
account-membership и farm-plant-access-storage canonical specs.

### TASK-006 — security primitives

Direct specs:

```text
.memory-bank/contracts/auth/session-security.md
.memory-bank/domains/auth/session-storage.md
.memory-bank/contracts/evidence-redaction.md
```

### TASK-007 — session lifecycle services

Direct specs:

```text
.memory-bank/domains/auth/session-storage.md
.memory-bank/contracts/auth/session-security.md
.memory-bank/states/auth/session-lifecycle.md
.memory-bank/contracts/auth/local-invite.md
```

`local-invite` нужен только для activation handoff; task не получает весь
Boss-admin contract.

### TASK-008 — ActorContext и role policy

Direct specs:

```text
.memory-bank/contracts/access/actor-context.md
.memory-bank/states/plants/plant-and-access-lifecycle.md
.memory-bank/domains/farm/farm-plant-access-storage.md
```

Последние две ссылки нужны только для concrete resolver compatibility и не
расширяют write scope до FT-002 persistence.

### TASK-009 — session HTTP API

Direct specs:

```text
.memory-bank/contracts/auth/session-http.md
.memory-bank/contracts/auth/session-security.md
.memory-bank/states/auth/session-lifecycle.md
.memory-bank/contracts/access/actor-context.md
.memory-bank/contracts/foundation-smoke-api.md
```

### TASK-010 — protected seams/context builders

Direct specs:

```text
.memory-bank/contracts/access/actor-context.md
.memory-bank/contracts/agent-chat-bus.md
.memory-bank/contracts/message-envelope.md
.memory-bank/contracts/ui-feed.md
.memory-bank/states/plants/plant-and-access-lifecycle.md
```

Не подключать весь FT-002 spec set или Plant HTTP contract, если task не
реализует Plant routes.

### TASK-011 — integration gate/docs sync

Direct specs:

```text
.memory-bank/testing/auth/session-and-access.md
.memory-bank/domains/identity/account-membership.md
.memory-bank/domains/auth/session-storage.md
.memory-bank/contracts/auth/session-security.md
.memory-bank/states/auth/session-lifecycle.md
.memory-bank/contracts/auth/session-http.md
.memory-bank/contracts/access/actor-context.md
```

Global contracts добавляются только если соответствующий integration check
действительно находится в TASK-011 verification surface.

### Общие правила task link migration

- Feature doc может оставаться в `source_artifacts` как product composition.
- Canonical specs размещаются в `normative_inputs` или другом существующем
  task field, предназначенном для authoritative rules.
- Hub paths удаляются из всех task fields, constraints, invariants и text.
- Wording `FT-001 owns`/`FT-002 owns` заменить только там, где речь о файле.
- Domain implementation boundary выразить через canonical scope, например:
  `Plant persistence is outside this task and specified by ...`.
- После link rewrite проверить T2/T3 single-card completeness contract.

## 10. Cross-reference migration inventory

Помимо самих specs и task cards проверить и обновить активные ссылки в:

```text
.memory-bank/changelog.md
.memory-bank/domains/runtime-data-model.md
.memory-bank/epics/EP-001-local-farm-access-admin.md
.memory-bank/features/index.md
.memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
.memory-bank/features/FT-002-farm-plant-lifecycle-access-grants.md
.memory-bank/features/FT-003-boss-admin-surface-admin-audit.md
.memory-bank/spec-index.md
.memory-bank/tasks/plans/IMPL-FT-001.md
.memory-bank/testing/index.md
```

Также обновляются взаимные `source_of_truth`/`Related specs` в мигрируемых
FT-001/002/003 specs.

Не выполнять массовую замену в:

- `.memory-bank/archive/mvp-v1/**`;
- закрытых `.tasks/**` evidence reports;
- завершённых task-specific `.protocols/**`;
- generated `.agents/**` и `.claude/**`.

Текущие operational artifacts с packet/hub wording сохраняются как history.
Актуальный task-plan review после миграции создаёт новый evidence/report и
supersedes старый review, а не переписывает его задним числом.

## 11. Порядок выполнения

### Wave 0 — prerequisite framework deployment

1. Развернуть framework с single-card schema и subject-spec routing.
2. Подтвердить отсутствие `/mb-packet` и packet generation в поставке.
3. Не запускать task execution между deployment и завершением task migration.

### Wave 1 — single-card migration

1. Semantic-check packet success checks против task cards.
2. Удалить packet fields из `TASK-001`--`TASK-011`.
3. Удалить persisted packets.
4. Проверить schema/index/ID/dependency completeness.

### Wave 2 — canonical path lock

1. Построить concern coverage table для FT-001/002/003.
2. Проверить существующие paths и descriptions.
3. Зафиксировать final slugs и split decisions.
4. Заблокировать создание при duplicate concern.

### Wave 3 — создать/перенести subject specs

1. Сначала создать новые paths и перенести normative content.
2. Разделить data/state/HTTP/security/testing boundaries.
3. Удалить feature metadata из spec frontmatter.
4. Добавить Scope/Out of scope/Related specs.
5. Проверить отсутствие дублированных contract blocks.

### Wave 4 — registry и composition cutover

1. Обновить `spec-index.md`.
2. Обновить folder indexes.
3. Обновить FT-001/002/003 `spec_design_links`.
4. Обновить EP/features/root routing docs.
5. Проверить все новые links до удаления hubs.

### Wave 5 — task direct-link cutover

1. Обновить `IMPL-FT-001.md`.
2. Обновить `TASK-005`--`TASK-011` по mapping выше.
3. Удалить hub links и file-owner wording.
4. Проверить single-card completeness каждой task.

### Wave 6 — удалить obsolete hubs

1. Убедиться, что active reverse-reference search пуст.
2. Удалить три `.memory-bank/tech-specs/FT-*` hubs.
3. Удалить `.memory-bank/tech-specs/`, если каталог пуст.
4. Не создавать replacement compatibility facade.

### Wave 7 — global terminology cleanup

1. Нормализовать 17 existing subject specs.
2. Классифицировать остальные `owner` occurrences.
3. Обновить spec/backbone/glossary/invariants descriptions.
4. Сохранить domain/runtime/task ownership semantics.

### Wave 8 — review и readiness

1. Запустить deterministic gates.
2. Выполнить fresh-context `/review-tasks-plan FT-001`.
3. Не считать старый `APPROVE` действительным после смены task/spec paths.
4. Только после нового `APPROVE` разрешить `/execute TASK-005`.

## 12. Проверки

### Structural searches

Все searches выполняются с исключением archive и historical operational
artifacts, где это указано.

```bash
rg -n "tech-specs/FT-|feature hub|Owner command|authoritative owner|natural owner" \
  .memory-bank --glob '!archive/**'

rg -n 'feature_id:|^## Ownership$' \
  .memory-bank/architecture \
  .memory-bank/contracts \
  .memory-bank/domains \
  .memory-bank/states \
  .memory-bank/testing \
  .memory-bank/runbooks

rg -n 'packet_required|packet_ref|\.memory-bank/packets/|/mb-packet' \
  AGENTS.md .memory-bank scripts

find .memory-bank/packets -type f
```

Ожидаемый результат:

- нет active FT hub paths;
- нет file-routing ownership terminology;
- нет `feature_id` в canonical specs;
- нет packet directory/fields/commands;
- допустимые domain/task/human ownership occurrences вручную классифицированы.

### Link and registry checks

- Каждый path в `spec-index.md` существует.
- Каждый feature `spec_design_link` существует и зарегистрирован.
- Каждый T2/T3 task имеет минимум один direct relevant SDD spec path.
- Task не ссылается только на `spec-index.md` или feature doc.
- В registry нет duplicate active scope.
- Folder indexes содержат новые paths.
- Нет broken links после удаления hubs.

### Project gates

```bash
node scripts/mb-lint.mjs
node scripts/mb-doctor.mjs --strict
git diff --check
```

Дополнительно:

- fresh-context review FT-001 task queue;
- semantic check task/spec applicability;
- проверка неизменности task IDs, tiers, waves, dependencies и statuses;
- проверка, что migration не затронула backend/tests/runtime behavior.



## 13. Definition of Done

- `.memory-bank/tech-specs/` отсутствует либо не содержит FT hubs.
- Все FT-001/002/003 concrete concerns имеют ровно один canonical subject path.
- Features содержат только composition links и product behavior.
- `spec-index.md` использует `Path` и `Change route`, без owner model.
- Все FT-001 T3 task cards напрямую ссылаются на применимые specs.
- Persisted packets и packet fields отсутствуют.
- Single-card handoff completeness подтверждена для всех T2/T3 tasks.
- Global specs не содержат file-routing Ownership sections.
- Domain/runtime/human/task ownership semantics не повреждены.
- Archive и historical evidence не переписаны.
- `mb-lint`, strict `mb-doctor` и `git diff --check` проходят.
- Новый `/review-tasks-plan FT-001` возвращает `APPROVE`.
