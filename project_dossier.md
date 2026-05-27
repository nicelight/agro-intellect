# Agro Intellect MVP: учебный полигон AI-first разработки агентных систем для агромониторинга

## Содержание файла и как его читать

Этот файл — исходное Досье проекта. Его задача: сохранить продуктовый замысел, архитектурные решения, ограничения MVP и правила, которые должны перейти в Brief, PRD и SDD Design Specs.

Содержание:

- `0. Суть проекта`;
- `1. Позиционирование проекта`;
- `2. Главная формула проекта`;
- `3. Основные цели`;
- `4. AI-first процесс разработки`;
- `5. Что не делать в первом MVP`;
- `6. Пользовательский продукт`;
- `7. Принцип однокомпетентных агентов`;
- `8. Агенты MVP`;
- `9. Глоссарий агентного взаимодействия`;
- `10. Протокол общения агентов`;
- `11. Отображение в чате`;
- `12. Почему не показывать настоящий сырой reasoning`;
- `13. Human-in-the-loop`;
- `14. Хранение данных: PostgreSQL + файловые фото + будущий InfluxDB`;
- `15. Формат JSON рядом с фото`;
- `16. Статусы достоверности полей`;
- `17. Типы фото`;
- `18. Dataset statuses`;
- `19. Как не испортить будущий датасет`;
- `20. Timeline и БД проекта`;
- `21. Ленивый upload / sync`;
- `22. Первый рабочий пользовательский flow`;
- `23. Первый рабочий demo-scope`;
- `24. Минимальный стек`;
- `25. Простая структура репозитория`;
- `26. Task Card: Agent Chat Bus и Competence Protocol`;
- `27. Canonical Memory Bank greenfield flow`;
- `28. MVP product slices`;
- `29. Flow разработки`;
- `30. Тестирование`;
- `31. Правила безопасности`;
- `32. Главные ошибки, которых нужно избежать`;
- `33. Практический roadmap / scope staging`;
- `34. Итоговая формула MVP`.

Не все разделы одинаково нужны на каждом этапе:

```text
/analysis
→ читать только суть, цели, текущую стадию и следующий шаг.

/brief
→ использовать продуктовую выжимку: 0–8, 13–14, 22–24, 28, 33.
→ не переносить большие JSON-примеры, task cards и подробные протоколы.

/write-prd
→ использовать problem, users, MVP scope, non-goals, constraints, user flow, success criteria.

/spec-init и /spec-design
→ использовать детальные разделы: Agno boundary, Agent Chat Bus, MessageEnvelope, UI Feed,
   photo/data model, dataset lifecycle, safety, tests, schemas.
```

Короткое правило:

```text
Brief/PRD берут из Досье смысл, scope и ограничения.
Design Specs берут из Досье точные контракты, схемы и инварианты.
```

Что не надо тащить в Brief без необходимости:

- большие JSON-примеры;
- подробные Bus/timeline examples;
- task card разделы;
- acceptance criteria и тестовые списки;
- внутренние детали UI Feed / MessageEnvelope, если они не нужны для продуктового решения.

Нормативность:

- до появления SDD Design Specs это Досье является главным исходным источником решений;
- после создания Design Specs нормативная истина проекта живёт в `.memory-bank/spec-index.md` и связанных specs;
- Досье остаётся upstream context и архитектурным основанием, но не заменяет Design Specs.

---

## 0. Суть проекта

Это не просто приложение для одного томата. Это учебный полигон, на котором я, как разработчик, архитектор и оркестратор, тренируюсь проектировать и вести **AI-first процесс разработки агентных систем**, чтобы набраться практического опыта и позже перейти к разработке коммерческой системы управления аграрной фермой.

Личный гидропонный томат используется как маленькая управляемая модель будущей фермы. На нём отрабатываются ключевые паттерны: агентные workflow, память, состояние объекта во времени, мультимодальный анализ, human-in-the-loop, safety gates, task orchestration, сбор данных, evaluation, dataset governance и контролируемый learning loop.

---

## 1. Позиционирование проекта

### 1.1. Что это за проект

Проект является не production-продуктом для внешних пользователей, а практическим учебным проектом.

Он выполняет две роли:

1. **Учебный архитектурный полигон** — среда, где я учусь проектировать агентные системы и управлять разработкой через AI-агентов.
2. **Личный рабочий инструмент** — помощник, которым я реально пользуюсь для наблюдения за своим растением.

Главная ценность проекта — не красивое приложение, а практический опыт проектирования, разработки, проверки и улучшения агентной системы.

---

### 1.2. Долгосрочная цель

Долгосрочная цель — подготовиться к разработке коммерческой агентной системы для аграрных ферм.

Будущая система должна уметь:

- мониторить ферму на протяжении всего цикла выращивания;
- собирать данные из разных источников: сенсоры, камеры, операторы, лабораторные анализы, метеоданные;
- анализировать состояние культур, зон, теплиц или полей;
- выявлять риски по питанию, поливу, климату, болезням, вредителям и урожайности;
- предлагать задачи операторам и агрономам;
- постепенно переходить от рекомендаций к контролируемому управлению;
- сохранять историю решений и результатов;
- формировать датасет для evaluation, fine-tuning и будущего улучшения моделей;
- улучшаться только на основании подтверждённых данных, а не непроверенных гипотез агента.

Текущий проект не должен сразу реализовывать фермерскую систему. Он должен дать архитектурный и инженерный опыт, который можно перенести на будущую farm-scale agentic system.

---

## 2. Главная формула проекта

```text
маленький личный гидропонный томат
→ контролируемый MVP
→ агентные workflow
→ AI-first разработка
→ дисциплина архитектуры и тестирования
→ понимание data feedback loop
→ подготовка к commercial farm management agentic system
```

Коротко:

```text
Tomato MVP is a miniature training ground for future farm-scale agentic systems.
```

---

## 3. Основные цели

### 3.1. Первичная цель

Получить практический опыт проектирования агентных систем:

- как разделять систему на агентов и workflow;
- как задавать агентам роли и границы ответственности;
- как строить общий агентный чат;
- как работать с conclusion/output между агентами;
- как не смешивать вывод агента и его размышления;
- как хранить состояние и историю объекта во времени;
- как работать с фото и неполными данными;
- как строить human-in-the-loop;
- как проектировать safety gates;
- как делать structured outputs вместо “болтовни”;
- как тестировать поведение агента;
- как управлять разработкой через AI-агентов;
- как собирать данные для будущего улучшения модели.

---

### 3.2. Вторичная цель

Создать личного AI-помощника для выращивания одного томата в гидропонике.

Он должен:

- вести ежедневный check-in;
- спрашивать, что было сделано;
- принимать фото растения;
- принимать ручные параметры pH/EC и другие наблюдения;
- анализировать состояние растения;
- запрашивать недостающие данные;
- давать осторожные рекомендации;
- создавать задачи;
- требовать подтверждение человека перед важными действиями;
- вести историю наблюдений, решений, задач и результатов;
- сохранять фото и метаданные так, чтобы позже это можно было использовать для learning loop.

---

## 4. AI-first процесс разработки

В проекте есть две разные агентные системы:

1. **Агентная система продукта** — агенты, которые помогают наблюдать за растением.
2. **Агентная система разработки** — AI-агенты, которые помогают проектировать, писать код, тестировать, ревьюить и документировать проект.

Моя роль:

```text
Human Architect
+ AI Team Orchestrator
+ Product Owner
+ Safety Owner
+ QA Gatekeeper
+ Domain Learner
```

AI-агенты могут реализовывать, ревьюить, тестировать и документировать, но не должны самовольно менять архитектуру, scope и safety-правила.

---

### 4.1. SDD и уровни истины

Проект ведётся SDD way.

```text
Design Specs = нормативная истина проекта.
Design Specs routing = .memory-bank/spec-index.md.
PostgreSQL/read model = runtime authority для текущего операционного состояния.
human_review / batch_review / expert_review = authority только для manual, batch и expert decisions.
curator_decision + evidence_refs = authority для evidence-based auto-confirmed dataset decisions.
InfluxDB = time-series authority для sensor readings после появления датчиков.
Agent Chat Bus / MessageEnvelope = транспорт и контракт сообщений.
timeline.jsonl = audit/export log.
Agno = SDK исполнения, не источник истины.
```

---

### 4.2. AGNO / Agno как SDK исполнения агентов

В продуктовой части проекта используется AGNO / Agno как SDK для реализации агентов, команд и workflow внутри монолита.

В этом проекте Agno Agent — это control loop вокруг модели с:

- tools;
- instructions;
- memory;
- knowledge;
- storage;
- HITL;
- guardrails.

Agno Teams можно использовать только как техническую группировку агентов, но не как доменный координатор.

По умолчанию MVP использует Agno Agent + Agno Workflow. Agno Team не обязателен.

