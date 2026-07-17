# FT-013 optimized reading manifest

Цель manifest — сохранить минимальный достаточный контекст для
`/prd-to-tasks FT-013`. Это не плоская очередь чтения: переходить к следующему
этапу нужно только после того, как предыдущий подтвердил соответствующий design
pressure.

## Правила использования

1. Обязательный project/skill context читается один раз и не перечитывается в
   decision-группах.
2. `tasks/index.json` и чужие task cards сначала проверяются точечными
   metadata-запросами; целиком они читаются только при доказанной semantic
   dependency.
3. Диапазоны canonical specs используются для triage. Если документ признан
   реальным кандидатом на `reuse|extend`, `/prd-to-tasks` требует прочитать его
   целиком до изменения или task handoff.
4. Plans, protocols, behavior specs, tests и brownfield code не определяют
   product semantics и читаются только после закрытия соответствующих
   normative concerns.
5. Один и тот же диапазон не читается повторно ради другой decision-группы.

## P0 — обязательный prime и preflight

### P0.1 Project и workflow context — читать целиком

```text
AGENTS.md:1-150
.agents/skills/prd-to-tasks/SKILL.md:1-560
.memory-bank/constitution.md:1-78
.memory-bank/mbb/index.md:1-39
.memory-bank/spec-backbone.md:1-119
.memory-bank/spec-index.md:1-116
.memory-bank/index.md:1-37
.memory-bank/roles/general.md:1-38
```

### P0.2 Feature и blocker scan — читать первым после prime

Feature читается целиком, включая frontmatter: именно там проверяются identity,
lifecycle, clarification и design status.

```text
.memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md:1-77
.memory-bank/epics/EP-005-companion-governance.md:15-46
```

Проверить только decomposition-relevant unresolved markers:

```bash
rg -n 'TBD|TODO|NEEDS CLARIFICATION|\?\?\?' \
  .memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md \
  .memory-bank/epics/EP-005-companion-governance.md \
  .memory-bank/prd.md \
  .memory-bank/requirements.md
```

### P0.3 Queue и Foundation gate — metadata прежде содержимого

Не читать `.memory-bank/tasks/index.json:1-169` линейно. Сначала выбрать только
FT-013 и Foundation gate:

```bash
jq '.tasks[] | select(.feature == "FT-013" or .id == "TASK-004-T2-FT-000-W0")' \
  .memory-bank/tasks/index.json
```

Для текущего Foundation решения достаточно:

```text
.memory-bank/foundation.md:22-38, 130-162
.memory-bank/tasks/TASK-004-T2-FT-000-W0.task.json:1-26, 97-101
```

Foundation verification logs, command history и evidence list из task card не
читать, если статус gate не противоречив.

### P0.4 Schema-first gate — до provisional task outline

После успешного feature/Foundation preflight, но до придумывания task
candidates, прочитать и разобрать целиком:

```text
.memory-bank/schemas/task.schema.json:1-193
.memory-bank/workflows/tier-policy.md:1-108
```

## P1 — product intent и governing behavior

Этот набор должен определить actors, authority, lifecycle, разрешённые workflow
effects и границу ответственности FT-013.

### P1.1 Основной product evidence

```text
.memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md:1-77
.memory-bank/epics/EP-005-companion-governance.md:15-46
.memory-bank/prd.md:60-62, 77-87, 104-126, 146-161, 230-265, 273-282
.memory-bank/requirements.md:23-27, 49-71, 85-110
.memory-bank/user-scenarios.md:42-65
.memory-bank/domains/core-domain.md:29-55, 57-79
.memory-bank/invariants.md:12-46
.memory-bank/states/lifecycle-map.md:25-26
```

### P1.2 Центральная lifecycle authority

`companion-governance.md` — центральный кандидат для FT-013, поэтому его нужно
читать целиком, а не только как набор decision slices.

```text
.memory-bank/states/companion-governance.md:1-148
```

После P1 должны быть сформулированы ответы на вопросы:

- кто может принять или отклонить CompanionProposal;
- как живут IssueStack, CompanionProposal и DecisionRecord;
- какие workflow effects разрешены и какие запрещены;
- владеет ли FT-013 фактическим model-backed Companion invocation;
- какие concerns требуют canonical `reuse|extend|create|not_applicable|block`.

Если ответ materially меняет authority, API, persistence, state, compatibility
или verification и не следует из P1, применить question gate до task slicing.

## P2 — canonical design по подтверждённым concerns

Сначала прочитать registry/folder routers. Затем открывать только кандидатов,
соответствующих pressure, подтверждённому в P1.

