# Potential Problems to Avoid

Статус: рабочий risk register.

Основано на `project_dossier.md`. Этот файл фиксирует архитектурные риски, которые важно учитывать при декомпозиции specs, tasks и vertical slices. Он не заменяет `.memory-bank/spec-index.md`, contracts, domains или states.

## P0 - критические риски

### PRBLM-001: Архитектура живет в dossier, а не в normative specs

**Проблема:** ключевые решения описаны в `project_dossier.md`, но `.memory-bank/product.md`, `.memory-bank/requirements.md`, `.memory-bank/invariants.md`, `.memory-bank/glossary.md` и spec areas пока в основном каркасные.

**Чем опасно:** код, схемы, tests и задачи начнут расходиться с архитектурным намерением. Агенты будут ссылаться на разные source of truth.

**Как избежать:**
- вынести минимальные specs: `agent_chat_bus.md`, `agno_runtime.md`, `agent_contracts.md`, `data_model.md`, `photo_protocol.md`, `dataset_lifecycle.md`, `human_review.md`;
- зарегистрировать их в `.memory-bank/spec-index.md`;
- не начинать T2/T3 implementation без linked specs.

### PRBLM-002: MVP превращается в farm-scale platform слишком рано

**Проблема:** даже MVP уже включает Agent Chat Bus, UI Feed, Agno boundary, PostgreSQL, timeline JSONL, photo manifests, Safety Gate, task/follow-up, dataset lifecycle и future learning loop.

**Чем опасно:** команда начнет строить платформу вместо одного работающего tomato daily check-in.

**Как избежать:**
- первый проверяемый slice: `user_photo -> mock Vision Agent -> MessageEnvelope -> UI spoiler split -> timeline.jsonl -> schema tests`;
- отложить real learning loop, server sync, InfluxDB, Agno Team и dataset registry;
- каждый новый слой добавлять только после end-to-end proof.

### PRBLM-003: Agent Chat Bus становится хрупким bottleneck

**Проблема:** весь агентный workflow зависит от правильного преобразования Agno output в `runtime_decision` и доменный `MessageEnvelope`.

**Чем опасно:** Agno events, workflow state или raw agent output начнут попадать в Bus как факты; агенты будут читать невалидный контекст.

**Как избежать:**
- один обязательный adapter boundary: `Agno output -> domain adapter -> BusEventEnvelope/MessageEnvelope`;
- запретить direct publish в Bus на уровне code path и tests;
- тестировать `silent`, `speak`, `clarify`, `escalate` как state machine, а не как prompt convention.

### PRBLM-004: Safety Gate реализован как prompt, а не deterministic policy

**Проблема:** Safety Gate может оказаться еще одним LLM-agent, который "советует", но не блокирует.

**Чем опасно:** Hydro Advisor или Companion Agent сможет сформулировать опасную рекомендацию без свежих pH/EC, safety check и human approval.

**Как избежать:**
- physical action проходит через deterministic policy gate;
- risky action без approval превращается только в `pending action proposal` или `pending approval task`;
- tests должны проверять запрет команд: pH/EC correction, dosing, pump/light changes.

### PRBLM-005: Неявный владелец Global Flow

**Проблема:** Global Flow описан как результат Bus, задач, safety rules и human decisions, но без явного runtime coordinator.

**Чем опасно:** будет непонятно, кто собирает финальный ответ пользователю, кто останавливает уточнения, кто выбирает следующий шаг.

**Как избежать:**
- сделать простой explicit workflow coordinator;
- Companion Agent формирует user-facing response, но не владеет safety или state truth;
- Global Flow decisions хранить как workflow/system events, а не как скрытое поведение агента.

## P1 - высокие риски

### PRBLM-006: Сложная модель source of truth для данных

**Проблема:** PostgreSQL, timeline.jsonl, photo JSON, future InfluxDB и Design Specs имеют разные authority roles.

**Чем опасно:** возможны расхождения между runtime state, audit log и export snapshot.

**Как избежать:**
- PostgreSQL владеет mutable state;
- timeline.jsonl только append-only audit/export;
- photo JSON только immutable snapshot/export artifact;
- каждый export должен иметь `snapshot_at`, `source_event_id`, source refs и schema version.

### PRBLM-007: Dataset governance внедряется раньше, чем появились outcomes