В MVP запрещено использовать Agno Team в режиме `coordinate`. Team leader не должен сам делегировать, синтезировать и решать, что является рабочим выводом системы.

Разрешённые режимы Agno Team, если они действительно нужны:

- `route` — только как технический роутер к одному исполнителю;
- `broadcast` — только для независимых параллельных проверок;
- `tasks` — только с жёстким `max_iterations` и доменным адаптером на выходе.

Agno Workflows позволяют строить предсказуемые шаги с:

- conditions;
- routers;
- loops;
- parallel execution.

Важная граница: Agno не должен становиться самим Agent Chat Bus. Agno может исполнять агентов, команды и workflow, но правила “что считается фактом”, “что можно использовать для обучения”, “что попадает в общий чат” и “что видят другие агенты” должны жить в собственном доменном слое проекта.

Жёсткое правило:

```text
Agno invocation != Agent Chat Bus publication
```

Agno Workflow может вызвать агента, команду, функцию или вложенный workflow. Это только возможность выполнить шаг, а не разрешение публиковать факт.

После каждого вызова агент обязан вернуть runtime decision:

```text
speak | silent | clarify | escalate
```

- `silent` — не публиковать Bus event / `MessageEnvelope`; audit record обязателен; UI Feed event опционален и не consumable для агентов;
- `speak` — опубликовать краткий рабочий вывод через `MessageEnvelope`;
- `clarify` — опубликовать короткий запрос недостающих данных;
- `escalate` — опубликовать Team Signal или Safety Block.

Agno Workflow events, Team synthesis, step output и внутренний reasoning не являются фактами системы, пока не прошли доменный адаптер и не стали `MessageEnvelope`.

---

## 5. Что не делать в первом MVP

Не делать сразу:

- production-систему;
- много пользователей;
- сложную схему БД;
- хранение фото и связанных JSON-манифестов внутри БД;
- автополив;
- автоматическое управление насосами;
- автоматическое изменение pH/EC;
- автодозирование удобрений;
- сложный RAG;
- экспертную панель;
- полноценный dataset registry;
- сложную мультиагентную иерархию;
- использовать Agno как замену доменному Agent Chat Bus;
- использовать Agno Team в режиме `coordinate`;
- делать InfluxDB runtime-зависимостью, если датчики ещё не готовы; контракты `sensor_window` закладываются заранее;
- реальное дообучение моделей без evaluation, evidence_refs и достаточного confirmation/review gate.

Первый MVP должен быть простым:

```text
чат + ежедневный ритуал + фото + анализ + рекомендации + задачи + human approval + история + БД проекта + файловые JSON-метаданные для фото
```

---

## 6. Пользовательский продукт

Технически лучше начать так:

```text
Web App → PWA → мобильная обёртка через Capacitor
```

Минимальный интерфейс:

- чат;
- загрузка фото;
- карточка растения;
- дневной check-in;
- ручной ввод pH/EC;
- список задач;
- история дней;
- история фото;
- рекомендации;
- подтверждение действий человеком;
- спойлеры с обучающими объяснениями агентов.

---

## 7. Принцип однокомпетентных агентов

Каждый агент системы отвечает только за одну область компетенции.

Агент не должен:

- самовольно расширять свою роль;
- выполнять работу другого агента;
- отдавать команды другим агентам напрямую;
- использовать чужие spoilered-размышления как источник фактов;
- публиковать длинные ответы без запроса;
- засорять общий чат, если его вклад не меняет Global Flow.

Агент должен:

- читать общий чат;
- использовать только consumable conclusion/output других агентов;
- самостоятельно решать, нужно ли реагировать;
- после каждого вызова возвращать `speak | silent | clarify | escalate`;
- кратко публиковать свой conclusion/output;
- просить уточнение у другого агента, если информации недостаточно;
- писать крупное сообщение только при важном Team Signal или Safety Block.

В реализации агент может быть Agno Agent, но его компетенция и права определяются не возможностями SDK, а доменными контрактами проекта: Competence Boundary, Agent Chat Bus, Safety Gate и правилами dataset governance.

Вызов агента не означает публикацию. Если агент вернул `silent`, в Agent Chat Bus не попадает ничего.

---

## 8. Агенты MVP

### 8.1. Companion Agent

Компетенция: пользовательский диалог и поддержание Flow.

Задачи:

- вести диалог с пользователем;
- поддерживать ежедневный ритм;
- объяснять выводы других агентов простым языком;
- просить недостающие данные у пользователя;
- не перегружать пользователя техническими деталями;
- превращать анализ в понятное действие.

Не должен:

- самостоятельно ставить диагноз;
- подменять Safety Gate;
- придумывать агрономические выводы вместо профильных агентов.

---

### 8.2. Vision Observation Agent

Компетенция: наблюдение по фото.

Задачи:

- анализировать качество фото;
- описывать, что видно и чего не видно;
- замечать визуальные симптомы: пятна, пожелтение, увядание, повреждения, деформации;
- отличать наблюдение от диагноза;
- запрашивать дополнительные фото, если данных мало;
- формировать краткий visual conclusion.

Не должен:

- назначать коррекцию pH/EC;
- делать финальный диагноз;
- создавать задачи на изменение раствора.

---

### 8.3. Plant State Agent

Компетенция: состояние растения во времени.

Задачи:

- обновлять подтверждённые данные и вероятностные/неполные поля состояния в рамках их статуса;
- различать `confirmed`, `probable`, `unknown`, `conflict`;
- сравнивать текущие наблюдения с прошлой историей;
- фиксировать изменения, тренды и противоречия.

Plant State Agent может обновлять поля со статусами `probable`, `unknown` или `conflict` на основании agent-labeled выводов и текущих наблюдений. Он не может повышать состояние до `confirmed` без human review или follow-up evidence.

Не должен:

- использовать неподтверждённую гипотезу как факт;
- помечать agent-labeled данные как confirmed.

---

### 8.4. Hydroponics Advisor Agent

Компетенция: гидропонные параметры и агрономическая логика.

Задачи:

- анализировать pH, EC, температуру, влажность, свет и раствор;
- сопоставлять параметры с состоянием растения;
- находить риски;
- давать осторожные рекомендации;
- запрашивать недостающие измерения;
- не давать жёсткую рекомендацию без критически важных данных.

Не должен:

- создавать задачи вместо Task Agent;
- обходить Safety Gate;
- рекомендовать дозировки как обязательное действие без approval.

---

### 8.5. Task & Follow-up Agent

Компетенция: задачи и контроль результата.

Задачи:

- создавать `check_task` / measurement task без approval;
- превращать approved action proposals в `action_task`;
- создавать follow-up через 1–3 дня;
- отслеживать статус задач;
- записывать outcome: улучшилось, ухудшилось, без изменений, данных нет.

Не должен:

- сам решать, что агрономическая рекомендация безопасна;
- менять состояние растения без подтверждённого события.

---

### 8.6. Safety Gate Agent

Компетенция: безопасность и human approval.

Задачи:

- классифицировать рискованные действия;
- блокировать физические action-команды без свежих данных, safety check и approval;
- переводить рискованные рекомендации в pending approval flow;
- различать рекомендацию, проверку и команду;
- требовать подтверждение человека для действий с pH, EC, раствором, насосами, светом и дозировками.

Не должен:

- подменять агрономический анализ;
- давать альтернативный совет вместо проверки безопасности.

---

### 8.7. Dataset Governance Agent

Компетенция: правила, gates и легальность статусов будущего learning loop.

Задачи:

- следить за `dataset.status`: `raw`, `agent_labeled`, `needs_review`, `confirmed`, `rejected`, `gold`, `excluded`;
- проверять допустимость `dataset.split`: `train`, `eval`, `holdout`;
- фиксировать `dataset.corrected` и `dataset.follow_up_seen` отдельно от `dataset.status`;
- запрещать `can_train_on=true` для данных без достаточного confirmation/review gate;
- запрещать fine-tuning на `eval` и `holdout`;
- фиксировать источник label: agent, user, expert, follow_up;
- хранить model_version, prompt_version, reviewer_role.

Не должен:

- считать вывод агента ground truth;
- допускать обучение на непроверенных гипотезах.

### 8.8. Training Data Curator Agent

Компетенция: delayed dataset selection для будущего дообучения и evaluation.

Роль в Agent Chat Bus минимальная: почти всегда `silent`. Curator читает прошлые фото, JSON snapshots, outcomes, sensor windows, follow-up и согласованные наблюдения, ведёт внутренние curator notes и принимает delayed dataset decisions спустя время.

Задачи:

- выбирать данные для `train`, `eval` и `holdout` после накопления evidence;
- выставлять `curator_decision`: `selected`, `deferred`, `rejected`;
- фиксировать `curator_notes_ref`, `evidence_refs` и `dataset.confirmation_source`;
- auto-confirm items, если evidence сильный: follow-up, outcome, sensor trend, повторные фото, согласованные наблюдения;
- редко задавать вопрос в общий чат только при острой необходимости;
- эскалировать на human, batch, sampling или expert review при conflict, low confidence, rare valuable example, gold candidate или high-impact label.