### P2.1 Discovery routers

```text
.memory-bank/contracts/index.md:11-58
.memory-bank/domains/index.md:11-39
.memory-bank/states/index.md:11-26
.memory-bank/testing/index.md:11-52
```

### P2.2 Governance authority и archived-Plant guard

Первые диапазоны — triage. Подтверждённый canonical candidate затем читать
целиком.

```text
.memory-bank/contracts/access/actor-context.md:25-114
.memory-bank/states/plants/plant-and-access-lifecycle.md:53-76, 107-134
.memory-bank/contracts/admin/boss-admin-http.md:133-144
```

Brownfield permissions читаются позже, в P4, после нормативного решения об
approver matrix.

### P2.3 Approved summary, Bus/UI projection и persistence

```text
.memory-bank/architecture/system-architecture.md:242-284, 336-365
.memory-bank/domains/runtime-data-model.md:21-34, 51-178
.memory-bank/contracts/agent-chat-bus.md:72-89, 101-197
.memory-bank/contracts/ui-feed.md:113-125, 148-221
.memory-bank/domains/agent-chat-ui-feed-storage.md:110-122, 147-189
.memory-bank/contracts/plant-feed-http.md:17-108
.memory-bank/contracts/message-envelope.md:19-40, 53-241
.memory-bank/contracts/timeline-event.md:17-35, 44-260
```

`message-envelope.md`, `timeline-event.md` и `plant-feed-http.md` остаются
условными: читать их полностью только если FT-013 меняет соответствующую
boundary, event registry или существующий Plant feed read path.

### P2.4 Закрытый catalog workflow effects

Эта группа нужна после того, как P1 подтвердил safe task/check/measurement/
follow-up effects. Plans и task cards FT-012 пока не читать.

```text
.memory-bank/states/task-follow-up-lifecycle.md:41-61, 83-115, 154-191
.memory-bank/domains/task-approval-outcomes.md:125-135, 174-232
.memory-bank/contracts/task-approval-http.md:93-120, 165-202
.memory-bank/contracts/task-follow-up-runtime.md:15-30, 48-251
.memory-bank/states/safety-action-lifecycle.md:15-94, 123-185
```

`safety-action-lifecycle.md` используется только для проверки separation:
DecisionRecord не предоставляет Safety Gate authority и не создаёт
`action_task`.

### P2.5 Explicit Companion invocation — условная группа

Читать только если P1 подтвердил, что текущая FT-013 реализует фактический
model-backed Companion run, а не только governance persistence/API/effects.

```text
.memory-bank/contracts/agent-roster-bootstrap.md:17-64, 171-184, 203-251
.memory-bank/contracts/agent-model-provider-profiles.md:15-34, 47-66, 102-169, 188-213
.memory-bank/contracts/agent-runtime-adapter.md:21-51, 74-383
.memory-bank/testing/agent-runtime.md:23-118, 132-154
.memory-bank/runbooks/agent-runtime-providers.md:14-98, 165-208
```

### P2.6 API и testing shape — после state/data/contracts

```text
.memory-bank/contracts/api-guidelines.md:16-28, 54-94, 119-137
.memory-bank/testing/strategy.md:25-133
.memory-bank/testing/agent-chat-ui-feed.md:22-45, 56-69
```

Feature-specific governance API/data/testing specs могут быть `create` только
после registry/folder discovery и проверки отсутствия подходящего subject-based
canonical path.

## P3 — dependencies и precedents

### P3.1 Dependency metadata — сначала только краткие поля

```bash
jq '{id,title,status,feature,tier,wave,depends_on}' \
  .memory-bank/tasks/TASK-037-T3-FT-011-W1.task.json \
  .memory-bank/tasks/TASK-038-T3-FT-011-W2.task.json \
  .memory-bank/tasks/TASK-039-T3-FT-012-W1.task.json \
  .memory-bank/tasks/TASK-040-T3-FT-012-W2.task.json
```

Полные task cards читать только если их exact success outcome или scope нужен
для обоснования `depends_on` FT-013.

### P3.2 FT-012 precedent — только при проектировании workflow effects

Canonical specs P2.4 имеют приоритет. Следующие артефакты используются позднее
для dependency/slicing precedent и не могут переопределять specs:

```text
.memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md:13-32, 36-86, 94-104
.protocols/FT-012/decision-log.md:7-65
.memory-bank/tasks/plans/IMPL-FT-012.md:8-35, 111-170
.memory-bank/tasks/TASK-039-T3-FT-012-W1.task.json:1-35, 94-184
.memory-bank/tasks/TASK-040-T3-FT-012-W2.task.json:1-26, 85-167
```