**Проблема:** lifecycle `raw/agent_labeled/confirmed/gold`, `curator_decision`, `evidence_refs`, split logic и `can_train_on` сложны для первого MVP.

**Чем опасно:** learning loop начнет тормозить базовый product flow.

**Как избежать:**
- в раннем MVP почти всегда `can_train_on=false`;
- разрешить только `raw` и `agent_labeled` до появления follow-up outcomes;
- curator confirmation добавлять после стабильного task/follow-up flow.

### PRBLM-008: UI Feed протекает в agent context

**Проблема:** `ui_spoiler_note` предназначен для пользователя, но его легко случайно передать агентам как контекст.

**Чем опасно:** агенты начнут использовать непотребляемые объяснения как facts, что ломает context hygiene и dataset quality.

**Как избежать:**
- context builder должен выбирать только `consumable_by_agents=true`;
- `visible_to_agents=false` должен быть enforced tests;
- `ui_spoiler_note_ref` может быть ссылкой, но не раскрытым содержимым для агентов.

### PRBLM-009: Agno boundary размывается

**Проблема:** Agno удобен как runtime SDK, но может незаметно стать доменным координатором, Bus или source of truth.

**Чем опасно:** проект потеряет собственные contracts и начнет зависеть от semantics SDK.

**Как избежать:**
- Agno Agent/Workflow только исполняет шаги;
- Agno Team `coordinate` запрещен для MVP;
- Agno memory/storage/workflow events не являются domain facts без adapter.

### PRBLM-010: LLM behavior тестируется как "умность", а не как boundary

**Проблема:** agent output нестабилен, поэтому тесты на точный текст будут хрупкими.

**Чем опасно:** tests начнут либо постоянно падать, либо ничего реально не защищать.

**Как избежать:**
- тестировать schemas, adapters, state transitions, policy gates и context filtering;
- agent text проверять только по структурным constraints: краткость, claim type, safety flags, source refs;
- для semantic behavior использовать fixtures и mock agents на раннем этапе.

## P2 - средние риски

### PRBLM-011: Потеря provenance

**Проблема:** `model_version`, `prompt_version`, `source_refs`, `confidence`, reviewer role и timestamps легко забыть в одном из paths.

**Чем опасно:** future evaluation/fine-tuning data станет непроверяемым.

**Как избежать:**
- сделать provenance обязательным в schemas;
- один helper/factory для agent reports;
- tests на отсутствие required provenance fields.

### PRBLM-012: Photo/file/DB consistency ломается

**Проблема:** фото хранится в filesystem, mutable statuses в PostgreSQL, JSON рядом с фото является snapshot.

**Чем опасно:** потерянные файлы, orphan JSON, неверный `plant_id`, дубли `photo_id`.

**Как избежать:**
- `photo_id` globally unique;
- `plant_id` mandatory в DB, timeline payload и photo manifest;
- sha256 обязательный для originals;
- consistency check: DB row -> file exists -> JSON exists -> sha256 matches.

### PRBLM-013: timeline.jsonl перестает быть append-only

**Проблема:** при простой файловой реализации можно случайно перезаписать timeline или писать события без порядка.

**Чем опасно:** audit trail станет недостоверным.

**Как избежать:**
- append-only writer abstraction;
- event id uniqueness check;
- tests запрещают mutation существующих events;
- при concurrency - single writer или DB-backed event table с export в JSONL.

### PRBLM-014: Sync/server statuses появляются до сервера

**Проблема:** MVP допускает только `local_only`, но roadmap уже содержит future statuses.

**Чем опасно:** UI или backend начнет показывать `server_verified` без реального server verification.

**Как избежать:**
- до server stage разрешен только `local_only`;
- upload prompt не меняет sync status;
- `server_verified` появляется только после реализации server-side sha256/idempotency verification.

## Минимальный safe implementation path

1. Normalize specs from `project_dossier.md` into `.memory-bank/contracts`, `.memory-bank/domains` and `.memory-bank/states`.
2. Implement schemas first: `BusEventEnvelope`, `MessageEnvelope`, `UIFeedEvent`, `photo_manifest`, `timeline_event`.
3. Build one vertical slice with mock agents.
4. Add deterministic Safety Gate before real Hydro Advisor recommendations.
5. Keep dataset training disabled until follow-up evidence exists.
6. Add Agno only behind the domain adapter boundary.
7. Expand to learning loop, sync and sensors only after the daily check-in flow is stable.