Не должен:

- обучаться или разрешать обучение на голых гипотезах агента;
- требовать ручного подтверждения человеком для сотен обычных фото;
- повышать пример до `gold` без human/expert review или batch review approval.

---

## 9. Глоссарий агентного взаимодействия

### 9.1. Single-Competence Agent / Однокомпетентный агент

Агент, который отвечает только за одну область компетенции и не выходит за её пределы.

---

### 9.2. Competence Boundary / Граница компетенции

Явное ограничение, что агенту разрешено и запрещено делать.

Пример:

```text
Vision Agent может сказать: “на фото видны светлые края листьев”.
Vision Agent не может сказать: “измени EC до 2.1”.
```

---

### 9.3. Agent Chat Bus / Общий агентный чат

Единый рабочий доменный поток, который формирует рабочий контекст агентной системы.

Другие агенты читают только этот поток и самостоятельно решают, нужно ли им реагировать.

Важно: агенты не управляют друг другом напрямую. Они взаимодействуют через общий чат и структурированные события.

Agent Chat Bus — доменная часть системы, а не внутренний механизм Agno. Даже если агент, команда или workflow реализованы через Agno, публикация в общий чат проходит через собственный контракт проекта.

В Agent Chat Bus попадает не “только агентское”, а только consumable для агентной системы.

Примеры допустимых событий:

- пользователь загрузил фото;
- пользователь дал pH/EC;
- человек подтвердил или отклонил действие;
- агент опубликовал conclusion;
- Safety Gate заблокировал действие;
- Task Agent создал задачу.

Runtime decision агента `silent` не создаёт `MessageEnvelope` и не публикуется в Agent Chat Bus. Audit record обязателен; UI Feed event опционален и не consumable для агентов.

Рабочие события в Bus имеют общую внешнюю оболочку:

```text
BusEventEnvelope
event_id
event_type
created_at
source_type
source_id
topic
payload
consumable_by_agents
audit_log
```

Смысл полей:

- `BusEventEnvelope` — единая оболочка события Agent Chat Bus;
- `event_id` — уникальный id события;
- `event_type` — тип события: user_photo, human_confirmation, agent_conclusion, safety_block и т.д.;
- `created_at` — время создания;
- `source_type` — источник события: user, agent, system, task, sync;
- `source_id` — id источника;
- `topic` — область или поток обсуждения;
- `payload` — данные события;
- `consumable_by_agents` — можно ли использовать событие как рабочий контекст агентной системы;
- `audit_log` — технический след исполнения, проверок и решений.

Если событие публикует агент, внутри `payload` лежит `MessageEnvelope`:

```text
MessageEnvelope
agent_id
claim_type
confidence
requires_human_approval
can_train_on
source_refs
consumable_output
ui_spoiler_note_ref
```

Смысл полей `MessageEnvelope`:

- `agent_id` — какой агент опубликовал рабочий вывод;
- `claim_type` — тип утверждения: observation, hypothesis, recommendation, safety_block, task_request, clarification_request, quoted_detail_reply;
- `confidence` — уровень уверенности;
- `requires_human_approval` — нужно ли подтверждение человека;
- `can_train_on` — можно ли использовать сообщение как обучающий сигнал;
- `source_refs` — ссылки на фото, JSON, timeline event, sensor reading или human review;
- `consumable_output` — краткий вывод, который могут читать другие агенты;
- `ui_spoiler_note_ref` — опциональная ссылка на UI Feed `ui_spoiler_note`; это контролируемое пояснение для человека, не reasoning модели и не рабочий контекст для агентов;

В Agent Chat Bus попадает только то, что должно влиять на работу агентной системы:

```text
user_photo         → входное событие для агентов
human_confirmation → подтверждение/запрет действия
task_created       → изменение рабочего состояния
agent_conclusion  → мягкое влияние
agent_team_signal → сильное влияние
safety_block      → жёсткое влияние
```

Silent-решения и спойлеры для пользователя не являются частью Agent Chat Bus.

Для `event_type=user_photo` обязательный payload:

```text
plant_id
photo_id
photo_type
```

`payload.plant_id` обязателен. Нельзя восстанавливать привязку фото к растению только из `topic`. `topic` остаётся routing/audit label.

Agno storage, memory, workflow state и workflow events не являются authority для доменных данных. Design Specs задают нормативные контракты проекта. PostgreSQL/read model — runtime authority для текущего операционного состояния. `timeline.jsonl` — append-only audit/event export. `plant.json` и photo/JSON-манифесты — файловый dataset snapshot/manifest, не primary state.

---

### 9.3.1. UI Feed / Пользовательский поток отображения

Отдельный поток для красивого отображения работы агентов в интерфейсе.

UI Feed может показывать:

```text
agent_silent_decision
ui_spoiler_note
agent_ui_status
system_ui_status
debug_lite_card
```

Правило KISS:

```text
Agent Chat Bus = рабочий доменный поток для агентной системы.
UI Feed = представление.
```

Агенты не получают UI Feed в свой input.

---

### 9.4. Conclusion / Agent Output

Краткий структурированный вывод агента, который можно использовать другим агентам.

Это основной межагентный артефакт.

Уровень влияния: **мягкий**. Conclusion добавляет факт, наблюдение, гипотезу или недостающие данные, но сам по себе не останавливает Global Flow.

Пример:

```json
{
  "event_id": "evt_002",
  "event_type": "agent_conclusion",
  "created_at": "2026-05-24T12:31:00+05:00",
  "source_type": "agent",
  "source_id": "vision_observation_agent",
  "topic": "image_observation",
  "payload": {
    "message_envelope": {
      "agent_id": "vision_observation_agent",
      "claim_type": "hypothesis",
      "confidence": "low",
      "requires_human_approval": false,
      "can_train_on": false,
      "source_refs": ["photo:2026-05-24_12-30-00_leaf_001"],
      "consumable_output": "На фото видно слабое пожелтение нижнего листа. Данных для диагноза недостаточно. Нужны pH, EC и lower_leaf_closeup.",
      "ui_spoiler_note_ref": "ui:vision_observation_agent:2026-05-24_12-31-05"
    }
  },
  "consumable_by_agents": true,
  "audit_log": {
    "runtime_decision": "speak",
    "adapter": "agno_output_to_message_envelope"
  }
}
```

---

### 9.5. UI-only Explanation Note / Непотребляемое UI-пояснение

Пояснение под спойлером, которое видно пользователю как обучающий материал, но не используется другими агентами как контекст для принятия решений.

Это не сырой chain-of-thought модели и не настоящий reasoning. Это специально сгенерированное безопасное объяснение для человека.

Правило:

```text
Спойлеры “поразмыслил” можно читать человеку.
Другие агенты не получают их во входные данные.
Спойлеры хранятся и отображаются через UI Feed, а не через Agent Chat Bus.
```

---

### 9.6. UI Spoiler Note / Спойлер “поразмыслил”

UI-блок для объяснения логики агента пользователю.

Он нужен для обучения пользователя архитектуре агентного мышления, но не является источником истины для системы и не участвует в межагентном общении.

Canonical форма UI-only события:

```text
UIFeedEvent
event_id
event_type
stream
created_at
source_agent_id
payload
visible_to_agents
consumable_by_agents
```

`ui_spoiler_note_ref` всегда ссылается на `UIFeedEvent.event_id`.

Photo JSON и `timeline.jsonl` могут хранить только snapshot/export copy этого события. Они не являются canonical source для UI Feed.

Silent-агент может не публиковать ничего в Agent Chat Bus, но всё равно показать пользователю короткий UI Spoiler Note.

---

### 9.7. Concise-by-Default Protocol / Краткость по умолчанию

Правило, по которому агент публикует короткие ответы и не раскрывает подробности без необходимости.

Формула:

```text
По умолчанию: краткий conclusion/output.
Если не хватает данных: короткий clarification request.
Если нужен detail: другой агент цитирует сообщение и запрашивает уточнение.
```

---

### 9.8. Clarification Request / Запрос уточнения

Короткий вопрос от одного агента к другому, когда текущего conclusion/output недостаточно.

Это не direct call и не команда другому агенту. `agent_clarification_request` публикуется как Bus event с `target_agent_id`; получатель сам решает, реагировать ли, и возвращает свой обычный runtime decision.

Пример:

```text
agent_clarification_request(target_agent_id="vision_observation_agent"):
Пожелтение видно на нижних листьях или только на верхнем ярусе?
```

---

### 9.9. Quoted Detail Reply / Ответ на цитирование

Чуть более подробный ответ агента, если к нему обратились с цитированием его сообщения.

Он должен быть подробнее обычного conclusion, но короче UI Spoiler Note.

Правило:

