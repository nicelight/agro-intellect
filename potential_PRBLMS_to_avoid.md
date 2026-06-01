# Potential Problems to Avoid

Статус: рабочий risk register; закрытые на текущем spec-layer риски удалены.

Основано на `project_dossier.md` и текущем spec-layer. Этот файл фиксирует оставшиеся архитектурные и execution risks, которые важно учитывать при декомпозиции tasks и vertical slices. Он не заменяет `.memory-bank/spec-index.md`, contracts, domains или states.

## P0 - критические риски

### PRBLM-005: Неявный владелец Global Flow

**Проблема:** Global Flow описан как результат Bus, задач, safety rules и human decisions, но без явного runtime coordinator.

**Чем опасно:** будет непонятно, кто собирает финальный ответ пользователю, кто останавливает уточнения, кто выбирает следующий шаг.

**Как избежать:**
- сделать простой explicit workflow coordinator;
- Companion Agent формирует user-facing response, но не владеет safety или state truth;
- Global Flow decisions хранить как workflow/system events, а не как скрытое поведение агента.

## P1 - высокие риски

### PRBLM-007: Dataset governance внедряется раньше, чем появились outcomes

**Проблема:** lifecycle `raw/agent_labeled/confirmed/gold`, `curator_decision`, `evidence_refs`, split logic и `can_train_on` сложны для первого MVP.

**Чем опасно:** learning loop начнет тормозить базовый product flow.

**Как избежать:**
- в раннем MVP почти всегда `can_train_on=false`;
- разрешить только `raw` и `agent_labeled` до появления follow-up outcomes;
- curator confirmation добавлять после стабильного task/follow-up flow.

## Минимальный safe implementation path

1. Convert the first safe slice into task decomposition: `user_photo -> mock Vision Agent -> MessageEnvelope -> UI spoiler split -> timeline.jsonl -> schema tests`.
2. Build one vertical slice with mock agents before expanding runtime integrations.
3. Keep dataset training disabled until follow-up evidence exists.
4. Add curator confirmation only after the task/follow-up flow is stable.
5. Make the workflow coordinator ownership explicit before implementing multi-agent Global Flow behavior.
6. Expand to learning loop, sync and sensors only after the daily check-in flow is stable.