### P3.3 FT-008 precedent — только после canonical design

```text
.memory-bank/features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md:28-78, 86-149
.memory-bank/tasks/plans/IMPL-FT-008.md:17-76, 108-139
.protocols/FT-008/decision-log.md:3-31
```

`FT-008/plan.md` и behavior specs читать только если нужен конкретный precedent
для task slicing или behavior example.

## P4 — brownfield implementation evidence

Переходить к коду только после concern audit и выбора canonical actions. Код
нужен для grounded `touched_files`, runtime scopes, migration seams и реальных
verification commands, а не для определения product authority.

### P4.1 Сначала implementation seams

```text
backend/app/access_admin/permissions.py:31-95, 131-150, 271-333
backend/app/agent_chat/contracts.py:93-157, 160-210
backend/app/agent_chat/models.py:61-205
backend/app/agent_chat/authorization.py:13-50
backend/app/agent_chat/publication.py:18-80
backend/app/agent_chat/feed.py:19-65, 73-84
backend/app/access_admin/context_builders.py:52-105, 112-205, 260-283, 286-376
backend/app/plant_history/service.py:41-56
backend/app/api/feed.py:18-70
backend/app/api/__init__.py:1-17
backend/app/main.py:32-65
backend/migrations/versions/ft008_agent_chat_ui_feed.py:55-245
```

`plant_history/service.py` и FT-008 migration условны: читать только при
подтверждённой Timeline/Plant History integration или migration reuse.

### P4.2 Runtime implementation — только для explicit invocation

```text
backend/app/agent_runtime/roster.py:8-88
backend/app/agent_runtime/providers.py:19-59, 76-110, 116-213, 225-234
pyproject.toml:5-27, 33-39
```

### P4.3 Tests — после task slicing

```text
tests/backend/access_admin/test_ft001_actor_context.py:301-324, 553-580
tests/backend/access_admin/test_ft001_context_builder_authz.py:115-264, 334-384
tests/backend/agent_chat/test_ft008_guarded_publication.py:33-86, 89-247
tests/backend/agent_chat/test_ft008_migration_models.py:15-99
tests/backend/api/test_ft008_feed_routes.py:17-97
tests/backend/agent_runtime/test_ft007_roster_providers.py:53-200
```

## P5 — consistency, RTM и behavior examples

Читать после появления canonical specs и provisional task outline:

```text
.memory-bank/requirements.md:199-225
.memory-bank/prd.md:30-32, 41-43, 204-220, 302-304
.memory-bank/user-scenarios.md:12-18, 77-87
.memory-bank/glossary.md:124-172
.memory-bank/contracts/boundary-map.md:14-31
.memory-bank/states/lifecycle-map.md:15-26
.memory-bank/testing/task-follow-up.md:15-181
.memory-bank/testing/farm/plant-lifecycle-and-access.md:108-127
.memory-bank/testing/plant-history.md:47-59
```

Behavior specs прошлых features читать только если они materially уменьшают
неопределённость конкретного FT-013 scenario:

```text
.memory-bank/behavior-specs/FT-008-BHV-002-archive-reconciliation-guard.behavior.json:1-17
.memory-bank/behavior-specs/FT-008-BHV-003-literal-ui-typed-bus.behavior.json:1-18
.memory-bank/behavior-specs/FT-012-BHV-002-retry-conflict-archive.behavior.json:1-19
.memory-bank/behavior-specs/FT-012-BHV-003-real-agent-ordinary-task.behavior.json:1-20
```

## Не читать отдельным проходом

- Повторный decision-group line index: его ссылки уже распределены по P1–P5.
- Полный `.memory-bank/tasks/index.json`, если точечный `jq` даёт необходимые
  queue facts.
- Foundation evidence/log history после подтверждения непротиворечивого `done`.
- Полные FT-008/FT-011/FT-012 plans, protocols и task cards до появления
  конкретной dependency или precedent need.
- Plant History discovery additions без подтверждённого governance history
  effect.
- Provider/runbook/test context, если FT-013 не владеет model invocation.

## Resumable checkpoints

Чтобы compaction не заставлял перечитывать источники, фиксировать только
существенные результаты в предусмотренных workflow artifacts:

```text
.protocols/FT-013/plan.md
.protocols/FT-013/decision-log.md
.memory-bank/tasks/plans/IMPL-FT-013.md
```

До schema-first gate не записывать provisional task outline. После discovery
держать в protocol working state краткий audit:

```text
concern | canonical path candidate | sufficient | action
```

Не создавать дополнительный registry или альтернативную task model.