```text
Обычный ответ: 1–3 строки.
Ответ на цитирование: 3–7 строк.
UI Spoiler Note: расширенное объяснение только для человека.
```

---

### 9.10. Team Signal / Сигнал команде

Сообщение агента, которое он публикует только если считает, что его информация важна для всей команды и может изменить Global Flow.

Уровень влияния: **сильный**. Team Signal направляет обсуждение, меняет приоритеты, требует внимания других агентов или Companion Agent.

Team Signal должен быть редким.

Примеры:

- обнаружен риск опасной рекомендации;
- не хватает критически важных данных;
- вывод другого агента противоречит фактам;
- действие нельзя выполнять без human approval.

---

### 9.10.1. Safety Block / Жёсткая блокировка

Структурированное событие, которое запрещает немедленное опасное действие или команду без свежих данных, safety check и human approval.

Уровень влияния: **жёсткий**. Safety Block останавливает соответствующий action flow, пока не выполнен весь явно заданный набор условий разблокировки.

`unlock_conditions` — обязательный AND-набор, а не список альтернатив. Для physical action минимальный набор: fresh data + safety check + human approval.

Разрешено формировать pending action proposal / pending approval task. Разрешено выполнять approved `action_task` после подтверждения человека.

Примеры:

- нельзя советовать коррекцию pH без актуального pH;
- нельзя менять EC без актуального EC и объёма бака;
- нельзя включать насос/дозатор без human approval;
- нельзя считать автодиагноз подтверждённым фактом.

Safety Block должен быть rule-first, максимально простым и проверяемым тестами.

---

### 9.11. Large-Font Team Message / Крупный ответ

Визуально выделенное сообщение в чате.

Агент использует его только для важного Team Signal или Safety Block, которые помогают направить или остановить Global Flow.

`large_team_message` относится к Bus/agent protocol и разрешён только для Team Signal или Safety Block. Обычный крупный основной ответ пользователю — это `primary_user_response` уровня UI presentation, а не рабочее сообщение Agent Chat Bus.

Правило:

```text
По умолчанию агент молчит или пишет краткий conclusion.
Крупный ответ разрешён только при высокой важности для команды.
```

---

### 9.12. Silent Listener Mode / Тихий режим

Режим, в котором агент читает Agent Chat Bus, но не публикует рабочее сообщение, если его компетенция сейчас не нужна или его вклад не меняет Global Flow.

Это снижает шум и не превращает чат в поток лишних сообщений.

Silent не значит invisible: агент может показать пользователю короткий `ui_spoiler_note` в UI Feed, но это не влияет на других агентов.

---

### 9.13. Global Flow / Глобальный Flow

Общее направление работы системы: что сейчас важно, какие данные нужны, какие риски есть, какое следующее действие наиболее полезно.

Global Flow не принадлежит одному агенту. Он формируется через общий чат, задачи, safety rules и решения человека.

---

### 9.14. Context Hygiene / Гигиена контекста

Правило, по которому агенты получают только нужный для работы контекст.

Основной принцип:

```text
conclusion/output можно использовать.
UI Feed / ui_spoiler_note нельзя использовать.
сырой reasoning модели не хранится как рабочий контекст и не передаётся.
```

---

## 10. Протокол общения агентов

### 10.1. Главные правила

1. Каждый агент отвечает за одну область компетенции.
2. В Agent Chat Bus попадают только события, consumable для агентной системы.
3. Другие агенты самостоятельно решают, нужно ли реагировать на опубликованную информацию.
4. Агенты используют только Agent Chat Bus и consumable-поля событий.
5. UI Spoiler Note не должен попадать в контекст других агентов.
6. Ответы агентов должны быть краткими по умолчанию.
7. Если агенту не хватает информации, он спрашивает другого агента о более подробном ответе.
8. Если к агенту обратились с цитированием сообщения, он отвечает чуть подробнее, но всё равно короче UI Spoiler Note.
9. Крупный ответ разрешён только для важного Team Signal или Safety Block.
10. Если вклад агента не меняет Global Flow, агент остаётся в Silent Listener Mode.
11. Silent-решение может отображаться пользователю в UI Feed, но не публикуется в Agent Chat Bus.
12. Safety Block имеет приоритет над conclusion и Team Signal.

---

### 10.2. Размеры ответов

```text
Silent Listener Mode:
- нет сообщения в Agent Chat Bus
- опционально короткий UI Spoiler Note для пользователя

Обычный conclusion/output:
- 1–3 строки
- только суть
- без длинного объяснения

Clarification Request:
- 1 короткий вопрос
- `target_agent_id` указывает предполагаемого получателя Bus event
- не является command/direct call; получатель решает сам через runtime decision

Quoted Detail Reply:
- 3–7 строк
- подробнее обычного conclusion
- без длинного рассуждения

UI Spoiler Note:
- расширенное объяснение для человека
- хранится/отображается в UI Feed
- не используется другими агентами
- consumable_by_agents=false
- visible_to_agents=false

Large-Font Team Message:
- 1–4 строки
- только при важном Team Signal или Safety Block
```

---

### 10.3. Типы событий в Agent Chat Bus

```text
user_message
user_photo
agent_conclusion
agent_clarification_request
agent_quoted_detail_reply
agent_team_signal
safety_block
task_created
human_confirmation
system_event
sync_event
```

UI-only события сюда не попадают.

---

### 10.3.1. Типы событий в UI Feed

```text
agent_silent_decision
ui_spoiler_note
agent_ui_status
system_ui_status
debug_lite_card
```

Эти события видит пользователь, но не читают агенты.

---

### 10.3.2. Уровни влияния рабочих событий

```text
agent_conclusion
→ мягкое влияние
→ добавляет наблюдение, гипотезу, missing data или обычный вывод
→ не останавливает flow

agent_team_signal
→ сильное влияние
→ меняет приоритеты, обращает внимание команды, направляет synthesis
→ должен быть редким

safety_block
→ жёсткое влияние
→ запрещает действие/рекомендацию до выполнения условий безопасности
→ имеет приоритет над другими событиями
```

---

### 10.4. Пример сообщения агента

```json
{
  "event_id": "evt_002",
  "event_type": "agent_conclusion",
  "created_at": "2026-05-24T12:31:00+05:00",
  "source_type": "agent",
  "source_id": "vision_observation_agent",
  "topic": "image_observation",
  "payload": {
    "message_envelope": {
      "agent_id": "vision_observation_agent",
      "claim_type": "hypothesis",
      "confidence": "low",
      "requires_human_approval": false,
      "can_train_on": false,
      "source_refs": ["photo:2026-05-24_12-30-00_leaf_001"],
      "consumable_output": "Фото пригодно. Видно слабое пожелтение нижнего листа. Диагноз по фото не подтверждён. Нужны pH, EC и lower_leaf_closeup.",
      "ui_spoiler_note_ref": "ui:vision_observation_agent:2026-05-24_12-31-05"
    }
  },
  "consumable_by_agents": true,
  "audit_log": {
    "runtime_decision": "speak",
    "adapter": "agno_output_to_message_envelope"
  }
}
```

---

### 10.5. Пример UI Spoiler Note

```json
{
  "event_id": "ui:vision_observation_agent:2026-05-24_12-31-05",
  "event_type": "ui_spoiler_note",
  "stream": "ui_feed",
  "created_at": "2026-05-24T12:31:05+05:00",
  "source_agent_id": "vision_observation_agent",
  "payload": {
    "source_message_ref": "evt_002",
    "spoiler_title": "поразмыслил",
    "text": "Сначала я сравнил общий тон листьев и края нижнего листа. Симптом слабый и может быть связан с разными причинами. Без pH/EC нельзя отличить дефицит от проблемы усвоения, поэтому вывод остаётся гипотезой."
  },
  "consumable_by_agents": false,
  "visible_to_agents": false
}
```

---

### 10.6. Пример уточнения между агентами

```text
[agent_clarification_request, source_agent_id="hydroponics_advisor_agent", target_agent_id="vision_observation_agent"]
Пожелтение видно именно на нижнем листе или на нескольких ярусах?

[Vision Observation Agent, quoted detail reply]
По текущему фото уверенно виден только один нижний лист. Пожелтение слабое, локальное, по краю. Несколько ярусов оценить нельзя: общий кадр не показывает нижнюю часть достаточно хорошо. Нужен lower_leaf_closeup.
```

---

### 10.7. Пример крупного Team Signal

```text
[Safety Gate Agent, large]
Нельзя рекомендовать коррекцию раствора: нет актуальных pH/EC. Сначала нужно запросить измерения и human approval.
```

Рабочее событие:

```json
{
  "event_id": "evt_safety_gate_001",
  "event_type": "agent_team_signal",
  "created_at": "2026-05-24T12:31:00+05:00",
  "source_type": "agent",
  "source_id": "safety_gate_agent",
  "topic": "safety_gate",
  "payload": {
    "message_envelope": {
      "agent_id": "safety_gate_agent",
      "claim_type": "task_request",
      "confidence": "high",
      "requires_human_approval": true,
      "can_train_on": false,
      "source_refs": ["state:latest_measurements", "measurement:2026-05-24T12-30-00"],
      "consumable_output": "Нет актуальных pH/EC. Коррекцию раствора сейчас обсуждать нельзя; сначала нужны свежие измерения и human approval.",
      "ui_spoiler_note_ref": "ui:safety_gate_agent:latest_measurements_block"
    }
  },
  "consumable_by_agents": true,
  "audit_log": {
    "runtime_decision": "escalate"
  }
}
```

---

### 10.8. Пример Safety Block

```json
{
  "event_id": "evt_safety_block_001",
  "event_type": "safety_block",
  "created_at": "2026-05-24T12:31:00+05:00",
  "source_type": "agent",
  "source_id": "safety_gate_agent",
  "topic": "safety_gate",
  "payload": {
    "message_envelope": {
      "agent_id": "safety_gate_agent",
      "claim_type": "safety_block",
      "confidence": "high",
      "requires_human_approval": true,
      "can_train_on": false,
      "source_refs": ["state:latest_measurements", "measurement:2026-05-24T12-30-00", "policy:safety_gate"],
      "consumable_output": "Коррекцию раствора нельзя рекомендовать без свежих pH/EC, пройденного safety check и подтверждения человека. Условия разблокировки: fresh_pH, fresh_EC, safety_check_passed, human_approval.",
      "ui_spoiler_note_ref": "ui:safety_gate_agent:solution_correction_block"
    }
  },
  "consumable_by_agents": true,
  "audit_log": {
    "runtime_decision": "escalate",
    "blocked_action": "recommend_solution_correction",
    "unlock_conditions": ["fresh_pH", "fresh_EC", "safety_check_passed", "human_approval"]
  }
}
```

---

## 11. Отображение в чате

Основной пользовательский ответ — `primary_user_response` уровня UI presentation. Он может быть визуально заметным для пользователя, но не является рабочим сообщением Agent Chat Bus и не использует `large_team_message`.

Служебные conclusion/output агентов — мелким текстом.

Расширенные объяснения и silent-пояснения — под спойлером **“поразмыслил”**.

Важно: это не настоящий сырой chain-of-thought модели, а специально сгенерированный `ui_spoiler_note` — контролируемое объяснение анализа, сомнений, догадок и ограничений.

Архитектурная граница:

```text
Agent Chat Bus = рабочий доменный поток для агентной системы.
UI Feed = представление для пользователя.
```

UI Feed не используется при сборке input для других агентов.

Пример:

```text
[Vision Observation Agent, small]
Фото пригодно. Видны верхние листья. Нижние листья почти не видны. Диагноз не подтверждён.

[спойлер: поразмыслил]
Сначала я смотрю на общий тон листьев: сильного увядания не видно, но края некоторых листьев выглядят чуть светлее. Это может быть ранний дефицит питания, но такой симптом сам по себе слабый. Я не вижу нижние листья, а именно по ним часто лучше заметны ранние проблемы. Ещё меня ограничивает отсутствие pH и EC.

[Hydroponics Advisor Agent, small]
Без pH/EC нельзя советовать коррекцию раствора. Нужны измерения.

[Companion Agent, large]
Пока не меняй раствор. Сделай фото нижнего листа крупно и напиши pH/EC, если измерял.
```

---

## 12. Почему не показывать настоящий сырой reasoning

Сырой reasoning модели не должен быть частью продукта.

Причины:

- его трудно контролировать;
- он может быть шумным;
- может содержать нестабильные промежуточные догадки;
- может путать пользователя;
- может раскрывать внутренние инструкции или технический мусор;
- не годится как надёжный журнал решения.

Вместо этого агент должен возвращать:

```text
краткий conclusion/output
+ structured fields
+ controlled ui_spoiler_note для обучения человека
```

---

## 13. Human-in-the-loop

В MVP человек подтверждает все важные действия.

Агент не должен сам:

- менять pH;
- менять EC;
- менять раствор;
- включать/выключать насосы;
- менять световой режим;
- назначать дозировку удобрений как обязательное действие;
- записывать автодиагноз как подтверждённый факт.

Безопасный формат:

```text
Похоже на ранний дисбаланс питания, но уверенность низкая.
Перед коррекцией раствора проверь pH и EC.
Сделай ещё фото нижних листьев при нейтральном свете.
```

Опасный формат:

```text
Добавь 20 мл удобрения и доведи EC до 2.1.
```

Опасный формат должен быть заблокирован Safety Gate или переведён в pending action proposal / pending approval task.

---

## 14. Хранение данных: PostgreSQL + файловые фото + будущий InfluxDB

PostgreSQL должен быть частью проекта уже в MVP. Он является runtime authority для текущего операционного состояния. Не нужно делать сложную схему: достаточно минимальных таблиц для текущего состояния, ссылок на события и статусов.

В БД можно хранить:

- растения и их текущий профиль;
- photo catalog: `photo_id`, `plant_id`, `captured_at`, `photo_type`, путь к файлу, `sha256`;
- задачи;
- human approval;
- статусы review;
- dataset status и `can_train_on`;
- ссылки на события timeline;
- технические статусы sync;
- future `sensor_window_ref` для связи фото с InfluxDB.

Фото не храним как binary/blob внутри PostgreSQL или InfluxDB. Оригиналы лежат в файловом хранилище сейчас, позже могут переехать в object storage.

PostgreSQL владеет mutable статусами фото, review, dataset и sync. JSON рядом с фото — export/training artifact, а не authority для этих статусов.

Инварианты привязки фото к растению:

```text
каждое фото обязано иметь plant_id
photo_catalog.photo_id глобально уникален
photo_catalog.plant_id обязателен и является canonical runtime binding
photo_manifest.plant_id обязателен и является immutable export snapshot
timeline/user_photo.payload.plant_id обязателен и является audit/event binding
file path plant folder — дополнительная проверка, но не source of truth
```

InfluxDB появится вместе с реальными датчиками и будет хранить только sensor readings: pH, EC, температура, влажность, свет и другие временные ряды.

Ключ для будущего training export:

```text
photo_id + plant_id + captured_at
```

Training export собирает единый `photo + JSON` из PostgreSQL и InfluxDB:

```text
photo file
+ PostgreSQL photo/review/dataset/sync snapshot
+ InfluxDB sensor_window вокруг captured_at
→ immutable JSON рядом с фото
```

Пример:

```text
data/
  plants/
    tomato_001/
      plant.json
      timeline.jsonl
      photos/
        originals/
          2026-05-24_12-30-00_leaf_001.jpg
          2026-05-24_12-30-00_leaf_001.json
        derived/
          2026-05-24_12-30-00_leaf_001_thumb.webp
          2026-05-24_12-30-00_leaf_001_annotated.jpg
```

`plant.json` — snapshot/manifest файлового датасета растения, не primary state.

`timeline.jsonl` — append-only audit/event export.

`photos/originals` — оригиналы фото и JSON-манифесты. Пара `photo + JSON` — dataset files.

`photos/derived` — миниатюры, обработанные версии, аннотации.

Источником готового обучающего artifact остаётся пара `photo + JSON`, но этот JSON генерируется как snapshot из PostgreSQL и InfluxDB. Он не является runtime authority.

---

## 15. Формат JSON рядом с фото

Минимальный JSON:

```json
{
  "schema_version": "1.0",
  "photo_id": "2026-05-24_12-30-00_leaf_001",
  "plant_id": "tomato_001",
  "captured_at": "2026-05-24T12:30:00+05:00",
  "photo_type": "leaf_closeup",
  "file": {
    "original": "2026-05-24_12-30-00_leaf_001.jpg",
    "sha256": "..."
  },
  "plant_context": {
    "crop": {
      "value": "tomato",
      "status": "confirmed_unchanged"
    },
    "growth_stage": {
      "value": "vegetative",
      "status": "probable"
    },
    "day_from_planting": {
      "value": 18,
      "status": "confirmed_updated"
    }
  },
  "system_state": {
    "ph": {
      "value": 6.1,
      "status": "confirmed_updated",
      "measured_at": "2026-05-24T12:30:00+05:00"
    },
    "ec": {
      "value": 1.8,
      "status": "confirmed_updated",
      "measured_at": "2026-05-24T12:30:00+05:00"
    },
    "light_mode": {
      "value": "16/8",
      "status": "confirmed_unchanged"
    }
  },
  "agent_reports": [
    {
      "provenance": {
        "source": "agent",
        "agent_id": "vision_observation_agent",
        "model_version": "mock-vision-v0",
        "prompt_version": "vision-observation-v1",
        "created_at": "2026-05-24T12:31:00+05:00",
        "output_ref": "evt_002",
        "source_refs": ["photo:2026-05-24_12-30-00_leaf_001"]
      },
      "message_envelope": {
        "agent_id": "vision_observation_agent",
        "claim_type": "hypothesis",
        "confidence": "low",
        "requires_human_approval": false,
        "can_train_on": false,
        "source_refs": ["photo:2026-05-24_12-30-00_leaf_001"],
        "consumable_output": "Фото пригодно. Есть лёгкое пожелтение края нижнего листа. Нужен lower_leaf_closeup.",
        "ui_spoiler_note_ref": "ui:vision_observation_agent:2026-05-24_12-31-05"
      },
      "ui_feed_snapshot": {
        "event_id": "ui:vision_observation_agent:2026-05-24_12-31-05",
        "event_type": "ui_spoiler_note",
        "stream": "ui_feed",
        "created_at": "2026-05-24T12:31:05+05:00",
        "source_agent_id": "vision_observation_agent",
        "payload": {
          "source_message_ref": "evt_002",
          "spoiler_title": "поразмыслил",
          "text": "Симптом слабый и не уникальный. pH/EC подтверждены, но по фото не хватает крупного плана нижнего листа."
        },
        "consumable_by_agents": false,
        "visible_to_agents": false,
        "snapshot": true
      },
      "needs_more_data": ["lower_leaf_closeup"]
    }
  ],
  "export_snapshot": {
    "snapshot_at": "2026-05-24T12:31:10+05:00",
    "source_event_id": "evt_002",
    "authoritative": false,
    "postgres": {
      "human_review": {
        "status": "not_reviewed",
        "verdict": null,
        "comment": null,
        "reviewer_role": null,
        "reviewed_at": null
      },
      "dataset": {
        "status": "raw",
        "split": null,
        "curator_decision": "deferred",
        "confirmation_source": null,
        "evidence_refs": [],
        "curator_notes_ref": null,
        "corrected": false,
        "follow_up_seen": false,
        "can_train_on": false,
        "label_version": 1
      },
      "sync": {
        "status": "local_only",
        "local_storage_bytes": 73400320,
        "upload_prompt_threshold_bytes": 209715200,
        "upload_prompt_visible": false,
        "last_attempt_at": null,
        "server_id": null
      }
    },
    "sensor_window": {
      "source": "manual_measurement",
      "from": "2026-05-24T12:15:00+05:00",
      "to": "2026-05-24T12:30:00+05:00",
      "future_source": "influxdb",
      "aggregation": "last"
    }
  }
}
```

---

## 15.1. Review and curator confirmation lifecycle

`human_review` — canonical lifecycle только для manual human decisions по data item / label.

Review проверяет фото, JSON snapshot, вывод агента, label, качество примера и пригодность для dataset.

Human review не является обязательной ручной проверкой каждого item. Для обычных примеров допустим `curator_decision=selected` с `dataset.confirmation_source=curator_auto`, если есть сильные `evidence_refs`.

Минимальные статусы `human_review.status`:

```text
not_reviewed
approved
corrected
rejected
```

`dataset.status` меняется только как результат review transition, evidence-based curator decision или явно заданного governance rule.

Минимальные поля curator decision:

```text
dataset.curator_decision     — selected | deferred | rejected
dataset.confirmation_source  — null | curator_auto | human | expert | batch_review
dataset.evidence_refs        — ссылки на follow-up, outcome, sensor_window, repeated_photo, согласованные наблюдения
dataset.curator_notes_ref    — ссылка на внутренние curator notes
```

`review_status` не является отдельным authoritative field. В export JSON он допустим только как alias для `human_review.status`.

---

## 16. Статусы достоверности полей

Каждое важное поле должно иметь не только значение, но и статус.

Рекомендуемые статусы:

```text
confirmed_updated    — значение явно обновлено сейчас
confirmed_unchanged  — человек подтвердил, что не изменилось
assumed_unchanged    — система перенесла значение с прошлого раза
probable             — предположение агента или системы
unknown              — неизвестно
conflict             — данные противоречат друг другу
```

Статусы `confirmed_updated` и `confirmed_unchanged` нельзя выставлять только на основании agent-labeled вывода; нужны human review или follow-up evidence.

Это важно для будущего обучения: модель должна отличать точные данные от предположений.

---

## 17. Типы фото

Для MVP достаточно:

```text
whole_plant
leaf_closeup
lower_leaf_closeup
top_view
stem
roots
solution_tank
problem_area
```

Агент может запросить конкретный тип фото:

```text
Нужно фото lower_leaf_closeup при нейтральном свете.
```

---

## 18. Dataset statuses

`dataset.status` — основной lifecycle объекта будущего датасета:

```text
raw             — сырые данные, не использовать для обучения
agent_labeled   — агент сделал предположение, не использовать для обучения
needs_review    — требуется manual, batch или expert review
confirmed       — подтверждено через confirmation_source
rejected        — отклонено review или curator decision
gold            — проверенный качественный пример
excluded        — исключить из обучения
```

Не статусы, а отдельные поля:

```text
dataset.split          — train | eval | holdout | null
dataset.curator_decision     — selected | deferred | rejected
dataset.confirmation_source  — null | curator_auto | human | expert | batch_review
dataset.evidence_refs        — список ссылок на подтверждающие evidence
dataset.curator_notes_ref    — ссылка на внутренние curator notes
dataset.corrected       — человек исправил label или metadata
dataset.follow_up_seen  — есть результат через 1–3 дня
```

Правило:

```text
MVP: can_train_on=true допустим только если:
dataset.curator_decision = selected
AND dataset.split = train
AND dataset.evidence_refs not empty
AND (
  (dataset.status = confirmed
  AND dataset.confirmation_source in {curator_auto, human, expert, batch_review}
  )
  OR
  (dataset.status = gold
  AND dataset.confirmation_source in {human, expert, batch_review}
  )
)
```

`dataset.split=eval` и `dataset.split=holdout` нельзя использовать для fine-tuning train. Они используются только для evaluation/quality checks.

`gold` требует human/expert review или batch review approval. `curator_auto` может подтвердить обычный train item, но не может сделать его `gold`.

---

## 19. Как не испортить будущий датасет

Нельзя:

- обучаться на автодиагнозах агента;
- считать гипотезу фактом;
- смешивать confirmed и agent_labeled;
- использовать плохие фото без отметки качества;
- терять prompt_version и model_version;
- игнорировать outcome после действия.

Нужно хранить:

```text
source: agent | user | expert | follow_up
model_version
prompt_version
confidence
human_review.status
dataset.confirmation_source
dataset.evidence_refs
reviewer_role
dataset.split
created_at
outcome
```

---

## 20. Timeline и БД проекта

PostgreSQL хранит текущее операционное состояние. `timeline.jsonl` — append-only audit/event export: события дописываются туда для аудита, отладки, импорта и экспорта. Он не primary state.

БД проекта может хранить индекс, ссылки на события и текущие состояния сущностей.

Каждая строка — одно событие.

Пример:

```json
{"event_id":"evt_001","event_type":"user_photo","created_at":"2026-05-24T12:30:00+05:00","source_type":"user","source_id":"local_user","topic":"plant:tomato_001:image_capture","payload":{"plant_id":"tomato_001","photo_id":"2026-05-24_12-30-00_leaf_001","photo_type":"leaf_closeup"},"consumable_by_agents":true,"audit_log":{"runtime_decision":"publish","adapter":"photo_capture_to_bus_event"}}
{"event_id":"evt_002","event_type":"agent_conclusion","created_at":"2026-05-24T12:31:00+05:00","source_type":"agent","source_id":"vision_observation_agent","topic":"image_observation","payload":{"message_envelope":{"agent_id":"vision_observation_agent","claim_type":"hypothesis","confidence":"low","requires_human_approval":false,"can_train_on":false,"source_refs":["photo:2026-05-24_12-30-00_leaf_001"],"consumable_output":"Фото пригодно. Диагноз не подтверждён.","ui_spoiler_note_ref":"ui:vision_observation_agent:2026-05-24_12-31-05"}},"consumable_by_agents":true,"audit_log":{"runtime_decision":"speak","adapter":"agno_output_to_message_envelope"}}
{"event_id":"ui:vision_observation_agent:2026-05-24_12-31-05","event_type":"ui_spoiler_note","stream":"ui_feed","created_at":"2026-05-24T12:31:05+05:00","source_agent_id":"vision_observation_agent","payload":{"source_message_ref":"evt_002","spoiler_title":"поразмыслил","text":"Симптом слабый и не уникальный."},"visible_to_agents":false,"consumable_by_agents":false}
```

Плюсы JSONL:

- просто дописывать;
- легко читать;
- легко импортировать или синхронизировать с БД;
- подходит для аудита решений;
- удобно для учебного понимания event sourcing.

---

## 21. Ленивый upload / sync

В MVP не делаем полноценный server sync lifecycle.

MVP sync status:

```text
local_only
```

KISS-правило для интерфейса:

```text
если локальное хранилище dataset превышает 200 MB
→ показать фразу:
"Нужно отправить данные для улучшения. Подтвердите, когда будет подключение по Wi-Fi."
```

Эта подсказка не меняет `sync.status` и не означает, что сервер уже есть.

Stage sync/server появится позже и может добавить:

```text
pending_upload
uploading
uploaded
server_verified
sync_failed
```

До появления сервера `server_verified` запрещён.

Будущий idempotency key: `plant_id + photo_id + sha256`.

---

## 22. Первый рабочий пользовательский flow

```text
1. Система утром пишет: “Как томат сегодня?”
2. Пользователь отвечает и загружает фото.
3. Система сохраняет фото + JSON.
4. Vision Observation Agent публикует краткий conclusion.
5. Plant State Agent обновляет вероятное состояние.
6. Hydroponics Advisor Agent проверяет pH/EC и риски.
7. Safety Gate Agent блокирует опасные рекомендации без данных.
8. Companion Agent формирует понятный ответ пользователю.
9. Task Agent создаёт follow-up.
10. Всё пишется в timeline.jsonl.
```

---

## 23. Первый рабочий demo-scope

Должно работать:

- одно растение `tomato_001`;
- daily check-in;
- загрузка фото;
- ручной ввод pH/EC;
- сохранение фото + JSON;
- timeline.jsonl;
- mock или real Vision Observation Agent;
- structured agent conclusions;
- UI Spoiler Note с `consumable_by_agents=false` и `visible_to_agents=false`;
- Hydroponics Advisor Agent без жёстких дозировок;
- Safety Gate;
- задачи и human approval;
- dataset statuses.

---

## 24. Минимальный стек

Backend:

```text
Python + FastAPI
```

Frontend:

```text
React / Next.js / PWA
```

AI:

```text
AGNO / Agno SDK для agents / teams / workflows внутри монолита
LLM для диалога и structured outputs
Vision model для фото
Mock agents на раннем этапе
```

Storage:

```text
PostgreSQL для операционных данных + локальные файлы + JSON + JSONL
InfluxDB позже для sensor time-series
```

Фото и JSON-манифесты для будущего дообучения:

```text
файловый training export, собираемый из PostgreSQL + InfluxDB
```

Позже для масштабирования:

```text
DuckDB для аналитики / object storage / dataset registry / InfluxDB для sensors / telemetry
```

---

## 25. Простая структура репозитория

Нормативные проектные документы живут в `.memory-bank/` и маршрутизируются через `.memory-bank/spec-index.md`.

`docs/` не является source of truth и не участвует в routing. Если он появится, это только export/readme layer для людей.

```text
agro-intellect/
  AGENTS.md
  README.md
  .memory-bank/
    constitution.md
    spec-index.md
    index.md
    product.md
    requirements.md
    invariants.md
    glossary.md
    architecture/
    contracts/
      agent_contracts.md
      agent_chat_bus.md
      agno_runtime.md
    domains/
      data_model.md
      photo_protocol.md
    states/
      dataset_lifecycle.md
      human_review.md
    testing/
      index.md
    adrs/
  schemas/
    bus_event_envelope.schema.json
    plant.schema.json
    timeline_event.schema.json
    message_envelope.schema.json
    photo_manifest.schema.json
    agent_report.schema.json
    task.schema.json
    human_review.schema.json
  examples/
    valid/
    invalid/
  app/
    backend/
      agents/
      teams/
      workflows/
      db/
        migrations/
      services/
      schemas/
    frontend/
      src/
  tests/
    schema/
    safety/
    workflow/
    agent_contracts/
  data/
    plants/
      tomato_001/
        plant.json
        timeline.jsonl
        photos/
          originals/
          derived/
```

---

## 26. Task Card: Agent Chat Bus и Competence Protocol

### Цель

Реализовать KISS-протокол, где каждый агент отвечает за одну компетенцию, Agent Chat Bus содержит только consumable события для агентной системы, а UI-only спойлеры и silent-пояснения остаются только представлением для пользователя.

### Нужно

- описать `Agno Runtime Boundary` в `.memory-bank/contracts/agno_runtime.md`;
- описать `Agent Chat Bus` в `.memory-bank/contracts/agent_chat_bus.md`;
- описать `Competence Boundary` для каждого агента в `.memory-bank/contracts/agent_contracts.md`;
- зарегистрировать эти specs в `.memory-bank/spec-index.md`;
- описать `BusEventEnvelope` в `schemas/bus_event_envelope.schema.json`;
- описать `MessageEnvelope` в `schemas/message_envelope.schema.json`;
- описать `UIFeedEvent` в `schemas/ui_feed_event.schema.json`;
- в `schemas/photo_manifest.schema.json` сделать `plant_id` обязательным;
- в `schemas/timeline_event.schema.json` для `event_type=user_photo` сделать `payload.plant_id` обязательным;
- в PostgreSQL `photo_catalog` сделать `plant_id NOT NULL` и `photo_id UNIQUE`;
- описать runtime decision агента: `speak | silent | clarify | escalate`;
- реализовать адаптер: Agno Agent/Workflow output → доменный `MessageEnvelope`;
- если Agno Team настроен и включён, пропускать Agno Team output через тот же доменный адаптер;
- запретить прямую публикацию Agno output в Agent Chat Bus без runtime decision и доменного адаптера;
- добавить типы рабочих событий Agent Chat Bus:
  - `agent_conclusion`;
  - `agent_clarification_request`;
  - `agent_quoted_detail_reply`;
  - `agent_team_signal`;
  - `safety_block`;
- добавить типы UI Feed:
  - `agent_silent_decision`;
  - `ui_spoiler_note`;
  - `agent_ui_status`;
  - `system_ui_status`;
  - `debug_lite_card`;
- добавить поле `consumable_by_agents`;
- добавить поля `event_id`, `event_type`, `created_at`, `source_type`, `source_id`, `topic`, `payload`, `consumable_by_agents`, `audit_log` для `BusEventEnvelope`;
- добавить поля `agent_id`, `claim_type`, `confidence`, `requires_human_approval`, `can_train_on`, `source_refs`, `consumable_output`, `ui_spoiler_note_ref` для `MessageEnvelope`;
- добавить поля `event_id`, `event_type`, `stream`, `created_at`, `source_agent_id`, `payload`, `visible_to_agents`, `consumable_by_agents` для `UIFeedEvent`;
- запретить передачу UI Feed другим агентам;
- запретить передачу `ui_spoiler_note` другим агентам как рабочего контекста;
- зафиксировать уровни влияния:
  - `agent_conclusion` → мягко;
  - `agent_team_signal` → сильно;
  - `safety_block` → жёстко;
- реализовать правило краткости по умолчанию;
- реализовать уточнение через цитирование сообщения;
- разрешить крупное сообщение только для Team Signal или Safety Block.

### Нельзя

- позволять агентам читать UI Spoiler Note как рабочий контекст;
- позволять агентам напрямую командовать друг другом;
- считать Agno Team, Agno Workflow или Agno memory/storage самим Agent Chat Bus;
- использовать Agno Team в режиме `coordinate`, если Agno Team настроен и включён;
- считать вызов агента в Agno Workflow публикацией в Agent Chat Bus;
- считать Agno workflow event или `step_completed` доменным фактом;
- публиковать длинные ответы без запроса;
- использовать крупный ответ для обычных сообщений;
- смешивать conclusion и reasoning.

### Acceptance criteria

- каждый агент имеет одну явно описанную компетенцию;
- Agno используется как SDK исполнения, а не как доменный Agent Chat Bus;
- Agno Team не обязателен для MVP;
- если Agno Team настроен и включён, режим `coordinate` не используется;
- каждый вызванный агент возвращает runtime decision;
- каждое событие Agent Chat Bus проходит через `BusEventEnvelope`;
- `user_photo.payload.plant_id` обязателен и не выводится только из `topic`;
- каждый рабочий output агента внутри Bus проходит через `MessageEnvelope`;
- каждое UI Feed событие проходит через `UIFeedEvent`;
- `ui_spoiler_note_ref` ссылается только на `UIFeedEvent.event_id`;
- `silent` не создаёт `MessageEnvelope` и не попадает в Agent Chat Bus;
- обычный conclusion/output занимает 1–3 строки;
- если агенту не хватает информации, он задаёт короткий clarification request;
- если к агенту обратились с цитированием, он отвечает 3–7 строками;
- `ui_spoiler_note` имеет `consumable_by_agents=false` и `visible_to_agents=false`;
- `ui_spoiler_note_ref` может ссылаться только на UI Feed событие с `visible_to_agents=false`;
- `can_train_on=true` только если `dataset.curator_decision=selected` AND `dataset.split=train` AND `dataset.evidence_refs` не пустой AND (`confirmed` с `curator_auto|human|expert|batch_review` OR `gold` с `human|expert|batch_review`);
- другой агент не получает UI Feed в свой input;
- `agent_conclusion` имеет мягкое влияние;
- `agent_team_signal` имеет сильное влияние;
- `safety_block` имеет жёсткое влияние и приоритет над другими событиями;
- крупный ответ появляется только при `agent_team_signal` или `safety_block`;
- tests проверяют, что UI-only/non-consumable поля не передаются другим агентам.

---

## 27. Canonical Memory Bank greenfield flow

Единственный process order проекта задаёт Memory Bank greenfield routing.

Основной путь до task cards:

```text
/analysis
→ /brainstorm, если идея сырая
→ /brief
→ /constitution, если project_principles не ratified/partial
→ /write-prd
→ /spec-init
→ /prd
→ /spec-design FT-XXX
→ /prd-to-tasks FT-XXX
→ indexed JSON task cards
```

После cards выполнение идёт через:

```text
/execute TASK-XXX → /verify TASK-XXX → /red-verify TASK-XXX для T2/T3 → /mb-sync
```

`/spec-init` создаёт или обновляет `.memory-bank/spec-index.md` как SDD route map до `/prd`.

`/prd` создаёт functional feature specs: `.memory-bank/features/FT-*.md`.

`/spec-design FT-XXX` проектирует конкретную feature перед task cards.

`/prd-to-tasks FT-XXX` создаёт implementation plan и indexed JSON task cards.

---

## 28. MVP product slices

MVP product slices ниже описывают проверяемые продуктовые инкременты. Они не задают порядок разработки и не заменяют Memory Bank greenfield flow.

- project foundation: AGENTS.md, `.memory-bank/spec-index.md`, product/requirements, architecture specs;
- data model: PostgreSQL state, timeline export, plant/photo snapshots, schema validation;
- Agno runtime: Agno Agent/Workflow, adapter boundary, доменный `MessageEnvelope`;
- Agent Chat Bus: `BusEventEnvelope`, consumable events, UI/Bus split, context filtering;
- daily check-in: вопрос системы, ответ пользователя, запись события;
- photo flow: upload photo, `photo_id`, file storage, JSON export snapshot, DB catalog/status;
- mock Vision Agent: photo, mock conclusion, `MessageEnvelope`, `ui_spoiler_note`, missing data request;
- Hydro Advisor и Safety Gate: pH/EC context, cautious recommendation, safety check, approval;
- tasks/follow-up: missing data task, user input, recommendation, action approval, outcome через 1–3 дня;
- learning loop: curator decision, evidence refs, train/eval/holdout split, export для evaluation/fine-tuning.

---

## 29. Flow разработки

Разработка идёт по Memory Bank greenfield flow из раздела 27.

MVP product slices используются как вход для features и task cards.

Этот раздел не задаёт отдельный порядок.

---

## 30. Тестирование

Минимальные тесты:

- JSON соответствует схеме;
- `BusEventEnvelope` соответствует схеме;
- `MessageEnvelope` соответствует схеме;
- `UIFeedEvent` соответствует схеме;
- output Agno Agent/Workflow конвертируется в доменный `MessageEnvelope`;
- output Agno Team конвертируется в доменный `MessageEnvelope` только если Team настроен и включён;
- Agno output не может попасть в Agent Chat Bus напрямую;
- `TeamMode.coordinate` запрещён тестом/линтером конфигурации только если Team config существует;
- `silent` не создаёт Bus event / `MessageEnvelope`; audit record обязателен; UI Feed event опционален и не consumable для агентов;
- workflow event и `step_completed` не считаются доменным фактом;
- у каждого фото есть JSON;
- у каждого фото есть `plant_id`;
- у каждого JSON есть существующий файл фото;
- `photo_manifest.plant_id` обязателен;
- `user_photo.payload.plant_id` обязателен;
- `photo_id` уникален;
- `schema_version` присутствует;
- `timeline.jsonl` append-only;
- `agent_conclusion` имеет `consumable_by_agents=true`;
- `ui_spoiler_note` имеет `consumable_by_agents=false` и `visible_to_agents=false`;
- `ui_spoiler_note` не передаётся другим агентам;
- `can_train_on=true` только если `dataset.curator_decision=selected` AND `dataset.split=train` AND `dataset.evidence_refs` не пустой AND (`confirmed` с `curator_auto|human|expert|batch_review` OR `gold` с `human|expert|batch_review`);
- UI Feed не передаётся другим агентам;
- обычный output агента краткий;
- quoted detail reply подробнее обычного output, но короче UI Spoiler Note;
- крупный ответ разрешён только для Team Signal или Safety Block;
- автодиагноз не может иметь `can_train_on=true`;
- `gold` требует human/expert review или batch review approval;
- обычный `confirmed` train item может быть `curator_auto`, если есть сильные `evidence_refs`;
- опасные рекомендации требуют approval;
- агент не даёт жёсткую рекомендацию без pH/EC.

---

## 31. Правила безопасности

Агент не должен выдавать как немедленную команду без свежих данных, safety check и human approval:

```text
Добавь удобрение X.
Измени pH до Y.
Подними EC до Z.
Выключи насос.
Поменяй световой режим.
```

Безопасные альтернативы:

```text
Проверь pH и EC.
Сделай фото нижних листьев.
Проверь температуру раствора.
Подтверди, когда измерения будут готовы.
Создать задачу на проверку.
```

Любое действие, которое меняет физическое состояние системы, требует human approval.

Разрешено сформировать pending action proposal / pending approval task. Выполнять можно только approved `action_task`.

---

## 32. Главные ошибки, которых нужно избежать

- Делать “умного советчика” без состояния и timeline.
- Позволять агентам смешивать компетенции.
- Позволять агентам использовать UI Spoiler Note других агентов как рабочий контекст.
- Генерировать длинные ответы по умолчанию.
- Давать дозировки без актуальных pH/EC.
- Считать гипотезу диагнозом.
- Считать автодиагноз пригодным для обучения.
- Делать сложную БД раньше, чем понятна модель данных.
- Складывать binary-фото в PostgreSQL или InfluxDB вместо файлового/object storage.
- Делать Agno источником нормативной истины проекта вместо Design Specs или владельцем runtime-данных вместо PostgreSQL/read model.
- Использовать Agno Team в режиме `coordinate`.
- Делать автополив и автодозирование в MVP.
- Строить многоагентность ради многоагентности.
- Разрабатывать через AI-агентов без AGENTS.md, тестов и acceptance criteria.

---

## 33. Практический roadmap / scope staging

Практический roadmap — это scope staging / product rollout. Он показывает, что входит в MVP и что идёт позже.

Он не задаёт workflow разработки. Выполнение идёт только через canonical Memory Bank greenfield flow из раздела 27.

### Stage 1 — project foundation

- Memory Bank routing;
- AGENTS.md;
- `.memory-bank/spec-index.md`;
- `.memory-bank/product.md`;
- `.memory-bank/requirements.md`;
- `.memory-bank/architecture/*`;
- `.memory-bank/adrs/ADR-*.md`.

### Stage 2 — data model

- `plant.schema.json`;
- `timeline_event.schema.json`;
- `photo_manifest.schema.json`;
- `agent_report.schema.json`;
- валидные и невалидные примеры;
- schema tests.

### Stage 3 — Agent Chat Bus

- message types;
- conclusion/output;
- UI Spoiler Note;
- context filtering;
- concise-by-default protocol;
- quoted detail replies;
- Team Signal;
- Safety Block.

### Stage 4 — first workflow

- daily check-in;
- фото;
- pH/EC;
- mock Vision Agent;
- Hydro Advisor;
- Safety Gate;
- task;
- human approval.

### Stage 5 — learning loop

- Training Data Curator Agent;
- evidence refs;
- dataset statuses;
- train/eval/holdout split;
- outcome через 1–3 дня;
- запрет обучения на raw/agent_labeled;
- подготовка к evaluation.

### Stage 6 — sync и сервер

- lazy upload lifecycle;
- sha256 verification;
- idempotency key;
- `server_verified` status.

### Stage 7 — датчики

Только после стабильного MVP:

- температура;
- влажность;
- pH sensor;
- EC sensor;
- light sensor;
- telemetry;
- InfluxDB/TimescaleDB.

---

## 34. Итоговая формула MVP

```text
Личный томат
+ ежедневный check-in
+ фото
+ ручной pH/EC
+ однокомпетентные агенты
+ общий Agent Chat Bus
+ краткие conclusion/output
+ ui_spoiler_note только для человека
+ safety gate
+ human approval
+ БД проекта для операционных данных
+ timeline.jsonl
+ фото + JSON как файловый датасет
+ dataset statuses
= учебный полигон для будущей farm-scale agentic system
```

Главный принцип:

```text
Агент предлагает.
Система валидирует.
Человек подтверждает опасные действия и спорные/gold данные.
История всё фиксирует.
Датасет учится только на проверенных данных.
```
