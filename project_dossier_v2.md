# Agro Intellect MVP v2: локальный Farm workspace и AI-first полигон агентной разработки

## Содержание файла и как его читать

Этот файл — исходное Досье проекта v2. Его задача: сохранить продуктовый замысел, архитектурные решения, ограничения MVP и правила, которые должны перейти в Brief, PRD и SDD Design Specs.

Основные источники v2:

- `.memory-bank/constitution.md`: активная Конституция проекта;
- `.memory-bank/prd.md`: активные product scope, actors, constraints и acceptance criteria;
- `.memory-bank/architecture/system-architecture.md`: актуальные architecture и authority boundaries;
- `.memory-bank/spec-index.md`: реестр действующих SDD specs.

Содержание:

- `0. Суть проекта`;
- `1. Позиционирование проекта`;
- `2. Главная формула проекта`;
- `3. Основные цели`;
- `4. AI-first процесс разработки`;
- `5. Что не делать в MVP`;
- `6. Пользовательский продукт`;
- `7. Принцип однокомпетентных агентов`;
- `8. Агенты MVP`;
- `9. Глоссарий агентного взаимодействия`;
- `10. Протокол общения агентов`;
- `11. Отображение в чате и UI`;
- `12. Почему не показывать сырой reasoning`;
- `13. Human-in-the-loop`;
- `14. Accounts, Farm, роли и Plant access`;
- `15. Хранение данных: PostgreSQL, файлы, timeline и будущие сенсоры`;
- `16. Photo JSON manifests`;
- `17. Статусы достоверности полей`;
- `18. Типы фото`;
- `19. Dataset statuses`;
- `20. Безопасность датасета и trainability`;
- `21. Timeline и runtime state`;
- `22. Local auth, privacy и lazy sync`;
- `23. Первый рабочий пользовательский flow`;
- `24. Первый рабочий demo-scope`;
- `25. Минимальный стек`;
- `26. Agent Chat Bus и Competence Protocol: handoff в specs`;
- `27. MVP product slices`.

Не все разделы одинаково нужны на каждом этапе:

```text
/write-prd
→ использовать product scope, non-goals, actors, user flow, safety и governance boundaries.

/prd и /spec-design
→ использовать детальные разделы: Account/Farm/ActorContext, Agent Chat Bus,
   MessageEnvelope, UI Feed, photo/data model, dataset lifecycle, safety и sync constraints.

/spec-improve и /prd-to-tasks
→ переносить только promoted decisions из PRD/spec-layer, не task-like текст Досье напрямую.
```

Короткое правило:

```text
Brief/PRD берут из Досье смысл, scope и ограничения.
Design Specs берут из Досье точные контракты, схемы и инварианты.
```

Нормативность:

- это досье является upstream context, а не binding spec layer;
- после promotion нормативная истина проекта живет в `.memory-bank/spec-index.md` и связанных specs;
- implementation tasks должны появляться через `/write-prd`, `/spec-init`, `/prd`, `/spec-design`, `/spec-improve` и `/prd-to-tasks`.

---

## 0. Суть проекта

Agro Intellect MVP v2 — это не просто приложение для одного томата. Это практический AI-first полигон для проектирования, разработки, тестирования и управления агентными системами агромониторинга.

`MVP v2` теперь является ограниченным `local-first` `Farm` workspace:

- одного локального `Farm` workspace достаточно для `MVP`;
- локальные `Account` входят в scope;
- роли `Boss`, `Engineer` и `Consultant` входят в продуктовую модель;
- несколько `Plant` разрешены;
- `tomato_001` остается initial `Plant` и первым конкретным полигоном проверки;
- `Boss Admin Surface`, `per-Plant access` и `Companion governance` входят в `MVP` scope;
- `production SaaS`, cloud sync, billing, enterprise identity, широкий commercial farm management и automated physical actuation остаются вне `MVP` scope.

Проект сохраняет исходную учебную цель. Маленький гидропонный томат становится первым контролируемым `Plant` внутри локального `Farm` workspace. На нем проект отрабатывает сложные паттерны на маленьком наблюдаемом объекте, прежде чем переносить эти паттерны на более крупные аграрные системы:

- agentic workflows;
- явные `source of truth` boundaries;
- authority и access control для `Account` / `Farm` / `Plant`;
- состояние объекта во времени;
- мультимодальное наблюдение;
- human-in-the-loop decisions;
- Safety Gate enforcement;
- `Companion governance` через явное typed state;
- task orchestration;
- evidence collection;
- dataset governance;
- подготовка controlled learning loop.

Главный продуктовый сдвиг относительно v1:

```text
v1: один локальный пользователь + один томат
v2: один локальный Farm workspace + local Accounts + role-scoped Plant access + initial Plant `tomato_001`
```

Главное архитектурное ограничение сохраняется:

```text
local-first modular monolith
+ PostgreSQL/read model как runtime authority
+ file artifacts для photos/manifests
+ append-only timeline audit
+ explicit agent contracts
+ typed human/governance decisions
+ Safety Gate для physical actions
```

Companion governance не делает Companion скрытым владельцем системы. Companion может организовывать обсуждение, вести явный `IssueStack`, предлагать решения, запрашивать human attention и закрывать discussion issues, когда правила это разрешают. Binding movement требует явных typed records и deterministic backend rules. Governance `DecisionRecord` не является Safety Gate approval и не может разблокировать physical plant actions.

`MVP` должен быть полезен как локальный рабочий инструмент для `Farm` и `Plant` operations уже сейчас и одновременно сохранять reusable patterns для будущей commercial farm-scale agentic monitoring system.

---

## 1. Позиционирование проекта

### 1.1. Что это за проект

Проект не является `production SaaS`-продуктом для внешнего рынка. Это практический учебный проект и локальный рабочий инструмент, который специально держится в ограниченной `MVP`-рамке.

Он выполняет три роли:

1. **Учебный архитектурный полигон** — среда, где я учусь проектировать агентные системы, управлять AI-first разработкой, проверять архитектурные гипотезы и проводить работу через `Memory Bank` workflows.
2. **Локальный `Farm` workspace** — рабочий инструмент для ведения `Plant`, наблюдений, фото, измерений, задач, approvals, истории и рекомендаций в рамках одного локального `Farm` context.
3. **Переходный прототип будущей farm-scale системы** — не полноценная коммерческая платформа, но уже не только single-user tomato toy. `MVP` намеренно включает `Account`, `Boss Admin Surface`, роли, `PlantAccessGrant` и `Companion governance`, чтобы раньше проверить сложные authority/access/governance boundaries.

Главная ценность проекта — рабочая агентная система, которую можно развивать без потери `source of truth` boundaries, human gates, safety rules, data governance и проверяемых workflow. AI-first обучение и архитектурная практика остаются важной целью, но не должны заранее ограничивать продуктовую траекторию.

### 1.2. Чем v2 отличается от v1

В v1 основная рамка была:

```text
один пользователь
+ один Plant `tomato_001`
+ daily monitoring loop
+ агентные выводы, задачи, approvals и датасетная дисциплина
```

В v2 MVP расширяется до:

```text
один локальный Farm workspace
+ local Accounts
+ Boss / Engineer / Consultant
+ несколько Plants
+ per-Plant access
+ Boss Admin Surface
+ Companion IssueStack / CompanionProposal / DecisionRecord governance
```

Это расширение не означает переход к `production SaaS`. В `MVP` по-прежнему не входят cloud hosting как обязательство, billing, enterprise identity, broad farm management, complex sync, sensor runtime dependency и automated actuation.

### 1.3. Долгосрочная цель

Долгосрочная цель — подготовиться к разработке коммерческой агентной системы для аграрных ферм.

Будущая система должна уметь:

- мониторить ферму на протяжении всего цикла выращивания;
- собирать данные из разных источников: сенсоры, камеры, операторы, лабораторные анализы, метеоданные;
- анализировать состояние культур, зон, теплиц или полей;
- выявлять риски по питанию, поливу, климату, болезням, вредителям и урожайности;
- предлагать задачи операторам и агрономам;
- поддерживать роли, доступы и ответственность участников;
- постепенно переходить от рекомендаций к контролируемому управлению;
- сохранять историю решений и результатов;
- формировать датасет для evaluation, fine-tuning и будущего улучшения моделей;
- улучшаться только на основании подтвержденных данных, а не непроверенных гипотез агента.

Текущий `MVP` фиксирует ограниченную `local-first` стартовую модель: один `Farm` workspace, локальные `Account`, несколько `Plant`, explicit governance, `Safety Gate` и traceable learning loop. Эта рамка нужна для управляемого старта, но она не запрещает продукту дальше эволюционировать в коммерческую farm-scale систему после отдельного PRD/spec-stage решения.

---

## 2. Главная формула проекта

Главная формула v2:

```text
локальный Farm workspace
→ Account / Boss / Engineer / Consultant
→ несколько Plant, начиная с tomato_001
→ daily Plant operations
→ Companion governance и explicit DecisionRecord
→ Agent Chat Bus и single-competence agents
→ Safety Gate и human approval для physical actions
→ traceable state, tasks, outcomes и dataset governance
→ AI-first разработка через Memory Bank
→ управляемая эволюция к commercial farm-scale agentic system
```

Коротко:

```text
Agro Intellect MVP v2 is a local-first Farm workspace for safe, traceable,
agent-assisted Plant operations and future farm-scale evolution.
```

В этой формуле `tomato_001` остается важным, но меняет роль:

```text
tomato_001 = initial Plant / migration seed / first real proving ground
```

Он больше не является постоянным ограничением продукта. Теперь это первый объект, на котором проверяются `Plant` workflows, `ActorContext`, `per-Plant access`, photo intake, measurements, agent conclusions, tasks, approvals, outcomes и dataset governance.

Смысл MVP v2 не в том, чтобы сразу построить всю коммерческую платформу. Смысл в том, чтобы выбрать достаточно маленькую, но уже правильную product boundary:

```text
не production SaaS
не broad farm management
не automated actuation
но уже Farm / Account / Plant / access / governance / Safety Gate
```

Именно эта boundary позволяет проверять будущие farm-scale паттерны раньше, не превращая MVP в enterprise-систему.

---

## 3. Основные цели

### 3.1. Продуктовая цель

Создать полезный `local-first` `Farm` workspace для bounded Plant operations:

- вести несколько `Plant`, начиная с `tomato_001`;
- поддерживать локальные `Account`;
- различать роли `Boss`, `Engineer` и `Consultant`;
- управлять `Plant lifecycle` и `per-Plant access`;
- вести daily check-in, фото, ручные pH/EC и другие наблюдения;
- получать осторожные agent-assisted рекомендации;
- создавать задачи и follow-up;
- фиксировать approvals, outcomes и историю решений;
- не допускать physical actions без `Safety Gate` и authorized human decision.

Продукт должен быть достаточно простым для MVP, но достаточно близким к будущему farm-scale направлению, чтобы заранее проверить authority, access, governance и safety boundaries.

### 3.2. Архитектурная цель

Проверить на маленькой, но уже реалистичной модели ключевые паттерны агентной системы:

- как разделять систему на `single-competence agent`;
- как задавать `Competence Boundary`;
- как строить `Agent Chat Bus`;
- как отделять `MessageEnvelope` от raw model output;
- как не смешивать `UI Feed`, `ui_spoiler_note` и agent working context;
- как хранить mutable operational state в `PostgreSQL/read model`;
- как вести append-only `timeline.jsonl`;
- как связывать `Account`, `Farm`, `Plant`, `ActorContext`, tasks, approvals и dataset evidence;
- как строить `Companion governance` через `IssueStack`, `CompanionProposal`, `DecisionRecord` и `HumanAttentionNeeded`;
- как не смешивать `governance approval` и `Safety Gate approval`;
- как строить dataset governance без обучения на непроверенных agent hypotheses.

### 3.3. AI-first цель

Проект остается AI-first разработкой, где Memory Bank и specs управляют работой:

- продуктовые решения фиксируются в PRD и Design Specs, а не в chat context;
- реализация идет через `Spec Before Code`;
- сложные зоны проходят `/spec-design` и `/spec-improve`;
- задачи должны быть traceable от requirements до verification evidence;
- AI-агенты разработки могут помогать с реализацией, ревью и тестами, но не должны самовольно менять product scope, architecture authority или safety rules.

AI-first обучение здесь не заменяет продуктовую цель. Оно помогает строить продукт дисциплинированно и проверяемо.

### 3.4. Learning loop цель

Система должна с самого начала сохранять данные так, чтобы будущий learning loop был возможен без порчи dataset:

- фото и JSON artifacts хранятся как evidence/export artifacts;
- runtime mutable state остается в `PostgreSQL/read model`;
- agent conclusions не становятся ground truth автоматически;
- `can_train_on` определяется только по dataset governance rules;
- `gold` требует human, expert или batch review;
- outcomes и follow-up используются как evidence, а не как автоматическое оправдание старых гипотез.

---

## 4. AI-first процесс разработки

В проекте есть две разные агентные системы:

1. **Агентная система продукта** — product agents, которые помогают вести `Farm`, `Plant`, observations, recommendations, tasks, approvals, dataset governance и Companion discussion governance.
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

AI-агенты разработки могут реализовывать, ревьюить, тестировать и документировать, но не должны самовольно менять architecture, scope, access model, data authority, governance semantics или safety rules.

### 4.1. SDD и уровни истины

Проект ведется SDD way.

```text
Constitution = верхний governing policy.
Design Specs = нормативная истина проекта после promotion.
Design Specs routing = .memory-bank/spec-index.md.
PostgreSQL/read model = runtime authority для mutable operational state.
Account / Farm / Plant / ActorContext = основа authorization и attribution.
DecisionRecord = binding governance record, но не Safety Gate approval.
Safety Gate approval = отдельный physical-action approval path.
human_review / batch_review / expert_review = authority для manual, batch и expert decisions.
dataset governance lifecycle/read-model state = authority для dataset decisions: curator_decision, dataset.status, dataset.split, confirmation_source, evidence_refs и applicable review rules.
InfluxDB = future time-series authority для sensor readings после появления датчиков.
Agent Chat Bus / MessageEnvelope = agent working event stream и output contract.
UI Feed = presentation stream, не agent working context.
timeline.jsonl = append-only audit/export log.
Agno = execution SDK, не source of truth.
```

Ключевое правило:

```text
runtime authority != audit/export != UI presentation != agent execution
```

### 4.2. Agno как SDK исполнения агентов

В продуктовой части проекта используется `Agno` как SDK для реализации agents, teams и workflows внутри modular monolith.

В этом проекте `Agno Agent` — это control loop вокруг модели с:

- tools;
- instructions;
- memory;
- knowledge;
- storage;
- HITL;
- guardrails.

`Agno Team` можно использовать только как техническую группировку agents, но не как domain coordinator.

По умолчанию MVP использует `Agno Agent` + `Agno Workflow`. `Agno Team` не обязателен.

В MVP запрещено использовать `Agno Team` в режиме `coordinate`. Team leader не должен сам решать, что является domain fact, binding decision или рабочим выводом системы.

Разрешенные режимы `Agno Team`, если они действительно нужны:

- `route` — только как технический router к одному executor;
- `broadcast` — только для независимых параллельных проверок;
- `tasks` — только с bounded iterations и domain adapter на выходе.

Жесткое правило:

```text
Agno invocation != Agent Chat Bus publication
```

`Agno Workflow` может вызвать agent, team, tool или вложенный workflow. Это только execution step, а не разрешение публиковать fact, task, proposal, approval или decision.

После каждого вызова product agent должен вернуть `runtime decision`; канонические значения и полный смысл решений заданы в 10.3.

В этом Agno boundary локально важно: `silent` не создает Bus event или `MessageEnvelope`; audit evidence обязателен; `UI Feed` event опционален и не consumable для agents.

Для agent-originated Bus output решения `speak`, `clarify` и `escalate` проходят через domain adapter и `MessageEnvelope` / `BusEventEnvelope`, если будущая binding spec явно не выделит узкое исключение. `silent` не создает `MessageEnvelope`.

`Agno Workflow` events, `Team synthesis`, step output и raw reasoning не являются facts системы, пока не прошли domain adapter и не стали валидным typed output.

### 4.3. Governance и safety в AI-first процессе

`Companion Agent` может помогать вести discussion flow, но `Companion governance` должна быть typed and auditable:

- issues живут в `IssueStack`, а не в скрытой LLM memory;
- proposal живет как `CompanionProposal`, а не как жирный markdown в UI;
- binding governance result живет как `DecisionRecord`;
- unapproved proposal не становится agent context;
- approved governance summary может стать agent-consumable только через spec-approved route.

`DecisionRecord` не может заменить `Safety Gate`, `Safety Gate approval` или authorized human approval для physical actions.

---

## 5. Что не делать в MVP

Не делать в текущем MVP:

- `production SaaS`;
- hosted/cloud sync как обязательную часть MVP;
- billing/subscription boundaries;
- enterprise identity provider;
- broad farm management;
- multi-Farm tenancy, если это не будет отдельно added by PRD/spec-stage;
- microservices вместо local modular monolith;
- автоматическое physical actuation;
- автополив;
- автоматическое управление насосами;
- автоматическое изменение pH/EC;
- автодозирование удобрений;
- автоматическое изменение light regime;
- сложный RAG;
- экспертную панель как обязательную MVP surface;
- полноценный dataset registry;
- сложную multi-agent hierarchy ради самой hierarchy;
- использовать `Agno` как замену domain-owned `Agent Chat Bus`;
- использовать `Agno Team` в режиме `coordinate`;
- делать `InfluxDB` runtime dependency до появления реальных sensors;
- делать real fine-tuning без evaluation, `evidence_refs` и достаточного confirmation/review gate.

Важно: локальные `Account`, один `Farm` workspace, роли `Boss` / `Engineer` / `Consultant`, несколько `Plant`, `PlantAccessGrant`, `Boss Admin Surface` и `Companion governance` входят в `MVP v2` direction. Поэтому они больше не считаются overengineering сами по себе.

MVP должен оставаться bounded:

```text
local-first Farm workspace
+ local auth/authz baseline
+ Account / Farm / Plant / ActorContext
+ Boss Admin Surface
+ per-Plant access
+ daily Plant operations
+ Agent Chat Bus
+ Companion governance
+ Safety Gate
+ tasks / approvals / outcomes
+ dataset governance
```

KISS в v2 означает не "оставить одного пользователя навсегда", а "ввести Accounts/Farm/Admin минимальным способом, достаточным для текущей product boundary".

---

## 6. Пользовательский продукт

Первый user-facing product surface:

```text
Web App/PWA → later mobile wrapper через Capacitor при необходимости
```

Минимальная поверхность v2:

- login/session для local `Account`;
- first setup для локального `Farm`;
- `Boss Admin Surface`;
- personnel list;
- add/invite local user;
- role assignment: `Boss`, `Engineer`, `Consultant`;
- `Plant` list;
- create/archive/restore `Plant`;
- `PlantAccessGrant` / per-Plant access management;
- `Plant` selector;
- daily check-in;
- photo upload;
- manual pH/EC input;
- observation input;
- plant card;
- task list;
- history by day;
- photo history;
- recommendations;
- `Safety Gate` blocks and pending approval prompts;
- human approval/rejection for physical actions;
- `Companion governance` UI: current issue, `HumanAttentionNeeded`, `CompanionProposal`, approve/reject decision, closure/conclusion;
- controlled `ui_spoiler_note` and debug-lite presentation without raw reasoning leakage.

Основной пользовательский сценарий:

```text
Boss opens local Farm workspace
→ manages Accounts, roles, Plants, and access
→ user selects an authorized Plant
→ runs daily check-in / photo / measurement flow
→ product agents publish concise outputs
→ Companion manages discussion governance
→ Safety Gate blocks or routes physical-action wording
→ authorized human approves/rejects action proposals
→ tasks and follow-up outcomes are recorded
→ state, timeline, UI Feed, and dataset evidence stay traceable
```

UI должен быть permission-aware:

- `Boss` видит admin workflows;
- `Engineer` видит assigned `Plant` operations;
- `Consultant` видит only allowed advisory/read/comment context by default;
- пользователь не должен видеть или менять `Plant`, к которым у него нет access;
- `Boss` authority не должен bypass `Safety Gate`.

---

## 7. Принцип однокомпетентных агентов

Каждый product agent отвечает только за одну область компетенции. Детальная Bus/UI boundary остается в главе 10; UI-consumability matrix — в 11.3.

`single-competence agent` не должен:

- самовольно расширять свою роль;
- выполнять работу другого agent;
- отдавать commands другим agents напрямую;
- использовать `UI Feed`, `ui_spoiler_note`, raw reasoning или unapproved proposal как working context/source of truth;
- публиковать длинные ответы без spec-approved route;
- засорять `Agent Chat Bus`, если его вклад не меняет `Global Flow`;
- обходить `ActorContext`, `PlantAccessGrant`, `Safety Gate`, `DecisionRecord` или dataset governance rules.

`single-competence agent` должен:

- читать только разрешенный working context по правилам главы 10;
- использовать только agent-consumable Bus/read-model context и validated `MessageEnvelope`;
- учитывать `ActorContext` и permission-scoped `Plant` context;
- самостоятельно решать, нужно ли реагировать;
- после каждого вызова возвращать `runtime decision` по 10.3;
- кратко публиковать свой `Conclusion / Agent Output`;
- просить уточнение, если информации недостаточно;
- писать крупное сообщение только при важном `Team Signal`, `Safety Block` или другом spec-approved escalation route.

В реализации agent может быть `Agno Agent`, но его competence и права определяются не возможностями SDK, а domain contracts проекта:

- `Competence Boundary`;
- `ActorContext`;
- `Agent Chat Bus`;
- `MessageEnvelope`;
- `Safety Gate`;
- `Companion governance`;
- dataset governance rules.

Вызов agent не означает публикацию. Если agent вернул `silent`, в `Agent Chat Bus` не попадает ничего. Если agent output влияет на state, task, approval, governance, dataset или user-visible physical-action wording, он должен пройти соответствующий domain adapter и policy gates.

---

## 8. Агенты MVP

`MVP v2` сохраняет принцип `single-competence agent`, но добавляет новую важную рамку: agents работают не в абстрактном single-user контексте, а внутри `Farm`, `Account`, `Plant`, `ActorContext` и permission-scoped context.

Все product agents должны уважать:

- `ActorContext`;
- `Farm` boundary;
- `PlantAccessGrant`;
- `Agent Chat Bus` как working stream;
- `MessageEnvelope` как output contract;
- `UI Feed` как presentation-only stream;
- `Safety Gate` для physical-action wording;
- `DecisionRecord` для binding governance decisions;
- dataset governance для trainability и evidence.

Ни один agent не получает права только потому, что SDK, prompt или model output позволяют ему что-то сделать. Права agents задаются domain contracts, state machines, policy gates и PRD/spec decisions.

### 8.1. Companion Agent

Компетенция: пользовательский диалог, поддержание discussion flow и typed `Companion governance`.

В v1 Companion был в основном разговорным agent для daily flow. В v2 он становится transparent governance coordinator, но не hidden owner системы.

Companion отвечает за:

- понятный human-facing dialogue;
- поддержание daily / Plant workflow narrative;
- объяснение outputs других agents простым языком без подмены их компетенции;
- запрос недостающих данных у human roles;
- поддержание явного `IssueStack`;
- выбор `current_issue` с коротким rationale;
- формирование `CompanionConclusion`;
- создание `CompanionProposal`, когда нужен binding direction или decision;
- создание `HumanAttentionNeeded`, когда нужен human reaction;
- публикацию controlled summaries в `UI Feed`;
- подготовку `approved governance summary` только после валидного `DecisionRecord`.

Companion может:

- читать разрешенный `Agent Chat Bus` context;
- видеть только тот `Farm` / `Plant` context, который разрешен текущим `ActorContext`;
- выявлять findings, gaps, problems, open questions и disagreements;
- добавлять или обновлять issues в `IssueStack`;
- выбирать следующий `current_issue` по severity, blocker status, unresolved disagreement или need for human reaction;
- закрывать discussion issue через `CompanionConclusion` / `IssueClosedByCompanion`, если issue resolved enough;
- предлагать next direction через `CompanionProposal`;
- просить `Boss`, `Engineer` или relevant human role принять governance decision;
- оставаться mostly silent/listening, если его вклад не меняет `Global Flow`.

Companion обязан:

- хранить governance state как typed state, а не в скрытой LLM memory;
- ссылаться на `source_refs` для issues, proposals, conclusions и decisions;
- различать `CompanionConclusion` и binding `DecisionRecord`;
- держать `CompanionProposal` до approval как human-visible only;
- не допускать, чтобы `unapproved proposal` попадал в agent working context;
- после approval отдавать agents только `DecisionRecord` или `approved governance summary`, а не raw discussion;
- использовать visibility metadata, а не markdown styling, как authority;
- прогонять physical-action wording через `Safety Gate`;
- явно отделять `governance approval` от `Safety Gate approval`.

Companion не должен:

- самостоятельно ставить диагноз;
- придумывать агрономический conclusion вместо профильных agents;
- подменять `Vision Observation Agent`, `Plant State Agent`, `Hydroponics Advisor Agent`, `Safety Gate Agent` или `Task & Follow-up Agent`;
- принимать binding system decisions без `DecisionRecord`;
- исполнять backend workflow decisions скрыто через prompt/history;
- считать chat consensus authority;
- считать UI markdown, `UI Feed`, `ui_spoiler_note` или raw reasoning source of truth;
- превращать `CompanionProposal` в fact до approval;
- bypass `Safety Gate`;
- делать physical-action safe через `DecisionRecord`;
- unlock `action_task` без valid `Safety Gate approval` и authorized human approval.

Companion output должен проходить обычный `runtime decision` route по 10.3.

Но typed governance effects не должны прятаться внутри обычного prose. Если Companion создает issue, proposal, conclusion или human attention marker, это должно становиться structured event/state через domain boundary.

Pending PRD/spec decisions для Companion:

- scope `IssueStack`: per `Farm`, per `Plant`, per conversation, per daily check-in или per workflow session;
- exact `CompanionProposal` expiry / supersede rules;
- какие `Engineer` decisions являются binding без `Boss`;
- exact `approved governance summary` shape для agent context;
- какие issues Companion может close сам, а какие требуют explicit human acknowledgement.

### 8.2. Vision Observation Agent

Компетенция: наблюдение по фото.

Задачи:

- анализировать качество фото;
- описывать, что видно и чего не видно;
- замечать визуальные симптомы: пятна, пожелтение, увядание, повреждения, деформации;
- отличать observation от diagnosis;
- запрашивать дополнительные фото, если данных мало;
- формировать краткий visual `Conclusion / Agent Output`;
- привязывать observation к authorized `Farm` / `Plant` / `photo_id` context.

Не должен:

- назначать коррекцию pH/EC;
- делать финальный diagnosis;
- создавать tasks на изменение раствора;
- bypass `Safety Gate`;
- видеть photos или Plant context вне разрешенного `ActorContext`.

### 8.3. Plant State Agent

Компетенция: состояние `Plant` во времени.

Задачи:

- обновлять вероятностные/неполные поля состояния в рамках trust/status rules;
- различать `confirmed_updated`, `confirmed_unchanged`, `assumed_unchanged`, `probable`, `unknown`, `conflict`;
- сравнивать текущие observations с прошлой историей;
- фиксировать changes, trends и contradictions;
- сохранять `source_refs` на observations, photos, measurements, tasks, outcomes и reviews;
- учитывать `Farm` / `Plant` scope.

`Plant State Agent` может обновлять probable/unknown/conflict state на основании agent-labeled conclusions и текущих observations. Он не может повышать state до confirmed без human review или follow-up evidence.

Не должен:

- использовать неподтвержденную hypothesis как fact;
- помечать agent-labeled данные как confirmed;
- менять state для `Plant`, к которому текущий actor/context не имеет access;
- считать `CompanionConclusion` или `DecisionRecord` evidence of plant state без domain evidence.

### 8.4. Hydroponics Advisor Agent

Компетенция: гидропонные параметры и агрономическая логика.

Задачи:

- анализировать pH, EC, температуру, влажность, свет, раствор и доступную историю;
- сопоставлять параметры с `Plant` state;
- находить risks;
- давать cautious recommendations;
- запрашивать missing critical data;
- учитывать freshness windows;
- передавать risky wording в `Safety Gate`.

Не должен:

- создавать `action_task` напрямую;
- обходить `Safety Gate`;
- рекомендовать дозировки как mandatory action без `Safety Gate approval`;
- использовать data вне allowed `Farm` / `Plant` context;
- считать `Boss` authority заменой safety checks.

### 8.5. Task & Follow-up Agent

Компетенция: tasks и контроль результата.

Задачи:

- создавать `check_task` и `measurement task` без physical-action approval, если нужны данные;
- создавать `pending approval task` из valid Safety Gate route;
- превращать approved action proposals в `action_task` только после valid approval/unlock semantics;
- создавать follow-up через 1-3 дня;
- отслеживать task status;
- записывать `outcome`: improved, worsened, unchanged или no data;
- учитывать `Account`, `Farm`, `Plant`, assignee и permission context.

Не должен:

- сам решать, что агрономическая recommendation безопасна;
- создавать `action_task` без valid approval;
- менять `Plant` state без подтвержденного event/evidence;
- использовать governance `DecisionRecord` как physical-action approval.

### 8.6. Safety Gate Agent

Компетенция: safety classification и physical-action approval routing.

Задачи:

- классифицировать risky physical actions;
- блокировать physical-action commands без fresh data, safety check и authorized human approval;
- переводить risky recommendations в pending approval flow;
- различать recommendation, check, task и command;
- требовать human approval для действий с pH, EC, solution, pumps, dosing, light regime и other plant-system interventions;
- учитывать actor permission для approval, но не считать permission достаточной safety clearance.

Не должен:

- подменять агрономический анализ;
- давать альтернативный agronomic advice вместо safety classification;
- считать `Boss`, `Engineer`, `DecisionRecord`, chat consensus или UI reaction bypass для `Safety Gate`;
- разрешать automated physical actuation в MVP.

### 8.7. Dataset Governance Agent

Компетенция: dataset lifecycle, gates и trainability rules.

Задачи:

- следить за `dataset.status`: `raw`, `agent_labeled`, `needs_review`, `confirmed`, `rejected`, `gold`, `excluded`;
- проверять допустимость `dataset.split`: `train`, `eval`, `holdout`;
- фиксировать `dataset.corrected` и `dataset.follow_up_seen` отдельно от `dataset.status`;
- запрещать `can_train_on=true` без sufficient confirmation/review/evidence gate;
- запрещать fine-tuning на `eval` и `holdout`;
- фиксировать label/source provenance: agent, user, expert, follow_up, batch review;
- учитывать `Farm` / `Plant` isolation для evidence и exports.

Не должен:

- считать agent output ground truth;
- допускать обучение на непроверенных hypotheses;
- брать `UI Feed`, raw discussion, unapproved proposal или Companion prose как trainable label;
- смешивать data между `Farm` / `Plant` context без разрешенного export/spec route.

### 8.8. Training Data Curator Agent

Компетенция: delayed dataset selection для будущего fine-tuning и evaluation.

Роль в `Agent Chat Bus` минимальная: почти всегда `silent`. Curator читает historical evidence только через allowed context: photos, `export_snapshot` refs to runtime-backed evidence, outcomes, sensor windows, follow-up, reviews и agreed observations. `export_snapshot` refs, snapshots и manifests сами по себе не являются trainability evidence.

Задачи:

- выбирать data для `train`, `eval` и `holdout` после накопления evidence;
- выставлять `dataset.curator_decision`: `selected`, `deferred`, `rejected`;
- фиксировать `dataset.curator_notes_ref`, `dataset.evidence_refs` и `dataset.confirmation_source`;
- auto-confirm ordinary items, если evidence сильный: follow-up, outcome, sensor trend, repeated photos, agreed observations;
- редко задавать question в Bus только при острой необходимости;
- эскалировать на human, batch, sampling или expert review при conflict, low confidence, rare valuable example, gold candidate или high-impact label.

Не должен:

- разрешать training на bare agent hypotheses;
- требовать ручного подтверждения человеком для сотен обычных фото;
- повышать example до `gold` без human/expert review или batch review approval;
- видеть data вне authorized `Farm` / `Plant` / export context.

---

## 9. Глоссарий агентного взаимодействия

Эта глава задает vocabulary и conceptual boundaries для агентного взаимодействия в `MVP v2`. Она не заменяет `Glossary`, PRD, contracts или state specs. Exact schemas, event fields, endpoint names и transition rules должны быть promoted через `/spec-design` и feature-level `/spec-improve`.

Детальные protocol rules находятся в главе 10, UI presentation taxonomy — в главе 11, compact specs handoff — в главе 26.

### 9.1. Agent runtime terms

#### `single-competence agent`

Agent, который отвечает только за одну область компетенции и не выходит за ее пределы.

Пример:

```text
Vision Observation Agent может сказать:
"На фото видны светлые края нижних листьев".

Vision Observation Agent не может сказать:
"Подними EC до 2.1".
```

#### `Competence Boundary`

Явное ограничение, что agent может и не может делать.

`Competence Boundary` важнее возможностей SDK. Даже если `Agno Agent` может вызвать tool или сгенерировать текст, domain contracts решают, можно ли считать это валидным output, task, approval, decision или fact.

#### `runtime decision`

Каждый вызванный product agent должен вернуть ровно одно решение. Канонические значения и полный смысл решений заданы в 10.3.

Короткая glossary-граница: `silent` не создает `MessageEnvelope` или `Agent Chat Bus` event; решения, публикующие agent-originated Bus output, проходят через domain adapter и `MessageEnvelope` / `BusEventEnvelope`.

#### `Conclusion / Agent Output`

Краткий structured output agent, который может быть использован другими agents, если он прошел `MessageEnvelope` validation и опубликован в `Agent Chat Bus`.

Обычный `Conclusion / Agent Output` имеет мягкое влияние: он может добавить observation, hypothesis, recommendation или missing-data signal, но сам по себе не становится binding decision.

#### `Silent Listener Mode`

Режим, в котором agent читает разрешенный `Agent Chat Bus` context, но не публикует working output, если его вклад не меняет `Global Flow`.

`silent` не значит invisible: `UI Feed` может показать human-facing status или controlled note, но это не становится agent working context.

### 9.2. Account/Farm/Actor context terms

#### `Account`

Локальная user identity для login, authorization, attribution и audit.

#### `Farm`

Bounded local workspace и data-ownership boundary. `Farm` содержит `Plant`, memberships, access grants и admin audit.

#### `Plant`

Farm-managed plant или crop unit. `tomato_001` является initial `Plant`, но не постоянным product limit.

#### `Boss`

Farm owner/admin role. `Boss` управляет personnel, roles, `Plant lifecycle`, `per-Plant access` и admin audit. `Boss` не может bypass `Safety Gate`.

#### `Engineer`

Operational role для assigned `Plant`. `Engineer` выполняет check-ins, photos, measurements, tasks и action approvals только если соответствующее право granted.

#### `Consultant`

Advisory/read/comment role. `Consultant` может участвовать в discussion и давать advice в разрешенном `Plant` context, но не имеет operational authority или binding decision authority by default.

#### `FarmMembership`

Связь между `Account` и `Farm`, которая несет role и membership status для authorization.

#### `PlantAccessGrant`

Явный per-Plant permission grant для `Account` или `FarmMembership`.

#### `ActorContext`

Application/API boundary context, который сообщает system:

- какой `Account` действует;
- в каком `Farm`;
- с какой role/membership;
- с какими `Plant` permissions;
- с какой session/auth provenance.

Все product workflows должны быть `ActorContext`-aware. Agent context builders тоже должны учитывать `ActorContext`, чтобы agents не видели unauthorized `Farm` / `Plant` data.

### 9.3. Agent Chat Bus

`Agent Chat Bus` — domain-owned working event stream для agent-consumable events.

Это не внутренний механизм `Agno`, не `UI Feed`, не `timeline.jsonl`, не runtime authority и не replacement for PostgreSQL/read model.

Agents читают разрешенный Bus context и самостоятельно решают, реагировать ли. Agents не управляют друг другом напрямую.

В `MVP v2` Bus должен быть `Farm` / `Plant` scoped where applicable, permission-aware через `ActorContext`, связан с validated `MessageEnvelope`, защищен от `UI Feed`, raw reasoning, unapproved proposals и unauthorized Plant context, auditable through refs without treating timeline replay as Bus authority.

Candidate scoping refs for later specs: `farm_id`, `plant_id`, `account_id`, `actor_context_ref`, `membership_ref`, `access_scope_ref`. Event types and example shape are in 10.5 and 10.8; compact spec handoff is in 26.1.

### 9.4. MessageEnvelope

`MessageEnvelope` — structured publishable agent output после runtime decision handling.

Conceptual fields: `message_id`, `agent_id`, `claim_type`, `confidence`, `requires_human_approval`, `source_refs`, `consumable_output`, optional `ui_spoiler_note_ref`, and optional non-authoritative `can_train_on`.

`can_train_on` в `MessageEnvelope`, если поле временно остается в examples/contracts, может быть только `false` или `null` и является non-authoritative mirror. Trainability authority принадлежит dataset governance lifecycle и runtime/read-model state, а не agent output.

`MessageEnvelope` keeps raw model output out of the Bus, separates concise agent output from UI explanations, preserves `source_refs`, prevents agent output from creating trainability authority, and links output to `Agent Chat Bus` without making `Agno` source of truth.

В `MVP v2` plant-bound output must also carry or reference `Farm` / `Plant` / permission context. Pending spec decisions remain: exact relationship with `ActorContext`, `farm_id`, `plant_id`, `approved governance summary`, and whether Companion governance events reuse `MessageEnvelope` or separate governance contracts.

### 9.5. UI Feed

`UI Feed` — human-facing presentation stream.

Он может показывать agent silent/status events, controlled `ui_spoiler_note`, debug-lite cards, approval prompts, sync/local storage prompts, `CompanionProposal`, `HumanAttentionNeeded`, current issue focus, issue closure/conclusion presentation и admin audit summaries where useful.

`UI Feed` не является `Agent Chat Bus`, runtime authority, source of truth, dataset label source или agent working context. UI message taxonomy and presentation rules are in chapter 11.

Правило:

```text
Agent Chat Bus = working stream for agents.
UI Feed = presentation stream for humans.
```

`ui_spoiler_note_ref` в `MessageEnvelope` является ссылкой на presentation event. Это не разрешение agents читать spoiler text.

UI markdown, bold text, cards, badges или button state не являются authority. Authority идет из typed state, contracts, `DecisionRecord`, `Safety Gate approval`, runtime state и audit refs.

### 9.6. ui_spoiler_note

`ui_spoiler_note` — controlled UI block для human, который объясняет логику agent/system behavior, но не является raw chain-of-thought и не становится agent working context, confirmed fact, trainable label, `DecisionRecord` или `Safety Gate approval`.

Для `ui_spoiler_note`:

```text
visible_to_agents=false
consumable_by_agents=false
```

General `UIFeedEvent` shape and example projection are covered in 10.9 and chapter 11.

### 9.7. Companion Governance terms

#### `IssueStack`

Explicit structured state для findings, gaps, problems, open questions и disagreements.

`IssueStack` не должен жить только в prompt/history или hidden LLM memory.

Pending PRD/spec decision:

- `IssueStack` scope: per `Farm`, per `Plant`, per conversation, per daily check-in или per workflow session.

#### `current_issue`

Один issue из `IssueStack`, на котором `Companion Agent` держит primary attention.

При смене `current_issue` Companion должен иметь short rationale: severity, blocker status, unresolved disagreement, dependency или need for human reaction.

#### `CompanionConclusion`

Companion summary, что issue resolved enough для discussion purposes.

`CompanionConclusion` не является binding system decision. Если issue требует authority, conclusion должен ссылаться на existing or pending `DecisionRecord`.

#### `IssueClosedByCompanion`

Typed event/state transition, который фиксирует, что Companion считает discussion issue closed.

Closure означает:

```text
discussion resolved enough
```

а не:

```text
backend may execute action
```

#### `CompanionProposal`

Typed human-visible proposal от Companion.

`CompanionProposal` может предлагать process direction, next decision или resolution of disagreement. Он не становится operative до valid human approval/rejection.

До approval:

```text
visible_to_humans=true
visible_to_agents=false
```

UI может показать proposal prominently, но markdown/styling не является authority.

#### `DecisionRecord`

Typed binding governance record, созданный из valid human decision по `CompanionProposal`.

`DecisionRecord` может направить discussion, workflow или domain direction в рамках existing backend rules. Он не может:

- bypass `Safety Gate`;
- authorize physical action;
- create `action_task` without `Safety Gate approval`;
- turn raw chat into fact;
- make agent hypothesis confirmed plant state by itself.

#### `HumanAttentionNeeded`

Typed marker, что Companion ожидает или требует human reaction.

В UI это может выглядеть как marker, badge, pending decision card или `...`, но authority определяется typed event/state, а не visual representation.

#### `governance approval`

Human approval/rejection of `CompanionProposal`, который может создать `DecisionRecord`.

`governance approval` never authorizes physical action.

#### `approved governance summary`

Agent-consumable summary derived from approved `DecisionRecord`.

Agents may receive approved summary only through spec-approved route. They must not receive raw proposal discussion as fact.

Pending PRD/spec decision:

- exact shape of `approved governance summary`;
- which governance event types become `consumable_by_agents=true`;
- exact roles allowed to approve/reject governance proposals.

### 9.8. Safety and approval distinction

`Safety Gate` — policy boundary для physical-action wording and action routing.

`Safety Gate approval` — physical-action approval path requiring:

```text
fresh data
+ safety check
+ authorized human decision
```

`governance approval` — approval/rejection of `CompanionProposal`.

Эти approval classes нельзя смешивать.

Пример:

```text
DecisionRecord:
"Дальше обсуждаем нехватку pH/EC данных и создаем measurement task."

Safety Gate approval:
"Разрешаю human-performed action_task по корректировке раствора после fresh pH/EC и Safety Gate pass."
```

Первое может направить discussion/workflow. Второе относится к physical action. Первое не заменяет второе.

### 9.9. Clarification Request

`Clarification Request` — короткий Bus event, когда agent или Companion не хватает данных.

Это не direct command. Даже если есть `target_agent_id`, получатель сам решает, реагировать ли, и возвращает обычный `runtime decision`.

Пример:

```text
agent_clarification_request(target_agent_id="vision_observation_agent"):
Пожелтение видно на нижних листьях или только на верхнем ярусе?
```

В `MVP v2` clarification должен уважать `ActorContext` и `PlantAccessGrant`: нельзя просить agent раскрыть context, который недоступен текущему actor/session.

### 9.10. Quoted Detail Reply

`Quoted Detail Reply` — чуть более подробный answer на quoted/targeted request.

Правило:

```text
Обычный conclusion: 1-3 строки.
Quoted Detail Reply: 3-7 строк.
UI Spoiler Note: expanded explanation only for humans.
```

Quoted detail все равно остается concise working output, а не raw reasoning.

### 9.11. Team Signal

`Team Signal` — редкое сильное working message, которое может изменить `Global Flow`.

Примеры:

- обнаружен риск unsafe recommendation;
- отсутствуют critical data;
- output другого agent противоречит evidence;
- нужен human decision;
- Companion detected unresolved blocker.

`Team Signal` должен быть structured enough для Bus/context filtering и не должен содержать raw reasoning.

### 9.12. Safety Block

`Safety Block` — hard stop для relevant action flow.

Он запрещает немедленную physical-action instruction или command, пока не выполнены required conditions:

```text
fresh data
+ Safety Gate pass
+ authorized human approval
```

`Safety Block` может route flow к:

- measurement task;
- check task;
- pending approval wording;
- pending approval task;
- safe explanation.

Он не должен:

- выдавать alternative dosing advice;
- create automated command;
- treat `Boss` or `DecisionRecord` as safety bypass.

### 9.13. Large-Font Team Message

`Large-Font Team Message` — visually prominent UI presentation for important `Team Signal` или `Safety Block`.

Это presentation affordance, а не отдельная authority class.

Правило:

```text
Обычный agent output = concise.
Large visible treatment = only for high-importance team/safety events.
Authority = typed event/state, not typography.
```

### 9.14. Global Flow

`Global Flow` — текущее направление работы системы:

- что сейчас важно;
- какие данные нужны;
- какой `Plant` / issue / task находится в фокусе;
- какие blockers есть;
- какие safety constraints активны;
- какое следующее действие полезно.

В v2 `Global Flow` формируется через:

- typed `Agent Chat Bus` events;
- tasks;
- `Safety Gate` outcomes;
- valid `DecisionRecord`;
- authorized human decisions;
- runtime state;
- `ActorContext` and permissions.

`Global Flow` не принадлежит одному agent. Companion может coordinate discussion и propose direction, но binding movement требует typed state and valid decision paths.

### 9.15. Context Hygiene

`Context Hygiene` — правило, по которому agents получают только approved, relevant, permission-scoped working context.

Allowed context: valid Bus events with `consumable_by_agents=true`, validated `MessageEnvelope`, authorized `Plant` context, approved governance summary, and source/evidence refs exposed through approved context builders.

Forbidden as agent working context: `UI Feed`, `ui_spoiler_note`, raw reasoning, raw chat outside approved context, `unapproved proposal`, UI markdown/styling, unauthorized `Farm` / `Plant` data, timeline replay as Bus authority, photo JSON manifests as mutable runtime state, and `DecisionRecord` as plant-state evidence unless domain evidence supports it.

Detailed context-builder allow/deny lists are in 10.14. Short rule:

```text
Agents consume approved domain context.
Humans see UI presentation.
Runtime state lives in PostgreSQL/read model.
Audit/export lives in timeline/json artifacts.
Execution traces from Agno are not facts until adapted.
```

---

## 10. Протокол общения агентов

### 10.1. Назначение протокола

Протокол общения агентов определяет, какие сообщения могут становиться shared working context, какие остаются только UI presentation, и как agents влияют на `Global Flow`.

В v2 этот протокол должен учитывать не только single-plant flow, но и новые product boundaries:

- `Account`;
- `Farm`;
- `Plant`;
- `ActorContext`;
- `PlantAccessGrant`;
- `Companion governance`;
- `Safety Gate`;
- `UI Feed` isolation.

Главное правило:

```text
Agent Chat Bus = agent-consumable working events.
UI Feed = human-facing presentation.
PostgreSQL/read model = mutable runtime authority.
timeline.jsonl = append-only audit/export.
Agno = execution SDK, not source of truth.
```

Ни один agent не должен читать raw UI history, raw reasoning, markdown styling, unapproved `CompanionProposal` или timeline replay как нормальную authority для agent context.

### 10.2. Главные правила

1. Каждый agent отвечает за одну `Competence Boundary`.
2. В `Agent Chat Bus` попадают только validated events, которые разрешены для agent working context.
3. `consumable_by_agents=true` на Bus event означает permission to consider, но не делает payload factual без проверки type/source/evidence.
4. `UI Feed` events не являются agent context даже если они визуально похожи на важное сообщение.
5. `ui_spoiler_note`, raw reasoning и expanded explanations доступны людям, но не agents.
6. Agent output должен быть concise by default.
7. Если agent не меняет `Global Flow`, он остается в `Silent Listener Mode`.
8. Silent decision может оставить audit evidence и UI-only status, но не публикует `MessageEnvelope`.
9. Если agent не хватает данных, он публикует `Clarification Request`, а не direct command.
10. `target_agent_id` в clarification является routing hint, а не обязательным вызовом.
11. `Team Signal` используется редко и только когда нужно изменить priority, direction или attention.
12. `Safety Block` имеет приоритет над conclusion, recommendation и Team Signal.
13. `Companion Agent` может coordinate discussion через typed governance state, но не может делать hidden decisions.
14. `CompanionProposal` до approval остается human-visible only и не становится agent fact.
15. `DecisionRecord` может направить governance/workflow, но не заменяет `Safety Gate approval`.
16. `Boss` authority, admin UI и governance approval не обходят Safety Gate.
17. Все plant-bound events должны быть scoped через `Farm` / `Plant` / `ActorContext` или явно ссылаться на approved scoped context.
18. Session tokens, auth secrets и raw credential data never enter `Agent Chat Bus`, `UI Feed`, timeline payloads, manifests, screenshots, exports или agent context.

### 10.3. Runtime decision перед публикацией

После invocation agent должен прийти ровно к одному `runtime decision`:

```text
speak
silent
clarify
escalate
```

Смысл решений:

```text
speak:
- publish concise MessageEnvelope
- publish Bus event if it is agent-consumable
- optionally create UI Feed presentation

silent:
- do not publish MessageEnvelope
- do not publish Bus event
- record audit/runtime trace where needed
- optionally show UI-only lightweight status

clarify:
- publish short missing-data request
- include target_agent_id only as hint
- do not force another agent to answer

escalate:
- publish Team Signal or Safety Block route
- may create pending task/proposal path if allowed
- must stay inside competence and safety rules
```

Для agent-originated Bus output `clarify` и `escalate`, как и `speak`, проходят через domain adapter и `MessageEnvelope` / `BusEventEnvelope`, если будущая binding spec явно не выделит узкое исключение.

В v2 `runtime decision` также должен учитывать authorization context:

```text
ActorContext
+ FarmMembership
+ PlantAccessGrant
+ event visibility/consumption rules
+ Safety Gate / governance boundaries
```

Agent не должен публиковать data, которые текущий actor/session не должен видеть.

### 10.4. Размеры ответов

```text
Silent Listener Mode:
- no MessageEnvelope
- no Agent Chat Bus publication
- optional UI-only status or ui_spoiler_note

Ordinary conclusion/output:
- 1-3 строки
- только actionable / working substance
- no raw reasoning

Clarification Request:
- 1 короткий вопрос
- one missing-data target
- optional target_agent_id as hint
- no command semantics

Quoted Detail Reply:
- 3-7 строк
- подробнее обычного conclusion
- still concise
- no hidden chain-of-thought

Team Signal:
- 1-4 строки
- редкий flow-level signal
- должен объяснить practical consequence

Safety Block:
- 1-4 строки visible summary
- explicit blocked_action
- explicit unlock_conditions
- no alternative unsafe advice

UI Spoiler Note:
- expanded human-facing explanation
- UI Feed only
- consumable_by_agents=false
- visible_to_agents=false
```

### 10.5. Типы Agent Chat Bus events

На dossier level ожидаемый набор Bus events выглядит так:

```text
user_message
user_photo
measurement_recorded
agent_conclusion
agent_clarification_request
agent_quoted_detail_reply
agent_team_signal
safety_block
task_created
task_outcome_recorded
human_confirmation
decision_record_created
approved_governance_summary
system_event
sync_event
```

Companion governance может потребовать отдельные event types:

```text
companion_conclusion
human_attention_needed
issue_closed_by_companion
```

Но точный набор должен быть закреплен в PRD/spec-stage. Важно не название event type, а authority rule:

```text
Only approved, scoped, validated, agent-consumable events can enter agent context.
```

События, которые остаются human-visible only:

```text
companion_proposal_created
companion_proposal_revised
companion_proposal_rejected
ui_spoiler_note
agent_ui_status
system_ui_status
debug_lite_card
admin_ui_notice
```

`CompanionProposal` может быть показан в UI, но его raw content не должен попадать в agent context как fact. После valid approval backend может создать `DecisionRecord`, а уже из него может быть сформирован approved governance summary.

Pending PRD/spec decision:

- exact Bus event type list;
- exact `BusEventEnvelope` v2 fields;
- which governance events are `consumable_by_agents=true`;
- whether approved governance summary is a Bus event, read-model projection, or both.

### 10.6. Типы UI Feed events

`UI Feed` нужен для человека, а не для agent working memory.

Ожидаемые projections включают `ui_spoiler_note`, agent/system status, debug-lite, `CompanionProposal`, human attention, approval, safety block, task and admin/audit cards. UI message taxonomy and matrix are maintained in chapter 11.

UI presentation может быть крупной, цветной, закрепленной или интерактивной. Это не меняет authority. Authority находится в typed backend event/state:

```text
Large UI card != DecisionRecord
Approval button != valid approval unless backend creates valid typed record
Spoiler note != evidence
Admin notice != permission grant
```

### 10.7. Уровни влияния рабочих событий

```text
agent_conclusion
→ мягкое влияние
→ observation, hypothesis, missing data или ordinary working output
→ не останавливает flow

agent_team_signal
→ сильное влияние
→ меняет priority, attention или synthesis direction
→ должен быть редким

safety_block
→ hard stop
→ запрещает physical-action advice/action route
→ требует unlock_conditions

decision_record_created / approved_governance_summary
→ governance influence
→ направляет discussion/workflow/domain direction
→ не является Safety Gate approval

task_created / task_outcome_recorded
→ operational influence
→ меняет follow-up loop и future evidence
→ требует actor/farm/plant scope
```

### 10.8. Минимальная форма Bus event в v2

Точная schema должна быть создана в `contracts/*` на spec-stage. На dossier level минимальная форма выглядит так:

```json
{
  "event_id": "evt_2026_06_01_0001",
  "event_type": "agent_conclusion",
  "created_at": "2026-06-01T10:30:00+05:00",
  "source_type": "agent",
  "source_id": "vision_observation_agent",
  "farm_id": "farm_local_001",
  "plant_id": "tomato_001",
  "actor_context_ref": "actorctx_2026_06_01_0001",
  "topic": "image_observation",
  "payload": {
    "message_envelope": {
      "agent_id": "vision_observation_agent",
      "claim_type": "hypothesis",
      "confidence": "low",
      "requires_human_approval": false,
      "can_train_on": false,
      "source_refs": [
        "photo:2026-06-01_10-29-00_leaf_001"
      ],
      "consumable_output": "Фото пригодно. Видно слабое пожелтение нижнего листа. Диагноз по фото не подтвержден; нужны pH, EC и lower_leaf_closeup.",
      "ui_spoiler_note_ref": "ui:vision_observation_agent:2026-06-01_10-30-05"
    }
  },
  "consumable_by_agents": true,
  "audit_log": {
    "runtime_decision": "speak",
    "adapter": "agno_output_to_message_envelope",
    "permission_check": "passed"
  }
}
```

В этом примере важны не конкретные IDs, а v2 shape:

- event scoped to `Farm` and `Plant`;
- actor/session context available by ref;
- source refs point to evidence;
- UI spoiler remains separate;
- Bus payload is concise;
- audit includes runtime/adapter/permission evidence.

Ниже examples intentionally use compact projections/deltas from this shape, чтобы не повторять один и тот же envelope. Omitted envelope fields such as `created_at`, `source_type`, `farm_id`, `plant_id` and `actor_context_ref` still follow the same scoped Bus/UI event rules when applicable.

### 10.9. Пример UI Spoiler Note

```json
{
  "event_id": "ui_2026_06_01_vision_0001",
  "event_type": "ui_spoiler_note",
  "stream": "ui_feed",
  "payload": {
    "source_message_ref": "evt_2026_06_01_0001",
    "spoiler_title": "объяснение",
    "text": "Симптом слабый и может иметь несколько причин. Без свежих pH/EC вывод остается гипотезой, поэтому система просит измерения и дополнительное фото."
  },
  "consumable_by_agents": false,
  "visible_to_agents": false
}
```

UI Spoiler Note может улучшить trust пользователя, но не должен становиться training label, plant fact или agent context. If plant-bound, it still carries the same `Farm` / `Plant` scope as the source message.

### 10.10. Пример уточнения между agents

```text
[agent_clarification_request]
source_agent_id="hydroponics_advisor_agent"
target_agent_id="vision_observation_agent"
farm_id="farm_local_001"
plant_id="tomato_001"

Пожелтение видно именно на нижнем листе или на нескольких ярусах?
```

Ответ:

```text
[agent_quoted_detail_reply]
source_agent_id="vision_observation_agent"
farm_id="farm_local_001"
plant_id="tomato_001"

По текущему фото уверенно виден один нижний лист. Пожелтение слабое, локальное, по краю. Несколько ярусов оценить нельзя: общий кадр не показывает нижнюю часть достаточно хорошо. Нужен lower_leaf_closeup.
```

Такой exchange не является direct RPC. Он проходит через Bus semantics, runtime decision и permission-aware context.

### 10.11. Пример Team Signal

```text
[Safety Gate Agent, Team Signal]
Нет актуальных pH/EC для approval-level рекомендации. Нужно создать measurement task и не обсуждать коррекцию раствора как actionable step.
```

Как compact delta от 10.8 это остается Bus event:

```json
{
  "event_id": "evt_safety_gate_2026_06_01_0001",
  "event_type": "agent_team_signal",
  "source_id": "safety_gate_agent",
  "topic": "safety_gate",
  "payload": {
    "message_envelope": {
      "claim_type": "team_signal",
      "requires_human_approval": true,
      "source_refs": [
        "state:latest_measurements",
        "policy:safety_gate"
      ],
      "consumable_output": "Нет актуальных pH/EC для approval-level рекомендации. Сначала нужны fresh measurements и Safety Gate check."
    }
  },
  "consumable_by_agents": true,
  "audit_log": {
    "runtime_decision": "escalate",
    "permission_check": "passed"
  }
}
```

Team Signal changes attention/priority, but does not unlock physical action.

### 10.12. Пример Safety Block

```json
{
  "event_id": "evt_safety_block_2026_06_01_0001",
  "event_type": "safety_block",
  "source_id": "safety_gate_agent",
  "topic": "safety_gate",
  "payload": {
    "message_envelope": {
      "claim_type": "safety_block",
      "requires_human_approval": true,
      "source_refs": [
        "state:latest_measurements",
        "policy:safety_gate"
      ],
      "consumable_output": "Коррекцию раствора нельзя рекомендовать без fresh pH/EC, Safety Gate pass и authorized human approval."
    }
  },
  "consumable_by_agents": true,
  "audit_log": {
    "runtime_decision": "escalate",
    "blocked_action": "recommend_solution_correction",
    "unlock_conditions": [
      "fresh_pH",
      "fresh_EC",
      "safety_check_passed",
      "authorized_human_approval"
    ],
    "permission_check": "passed"
  }
}
```

`Safety Block` может приводить к `measurement task`, `pending approval task` или safe explanation. Он не должен превращаться в alternative dosing advice. Physical action remains blocked until fresh data + Safety Gate pass + valid human approval for the specific action.

### 10.13. Пример Companion governance exchange

Companion может обнаружить unresolved issue:

```text
[HumanAttentionNeeded]
current_issue="missing_measurement_next_step"
Нужно решить, продолжаем ли текущий discussion flow через measurement task для fresh pH/EC.
```

Companion может создать typed governance proposal. `CompanionProposal` is a typed event, not a UI card; UI card является только projection этого event, а не authority:

```json
{
  "event_id": "evt_companion_proposal_2026_06_01_0001",
  "event_type": "companion_proposal_created",
  "source_id": "companion_agent",
  "topic": "companion_governance",
  "payload": {
    "proposal_id": "proposal_measurement_next_step_001",
    "issue_id": "issue_missing_measurement_next_step",
    "version": 1,
    "proposal_text": "Продолжить текущий flow через measurement task для fresh pH/EC перед обсуждением actionable advice.",
    "rationale": "Для дальнейшего обсуждения не хватает свежих pH/EC, а это не меняет safety или access policy.",
    "recommended_next_direction": "create_measurement_task",
    "visible_to_humans": true,
    "visible_to_agents": false,
    "status": "pending"
  },
  "consumable_by_agents": false,
  "visible_to_agents": false
}
```

Если human approves, backend создает typed `DecisionRecord`:

Minimum binding fields shown here are `proposal_version`, `decision`, `decided_by`, `decider_role` and `decided_at`; without them the governance decision is not auditable enough.

```json
{
  "event_id": "evt_decision_record_2026_06_01_0001",
  "event_type": "decision_record_created",
  "source_id": "governance_service",
  "topic": "companion_governance",
  "payload": {
    "decision_record_id": "decision_measurement_next_step_001",
    "proposal_id": "proposal_measurement_next_step_001",
    "proposal_version": 1,
    "decision": "approved",
    "decision_summary": "Продолжаем текущий flow через measurement task для fresh pH/EC перед обсуждением actionable advice.",
    "decided_by": "account_boss_001",
    "decider_role": "boss",
    "decided_at": "2026-06-01T10:45:00+05:00",
    "safety_gate_authority": "not_granted"
  },
  "consumable_by_agents": true,
  "audit_log": {
    "approved_by_actor_ref": "actorctx_2026_06_01_boss_0001",
    "governance_approval": "approved"
  }
}
```

Даже после `DecisionRecord` physical action остается заблокированным, пока не выполнены fresh data, Safety Gate pass и valid human approval для конкретного action.

### 10.14. Permission-aware context

В v2 context builder для agents должен фильтровать events по:

- `farm_id`;
- `plant_id`;
- `ActorContext`;
- role/membership;
- `PlantAccessGrant`;
- event type;
- `consumable_by_agents`;
- safety/governance visibility rules.

Запрещенный context:

```text
events from another Farm
Plant data outside actor permission
UI Feed
ui_spoiler_note
unapproved proposal
raw chat
raw reasoning
admin notes without typed authority
timeline replay as Bus authority
session tokens / auth secrets / raw credential data
```

Разрешенный context:

```text
validated Bus events
current PostgreSQL/read-model state
source_refs exposed by approved context builder
approved governance summary
task/outcome records within actor scope
Safety Gate records within plant scope
```

### 10.15. Что должно уйти в binding specs

Эта глава задает продуктово-архитектурное направление. Binding spec-layer должен formalize Bus/Message/UI envelopes, `ActorContext` refs, publication and context-builder rules, governance and `Safety Gate` contracts, Agno adapter mapping, audit/timeline append, retention and visibility rules.

До spec promotion эта глава не должна использоваться как implementation task contract. Compact target list for spec decomposition is in chapter 26.

---

## 11. Отображение в чате и UI

### 11.1. Главная идея

Пользователь видит не `Agent Chat Bus`, а human-facing chat/UI surface.

Эта поверхность должна быть удобной и понятной, но она не является source of truth сама по себе. UI показывает разные виды сообщений:

- обычные shared working messages;
- сообщения под спойлером;
- вопросы человеку;
- governance proposals;
- approval prompts;
- safety blocks;
- task cards;
- admin/system notices;
- lightweight status/debug cards.

Важное правило:

```text
UI visibility != agent visibility.
UI gesture != authority.
UI card != domain state.
```

Если сообщение, кнопка или лайк должны повлиять на agents, state, governance, task или approval, backend обязан создать typed event/state record. Agents читают не UI, а approved context через `Agent Chat Bus`, read model и context builders.

### 11.2. Типы сообщений в UI chat

#### Shared Working Message

Обычное сообщение, которое может попасть в agent context.

Примеры:

- user message в рамках authorized `Farm` / `Plant` context;
- concise `agent_conclusion`;
- `agent_clarification_request`;
- `agent_quoted_detail_reply`;
- `agent_team_signal`;
- `safety_block`.

UI может показать такое сообщение обычным chat bubble, compact agent line или highlighted team message. Но agent-consumption определяется не UI-видом, а typed event:

```text
Agent Chat Bus event
+ consumable_by_agents=true
+ valid envelope
+ permission-aware context builder
+ source/evidence refs where needed
```

Фраза "все агенты берут в контекст" на практике означает:

```text
all eligible agents may receive it through context builder,
if event type, Farm, Plant, ActorContext, permissions and safety/governance rules allow it.
```

#### UI Spoiler Note / "поразмыслил"

Сообщение под спойлером — controlled explanation для человека.

Это не raw reasoning и не chain-of-thought. Это специально подготовленное краткое объяснение:

- почему agent так ответил;
- какие были ограничения;
- какие данные missing;
- почему confidence low/high;
- что человек может проверить.

Правила:

```text
stream=ui_feed
event_type=ui_spoiler_note
visible_to_humans=true
visible_to_agents=false
consumable_by_agents=false
```

`ui_spoiler_note` не становится:

- plant fact;
- dataset label;
- agent working context;
- Safety Gate approval;
- governance decision.

#### Human Attention Question

Вопрос для `Engineer` или `Boss`, который требует human reaction.

Это может выглядеть как обычный вопрос в чате, карточка с `...`, badge "нужен ответ", или prompt под сообщением agent. По умолчанию такой вопрос:

```text
visible_to_humans=true
visible_to_agents=false
consumable_by_agents=false
```

Он не берется другими agents в context, пока authorized human не сделает valid reaction.

Варианты реакции:

- ответ текстом;
- approve/reject;
- like/confirm;
- assign task;
- request more detail;
- dismiss.

Ключевой момент: like/confirm под обычным human question в `MVP v2` означает одновременно context release и confirmation. Это не governance approval и не Safety Gate approval. Backend должен проверить role/permission и создать typed record.

Пример:

```text
Engineer нажал like под вопросом:
"Да, это релевантно для tomato_001."

Backend:
- checks ActorContext and PlantAccessGrant
- creates typed human_confirmation with context_release=true
- publishes approved_context_summary or validated Bus event if allowed
```

Agents должны получить только typed result, например:

```text
human_confirmation:
Engineer confirmed the question/result as relevant for tomato_001 and released the typed summary to agent context.
```

Они не должны получать raw UI card, raw like state или hidden UI thread.

Pending PRD/spec decision:

- какие роли могут подтверждать human attention questions;
- точная schema для `human_confirmation` with `context_release=true`;
- нужен ли отдельный `approved_context_summary` вместо публикации typed confirmation summary.

#### Companion Proposal Card

`CompanionProposal` — human-visible proposal от Companion.

UI может показывать его как decision card:

- issue;
- proposal text;
- rationale;
- impact;
- approve/reject buttons;
- expiry/supersede status;
- кто может решить.

До valid approval/rejection:

```text
visible_to_humans=true
visible_to_agents=false
consumable_by_agents=false
```

После valid approval backend создает `DecisionRecord`. В agent context может попасть только `DecisionRecord` или `approved governance summary`, а не raw proposal discussion.

#### Approval Prompt

Approval prompt — UI card для human approval.

В v2 есть два разных approval classes:

```text
governance approval
Safety Gate approval
```

`governance approval` относится к `CompanionProposal` и может создать `DecisionRecord`.

`Safety Gate approval` относится к physical action и требует:

```text
fresh data
+ Safety Gate pass
+ authorized human approval
```

UI обязан визуально различать эти два типа approval. Нельзя показывать governance approval так, будто он разрешает коррекцию раствора, дозировку, насос, свет или другой physical action.

#### Safety Block Card

Safety block должен быть заметным UI-сообщением.

Он показывает:

- blocked action;
- короткую причину;
- unlock conditions;
- safe next steps;
- related measurement/check tasks.

Но UI card является только presentation. Authority находится в typed `safety_block` event и Safety Gate state.

#### Task Card

Task card показывает operational work:

- `measurement task`;
- `check_task`;
- `pending approval task`;
- `action_task`;
- follow-up;
- outcome capture.

Task card может быть agent-visible only through task/read-model context, если task создан valid backend workflow. UI text задачи сам по себе не создает authority.

Для v2 task card должна показывать:

- `Farm`;
- `Plant`;
- assignee;
- role/access constraints;
- due time или follow-up window;
- status;
- source refs;
- safety/approval dependency if any.

#### Admin / Access Notice

Admin notices относятся к `Boss Admin Surface`:

- Account added/disabled;
- role changed;
- `PlantAccessGrant` created/revoked;
- `Plant` archived/restored;
- admin audit event created.

Такие notices видят only authorized humans. Agents не должны читать admin UI text как context. Если access change влияет на agent context, это должно происходить через authorization/context builder, а не через UI notice.

#### System Status / Debug Lite

System status и debug-lite cards помогают пользователю понять состояние системы:

- offline/local mode;
- sync disabled;
- photo upload accepted;
- manifest created;
- agent invocation running;
- local storage warning;
- validation failed.

Эти cards по умолчанию UI-only:

```text
visible_to_humans=true
visible_to_agents=false
consumable_by_agents=false
```

Если status должен стать agent-consumable system event, backend публикует отдельный typed `system_event`.

### 11.3. UI message matrix

Рабочая v2-матрица:

| UI type | Human sees | Agents consume | How it becomes authority |
| --- | --- | --- | --- |
| Shared Working Message | yes | yes, if eligible | validated Bus event |
| UI Spoiler Note | yes | no | never authority |
| Human Attention Question | yes | no by default | authorized reaction creates typed event |
| Like/Confirm Gesture | yes | no by itself | backend validates and creates typed record |
| Companion Proposal Card | yes | no before approval | approved `DecisionRecord` / summary |
| Governance Approval Card | yes | not raw card | `DecisionRecord` |
| Safety Approval Prompt | yes | not raw card | Safety Gate approval record |
| Safety Block Card | yes | yes via Bus/state | `safety_block` event |
| Task Card | yes | via task/read model if scoped | task state |
| Admin Notice | authorized humans only | no | admin audit/authz state |
| System Status | yes | no by default | separate `system_event` if needed |
| Debug Lite Card | dev/authorized only | no | never domain authority |

Эта таблица должна позже стать источником для `UIFeedEvent` contract и UI acceptance tests.

### 11.4. Как выглядит обычный flow в UI

Пример daily check-in:

```text
[User]
Загрузил фото нижних листьев tomato_001.

[Vision Observation Agent, shared]
Фото пригодно. Видно слабое пожелтение одного нижнего листа. Диагноз не подтвержден.

[спойлер: поразмыслил]
Симптом слабый, локальный и может иметь разные причины. Без pH/EC нельзя отделить дефицит от проблемы усвоения.

[Hydroponics Advisor Agent, shared]
Для рекомендации нужны fresh pH и EC. Без них correction advice blocked.

[Human Attention Question, Engineer-only]
Подтверди, что это фото относится к tomato_001 и снято сегодня.

[Engineer reaction]
Like / Confirm.

[System typed event]
human_confirmation created for tomato_001.

[Task Card]
Measurement task: измерить pH и EC сегодня.
```

Важная граница:

```text
Agents do not read the spoiler.
Agents do not read the Engineer-only question.
Agents may read the resulting human_confirmation if backend published it as valid scoped event.
```

### 11.5. Human question semantics

Вопрос человеку может иметь разные цели, и UI должен их различать:

```text
Need data:
- "Введи pH/EC."
- result may become measurement record.

Need confirmation:
- "Подтверди, что фото относится к tomato_001."
- result may become human_confirmation.

Need governance decision:
- "Принять этот CompanionProposal?"
- result may become DecisionRecord.

Need safety approval:
- "Разрешить human-performed action_task после Safety Gate pass?"
- result may become Safety Gate approval record.

Need assignment:
- "Назначить Engineer follow-up?"
- result may become task assignment.
```

Один и тот же UI control не должен скрывать разные semantics. Если визуально это "лайк", backend semantics должны быть явными:

```text
like_confirm = context_release + confirmation for ordinary human questions
approve/reject = governance or safety decision controls
```

Для MVP нельзя перегружать один лайк всеми смыслами:

- like/confirm под обычным human question = confirmation + context release;
- approve/reject buttons = governance or safety decisions;
- task buttons = create/assign/complete task;
- measurement form = create measurement record.

### 11.6. Роли и видимость

UI chat должен быть role-aware:

- `Boss` видит admin/governance/safety prompts в рамках `Farm`;
- `Engineer` видит assigned `Plant` operations и allowed approvals;
- `Consultant` видит только разрешенный advisory/read/comment context;
- unauthorized user не видит чужой `Plant`, admin audit или prompt.

Visibility должна считаться backend rules, а не frontend-only hide/show.

Для каждого UI message нужны как минимум:

```text
farm_id
plant_id when applicable
target_role or target_actor when applicable
visibility class
consumability class
source_refs
typed backend record ref if authority exists
```

### 11.7. Что не показывать как обычный chat text

Нельзя смешивать с обычными сообщениями:

- raw reasoning;
- session tokens;
- auth secrets;
- hidden prompts;
- provider traces;
- raw Agno execution logs;
- unauthorized Plant context;
- raw admin/audit payloads;
- unapproved proposal as if it were fact;
- Safety Gate approval as if it were governance approval;
- governance approval as if it were Safety Gate approval.

Если такая информация нужна для debugging, она должна быть restricted debug surface, redacted, and never agent-consumable by default.

### 11.8. Что должно уйти в binding specs

Эта глава должна feed UI-specific spec-layer parts: `UIFeedEvent` schema, UI message taxonomy, visibility/consumability matrix, human reaction semantics, like/confirm behavior, approval prompt contracts, Companion proposal cards, Safety Block card behavior, task card behavior, admin notice visibility, redaction rules and UI acceptance tests for "not agent-consumable" content.

Cross-boundary Bus/MessageEnvelope/Governance/Safety handoff is in chapter 26. До PRD/spec-stage это остается dossier-level direction. Самый важный open decision: что именно означает лайк под human question и какой typed event backend создает после valid `Engineer` / `Boss` reaction.

---

## 12. Почему не показывать сырой reasoning

`raw reasoning` модели не должен быть частью продукта, agent context, dataset labels, timeline facts или audit evidence.

Причины:

- нестабилен и плохо контролируется;
- может содержать промежуточные ошибочные догадки;
- путает пользователя и agents;
- может раскрыть hidden prompts, tools или credentials;
- не является надежным журналом решения.

Вместо него agent возвращает:

```text
concise conclusion/output
+ structured fields
+ source_refs
+ confidence
+ controlled ui_spoiler_note for humans
```

`ui_spoiler_note` может объяснять ход проверки простыми словами, но остается UI-only: `visible_to_agents=false`, `consumable_by_agents=false`, `not trainable evidence`.

Детальные Bus/UI rules не дублируются здесь: canonical boundary находится в главе 10, UI message matrix — в 11.3. Если UI/proposal/admin/approval content должен стать authority, backend создает typed record: `MessageEnvelope`, `DecisionRecord`, Safety Gate approval, task/outcome, measurement или state transition; raw UI/prose сам по себе не становится agent fact.

---

## 13. Human-in-the-loop

В `MVP v2` человек остается обязательным gate для plant-impacting decisions.

Agents могут:

- анализировать observations;
- просить missing data;
- создавать safe check/measurement tasks;
- предлагать next steps;
- готовить pending approval path;
- вести `Companion governance`.

Agents не могут самостоятельно:

- менять pH/EC, раствор, насосы, свет или dosing;
- выдавать physical action как immediate command;
- подтверждать diagnosis/state без human review или follow-up evidence;
- создавать `action_task` без valid approval path;
- обходить `Safety Gate` через `Boss`, `DecisionRecord`, лайк или chat consensus.

Physical action требует:

```text
fresh data
+ Safety Gate pass
+ authorized human approval
+ task/action tracking
```

В v2 approval должен быть scoped:

```text
Account
+ Farm
+ Plant
+ ActorContext
+ PlantAccessGrant / role authority
```

Важно различать:

- `governance approval`: approval/rejection of `CompanionProposal`, может создать `DecisionRecord`;
- `Safety Gate approval`: physical-action approval, может открыть только human-performed `action_task`.

Пример safe wording:

```text
Похоже на ранний дисбаланс, но уверенность низкая.
Перед любым изменением раствора нужны fresh pH/EC и Safety Gate approval.
```

Unsafe wording:

```text
Добавь 20 мл удобрения и доведи EC до 2.1.
```

Unsafe wording должен быть заблокирован или превращен в pending proposal/task с явными unlock conditions.

---

## 14. Accounts, Farm, роли и Plant access

`MVP v2` вводит bounded `local-first` account/farm model сразу в MVP, но не превращает проект в production SaaS.

Минимальная модель:

```text
one local Farm workspace
+ local Accounts
+ FarmMembership
+ Boss / Engineer / Consultant role presets
+ multiple Plants
+ PlantAccessGrant
+ admin audit
```

`tomato_001` становится initial `Plant`, а не permanent product limit.

### 14.1. Роли

`Boss`:

- управляет Accounts, roles, `Plant lifecycle`, `PlantAccessGrant`;
- видит `Boss Admin Surface` и admin audit;
- может участвовать в governance decisions;
- не bypass `Safety Gate`.

`Engineer`:

- работает с assigned `Plant`;
- делает check-ins, photos, measurements, tasks;
- может approve allowed actions only when granted;
- не видит Plants без access.

`Consultant`:

- advisory/read/comment role;
- работает только в granted `Plant` context;
- by default не создает binding decisions и не approve physical actions.

### 14.2. ActorContext

Каждый product/API workflow должен иметь `ActorContext`:

```text
account_id
farm_id
membership/role
plant permissions
session/auth provenance
```

`ActorContext` нужен для:

- authorization;
- audit attribution;
- UI visibility;
- Bus/context filtering;
- task assignment;
- human approval validity;
- dataset/export isolation.

Frontend hide/show недостаточно. Backend должен enforce access на каждом read/mutate route.

### 14.3. Admin boundaries

Admin actions должны создавать durable `admin audit` records:

- Account created/disabled;
- role changed;
- `Plant` created/archived/restored;
- `PlantAccessGrant` created/revoked;
- membership changed.

Admin UI text не является authority для agents. Context changes происходят через authz/read-model state, а не через UI notice.

Open PRD/spec decisions:

- multi-Farm membership/tenancy is out of MVP; specs should encode one local `Farm` boundary;
- exact role permission matrix;
- who may approve physical actions;
- Plant archive/delete/restore semantics;
- how `tomato_001` migrates into Farm/Plant model.

---

## 15. Хранение данных: PostgreSQL, файлы, timeline и будущие сенсоры

Authority model:

```text
PostgreSQL/read model = mutable runtime authority
local files = photo binaries and artifacts
photo manifest = immutable capture/export artifact
timeline.jsonl = append-only audit/export
Agent Chat Bus = working event stream
UI Feed = presentation
InfluxDB = future sensor time-series, not MVP dependency
```

PostgreSQL хранит текущие mutable records:

- `Account`, `Farm`, `FarmMembership`, `Plant`, `PlantAccessGrant`;
- `photo_catalog`: `photo_id`, `farm_id`, `plant_id`, `captured_at`, `photo_type`, path, `sha256`;
- measurements and plant state;
- tasks, approvals, outcomes;
- `IssueStack`, `CompanionProposal`, `DecisionRecord`;
- human review and dataset lifecycle;
- sync/storage status;
- refs to timeline/events/artifacts.

Фото не храним как blob в PostgreSQL. Оригиналы лежат в local file storage; позже возможен `object storage`.

Required binding для фото:

```text
photo_catalog.photo_id globally unique
photo_catalog.farm_id required
photo_catalog.plant_id required
photo_manifest.farm_id/plant_id required
timeline/user_photo payload includes farm_id/plant_id/photo_id
folder path is helper, not source of truth
```

`timeline.jsonl` не должен становиться runtime authority и не должен replay напрямую в agent context. Domain/application workflow может одновременно:

```text
append timeline audit
+ publish validated Bus event
+ update PostgreSQL/read model
```

Future sensor model:

- `InfluxDB` appears only when real sensors exist;
- `sensor_window_ref` may link photo/observation to future pH/EC/temp/humidity/light data;
- current MVP uses manual measurements.

Secrets/session/auth material must never enter logs, Bus, UI Feed, timeline, manifests, screenshots, exports or agent context. Private `Farm` / `Plant` refs may appear in authorized manifests/exports when they are required for provenance and access-scoped.

---

## 16. Photo JSON manifests

Photo manifest is an artifact next to the photo file, not primary runtime state.

Two manifest kinds:

```text
initial_capture  — created at upload/capture time
export_snapshot  — created later for dataset/export context
```

`initial_capture` should stay small and immutable:

```json
{
  "schema_version": "1.0",
  "manifest_kind": "initial_capture",
  "photo_id": "2026-06-01_10-29-00_leaf_001",
  "farm_id": "farm_local_001",
  "plant_id": "tomato_001",
  "captured_at": "2026-06-01T10:29:00+05:00",
  "photo_type": "lower_leaf_closeup",
  "file": {
    "original": "2026-06-01_10-29-00_leaf_001.jpg",
    "sha256": "..."
  },
  "created_by_actor_ref": "actorctx_2026_06_01_0001"
}
```

`export_snapshot` may include snapshot data assembled from PostgreSQL/read model:

- plant context and trust statuses;
- measurement window;
- agent reports through `MessageEnvelope` refs;
- human review status;
- dataset status;
- evidence refs;
- sync/export metadata.

Manifest rules:

- no mutable authority fields that diverge from PostgreSQL;
- no raw reasoning;
- no auth/session/secrets;
- no UI Feed as trainable evidence;
- no trainability authority; `can_train_on` may be copied only from dataset governance/read model and must never be inferred from manifest/UI content;
- `ui_spoiler_note` may appear only as non-agent, non-trainable snapshot if specs allow.

Minimal export key:

```text
farm_id + plant_id + photo_id + captured_at + sha256
```

---

## 17. Статусы достоверности полей

Каждое важное field должно иметь value + trust status.

Core statuses:

```text
confirmed_updated    — явно обновлено сейчас
confirmed_unchanged  — human подтвердил, что не изменилось
assumed_unchanged    — перенесено forward без свежего подтверждения
probable             — hypothesis / incomplete evidence
unknown              — неизвестно
conflict             — evidence противоречит
```

Rules:

- agent hypothesis alone cannot create `confirmed_*`;
- `confirmed_updated` требует fresh human input, measurement, review или follow-up evidence;
- `confirmed_unchanged` требует explicit human confirmation;
- stale pH/EC must not be treated as fresh;
- `DecisionRecord` is not plant-state evidence by itself;
- `CompanionConclusion` is not confirmation.

Freshness distinction:

```text
analysis freshness: up to 24h for advisory analysis
approval freshness: up to 2h for physical-action approval
```

Exact windows belong in binding specs; dossier-level rule is simple: physical actions require stricter freshness than ordinary analysis.

---

## 18. Типы фото

MVP photo types:

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

Each photo must have:

```text
photo_id
farm_id
plant_id
captured_at
photo_type
sha256
storage path
created_by_actor_ref
```

Agent may request a concrete type:

```text
Нужно фото lower_leaf_closeup при нейтральном свете.
```

Quality metadata should be captured where useful:

- usable/unusable;
- lighting;
- blur;
- framing;
- missing requested view;
- repeated photo/ref to previous.

Photo type and quality are not diagnosis. `Vision Observation Agent` observes image quality and visible features, but does not confirm disease/nutrient diagnosis or recommend physical action.

---

## 19. Dataset statuses

`dataset.status` lifecycle:

```text
raw             — сырые данные, not trainable
agent_labeled   — agent hypothesis exists, not trainable by default
needs_review    — требует manual/batch/expert review
confirmed       — подтверждено valid confirmation_source
rejected        — отклонено
gold            — high-quality reviewed example
excluded        — не использовать
```

Related fields:

```text
dataset.split                 train | eval | holdout | null
dataset.curator_decision      selected | deferred | rejected
dataset.confirmation_source   null | curator_auto | human | expert | batch_review
dataset.evidence_refs         supporting evidence refs
dataset.curator_notes_ref     internal notes ref
dataset.corrected             human/review corrected label or metadata
dataset.follow_up_seen        follow-up outcome exists
can_train_on                  derived/guarded flag
```

`can_train_on=true` requires:

```text
curator_decision = selected
AND dataset.split = train
AND evidence_refs not empty
AND (
  confirmed with curator_auto|human|expert|batch_review
  OR gold with human|expert|batch_review
)
```

Restrictions:

- `eval` and `holdout` are never fine-tuning train data;
- `gold` cannot be created by `curator_auto`;
- `UI Feed`, `ui_spoiler_note`, raw agent output, raw Agno output, raw reasoning, timeline snapshot or photo manifest never grant trainability;
- unapproved `CompanionProposal` and governance prose are not labels;
- UI like/confirm without typed backend record is not a trainability approval;
- Farm/Plant isolation must be preserved in export and dataset selection.

Trainability authority belongs to dataset governance lifecycle/read-model state. It must not be inferred from manifests, timeline replay, `MessageEnvelope`, UI flags, raw agent output, or raw Agno execution artifacts.

Canonical provenance/export metadata to store:

```text
farm_id
plant_id
photo_id
captured_at
sha256
source_refs
model_version
prompt_version
confidence
human_review.status
dataset.confirmation_source
dataset.evidence_refs
reviewer_role
dataset.split
created_at
outcome / follow_up
```

Open PRD/spec decision: how much dataset governance is active in MVP UI versus stored as backend/export metadata only.

---

## 20. Безопасность датасета и trainability

Цель dataset governance — не дать будущему learning loop обучаться на неподтвержденных, смешанных или утекших данных.

Канонические правила lifecycle, statuses, `can_train_on` и provenance находятся в главе 19. Эта глава остается коротким rationale/guardrails section:

- `can_train_on=true` должен быть derived/guarded by dataset governance lifecycle/read-model state, а не свободно редактируемым UI flag;
- `UI Feed`, `ui_spoiler_note`, raw reasoning, raw Agno output, unapproved `CompanionProposal`, governance prose, timeline snapshot, photo manifest and UI like/confirm without typed backend record never grant trainability;
- `Farm` / `Plant` isolation is mandatory for evidence selection and export; unauthorized context cannot enter dataset candidates;
- Dataset export must preserve provenance fields from chapter 19 and must not infer trainability from export artifacts alone.

`Dataset Governance Agent` отвечает за policy checks. `Training Data Curator Agent` может mostly stay silent и выбирать candidates only through chapter 19 evidence refs. `gold` требует human/expert/batch review.

---

## 21. Timeline и runtime state

`PostgreSQL/read model` — runtime authority для mutable state.

`timeline.jsonl` — append-only audit/export log:

- audit;
- debugging;
- import/export;
- later sync support;
- learning of event history by humans.

Он не является:

- primary mutable state;
- normal source for agent context;
- replacement for `Agent Chat Bus`;
- source of trainability.

Правильный flow:

```text
application/domain workflow
→ validate command/event
→ update PostgreSQL/read model when needed
→ append timeline audit
→ publish Agent Chat Bus event only through BusPublicationService
→ update UI Feed only as presentation
```

Agent context builders читают approved runtime/context sources, а не replay timeline. `timeline.consumable_by_agents` если появится, может быть только eligibility marker для validated Bus publication, а не permission for direct read.

Каждый timeline event должен быть scoped where applicable:

```text
event_id
event_type
created_at
source_type/source_id
farm_id
plant_id
actor_context_ref
payload
source_refs
audit_log
```

No secrets in timeline: sessions, tokens, API keys, credentials and raw auth material must be redacted.

---

## 22. Local auth, privacy и lazy sync

MVP работает `local-first` and private by default.

Security baseline:

```text
loopback by default
LAN mode only if explicitly enabled
ActorContext/authz on every Farm/Plant route
LAN mode adds exposure/auth requirements
secret redaction everywhere
```

Loopback is the default exposure boundary, but `ActorContext`, authorization and audit attribution apply to every read/mutate route for `Farm`, `Plant`, photos, tasks, approvals, Bus-visible data, UI Feed and exports. LAN mode only adds extra exposure requirements: explicit enablement, authentication, authorization, token/session protection and CORS/origin controls.

Secrets/session/auth material must never enter:

- logs;
- timeline;
- manifests;
- Agent Chat Bus;
- UI Feed;
- screenshots;
- exports;
- agent context.

Private `Farm` / `Plant` refs are not auth material; they may appear in authorized manifests and exports when needed for provenance and access-scoped operations.

MVP sync status:

```text
sync.status = local_only
```

No server is implied. `server_verified` is forbidden until a real server-sync stage exists.

Lazy sync in MVP is prompt-only:

```text
if local dataset storage > 200 MB
→ show local storage prompt
→ user may acknowledge/dismiss
→ no upload/server availability implied
```

Future sync may add:

```text
pending_upload
uploading
uploaded
server_verified
sync_failed
```

Future idempotency key:

```text
farm_id + plant_id + photo_id + sha256
```

---

## 23. Первый рабочий пользовательский flow

v2 flow начинается не с абстрактного пользователя, а с authorized `ActorContext`.

```text
1. User logs in or opens local session.
2. System resolves Account, Farm, role and Plant access.
3. User selects authorized Plant, initially tomato_001.
4. System asks daily check-in question.
5. User adds observation, photo and/or pH/EC measurements.
6. Backend stores photo file, photo_catalog row and initial_capture manifest.
7. Runtime state and timeline audit are updated.
8. Validated Bus events are published for agents.
9. Vision Observation Agent checks photo quality/features.
10. Plant State Agent updates probable/unknown/conflict state.
11. Hydroponics Advisor Agent checks missing/stale pH/EC.
12. Safety Gate blocks unsafe physical-action wording.
13. Companion summarizes flow and raises HumanAttentionNeeded or CompanionProposal if needed.
14. Task & Follow-up Agent creates measurement/check/follow-up tasks.
15. UI Feed shows shared messages, spoilers, prompts, tasks and safety cards with correct visibility.
16. Outcomes and evidence refs feed dataset governance.
```

Important boundaries:

- `UI Feed` is not agent context;
- `CompanionProposal` is not operative until approval;
- `DecisionRecord` is not Safety Gate approval;
- physical action requires fresh data + Safety Gate pass + authorized human approval.

---

## 24. Первый рабочий demo-scope

Demo scope должен доказать architecture boundaries, not broad farm management.

Must work:

- one local `Farm`;
- local `Account` login/session baseline;
- `Boss` and at least one operational `Engineer` role path, even if minimal;
- `tomato_001` as initial `Plant`;
- Plant selector with access check;
- daily check-in;
- photo upload/capture with `photo_id`, file, `sha256`, manifest and catalog row;
- manual pH/EC input;
- `Agent Chat Bus` vs `UI Feed` split;
- real `Vision Observation Agent` over actual uploaded photo data;
- `Plant State Agent` trust statuses;
- `Hydroponics Advisor Agent` missing-data policy;
- `Safety Gate` for physical-action wording;
- `Task & Follow-up Agent` for measurement/check/follow-up;
- `Companion Agent` with visible `HumanAttentionNeeded` and proposal/decision path;
- dataset status fields and `can_train_on=false` by default;
- timeline audit/export;
- local storage prompt without server implication.

May be deferred or simplified:

- advanced `Boss Admin Surface`;
- full role matrix;
- sync UI prompt/status behavior;
- sensor runtime / InfluxDB.

MVP runtime/demo agent rule:

- product agents must run as real LLM/model-backed flows over actual scoped `Plant` data entered or uploaded by users;
- `Vision Observation Agent` must use actual uploaded photo data through a real vision-capable model or real vision model integration;
- fake, mock, hardcoded or stubbed agent outputs do not satisfy MVP runtime/demo acceptance criteria;
- test-only mocks may exist for automated tests, but not as the MVP runtime path.

Explicitly deferred from first demo:

- `Consultant` UI/path remains in `MVP v2` scope, but is deferred to avoid bloating the first working slice.

Must not be included:

- production SaaS;
- billing;
- enterprise identity;
- multi-Farm tenancy;
- automated actuation;
- real fine-tuning pipeline.

---

## 25. Минимальный стек

Keep modular monolith and KISS.

Backend:

```text
Python
FastAPI
Pydantic/schema validation
PostgreSQL/read model
local filesystem for photos/artifacts
JSONL for timeline export
```

Frontend:

```text
React / Next.js / PWA
role-aware UI
Plant selector
chat/feed surface
task/approval cards
Boss Admin Surface minimal slice
```

AI runtime:

```text
Agno SDK as execution layer
LLM for dialogue and structured outputs
real vision-capable model or real vision model integration for photos
domain adapter → MessageEnvelope / BusEventEnvelope / UIFeedEvent
```

Agno rules:

- Agno is not source of truth;
- Agno memory/storage is not Agent Chat Bus;
- Agno Team is optional;
- `coordinate` is forbidden for domain coordination;
- all outputs pass project-owned adapters and gates.

Future/non-MVP options:

- `InfluxDB` for real sensor readings;
- `object storage` for photos/artifacts;
- `DuckDB` for analytics;
- `Capacitor` mobile wrapper;
- full dataset registry;
- server sync/cloud deployment.

Stack goal:

```text
local-first modular monolith
+ explicit contracts
+ minimal infra
+ strong authority boundaries
+ easy migration path
```

---

## 26. Agent Chat Bus и Competence Protocol: handoff в specs

Старая v1-глава 26 была task card. В v2 досье не должно хранить implementation checklist, но должно сохранить design intent для будущего spec-layer.

### 26.1. Что должно быть формализовано

Будущие specs должны закрепить:

- `Agent Chat Bus` as domain-owned working event stream;
- `BusEventEnvelope` for all Bus events;
- `MessageEnvelope` for agent publishable output;
- `UIFeedEvent` for human-facing presentation;
- `runtime decision` states and semantics from 10.3;
- `Competence Boundary` for every agent;
- Agno output adapter boundary;
- permission-aware context builders for `Farm` / `Plant` / `ActorContext`;
- `Companion governance` events and visibility rules;
- `Safety Block` and `Team Signal` semantics.

### 26.2. Canonical handoff references

This section is an index, not a second copy of protocol rules. Specs should take binding semantics from:

- protocol/runtime/Bus boundaries: chapter 10, especially 10.1-10.5, 10.8 and 10.14;
- UI visibility, consumability matrix and human-facing authority rules: chapter 11, especially 11.1-11.3 and 11.5-11.8;
- `Safety Gate` vs governance approval: chapter 13, with Companion governance handoff in 10.13 and UI approval distinctions in chapter 11.

When promoting this dossier into specs, preserve the authority, visibility and safety semantics from those canonical sections. Use chapter 26 only as the compact handoff and spec-target index.

### 26.3. Future spec targets

This chapter should later feed:

- `contracts/agent-chat-bus.md`;
- `contracts/message-envelope.md`;
- `contracts/ui-feed.md`;
- `contracts/agno-runtime-boundary.md`;
- `contracts/companion-governance.md`;
- `states/agent-runtime-decision.md`;
- `states/safety-gate.md`;
- feature specs for Bus, UI Feed, Agent Runtime, Companion, Safety Gate and Tasks.

### 26.4. What not to keep here

Do not place implementation acceptance checklists in this dossier. Detailed tasks belong to:

```text
/write-prd
→ /spec-init
→ /prd
→ /spec-design
→ /spec-improve
→ /prd-to-tasks
```

The dossier should preserve product/architecture intent. Binding schemas, tests and task acceptance criteria belong in the spec-layer and task records.

---

## 27. MVP product slices

`MVP product slices` описывают проверяемые продуктовые инкременты. Это не порядок разработки и не task decomposition. Binding order later belongs to PRD/spec workflow.

### 27.1. Foundation and source-of-truth slice

Цель: зафиксировать v2 scope before implementation.

Includes:

- `Constitution v2`;
- `glossary`;
- `invariants`;
- PRD/spec-layer promotion route;
- architecture backbone for `Account`, `Farm`, `Plant`, agents, safety and dataset.

Done when: source-of-truth docs no longer describe MVP as single-user/one-plant only.

### 27.2. Local Accounts and ActorContext slice

Цель: every action has actor, role and permission context.

Includes:

- local `Account`;
- local session/auth baseline;
- `FarmMembership`;
- `ActorContext`;
- route-level authorization;
- secret redaction.

Done when: every farm/plant route can answer who acts, in which `Farm`, with which permissions.

### 27.3. Farm, Plant lifecycle and access slice

Цель: `tomato_001` becomes initial `Plant` inside a bounded local `Farm`.

Includes:

- one local `Farm`;
- multiple `Plant` support;
- create/archive/restore minimal lifecycle;
- `PlantAccessGrant`;
- Plant selector;
- admin audit for access/lifecycle changes.

Done when: users see only authorized Plants and plant-bound records carry `farm_id` / `plant_id`.

### 27.4. Boss Admin Surface slice

Цель: Boss can manage people, roles, Plants and access without SaaS complexity.

Includes:

- personnel list;
- role assignment;
- Plant access management;
- minimal admin audit view;
- no billing, enterprise identity or hosted tenancy.

Done when: Boss can grant/revoke access and Engineer/Consultant UI changes accordingly.

### 27.5. Daily Check-in and manual measurements slice

Цель: basic Plant operations loop.

Includes:

- daily question;
- observation input;
- manual pH/EC;
- freshness status;
- trust status updates;
- timeline audit;
- UI Feed display.

Done when: check-in produces scoped state/evidence and agents can request missing data safely.

### 27.6. Photo intake, catalog and manifests slice

Цель: photo flow with durable identity and dataset-ready artifacts.

Includes:

- upload/capture;
- upload-validation gate;
- `photo_id`;
- local file storage;
- `sha256`;
- `photo_catalog`;
- `initial_capture` manifest;
- later `export_snapshot`;
- `farm_id` / `plant_id` binding.

Done when: each accepted photo has file, catalog row, manifest and audit refs.

### 27.7. Agent Chat Bus and UI Feed slice

Цель: agents and humans see different streams with clear authority boundaries.

Includes:

- `BusEventEnvelope`;
- `MessageEnvelope`;
- `UIFeedEvent`;
- `runtime decision`;
- concise output;
- `ui_spoiler_note`;
- permission-aware context builders;
- no UI Feed in agent context; detailed boundary follows chapters 10 and 11.3.

Done when: chapter 10/11.3 boundaries are enforced and agent-consumable/human-only messages cannot leak into each other.

### 27.8. Vision, Plant State and Advisor slice

Цель: photo observations become cautious plant state/advice without unsafe action.

Includes:

- `Vision Observation Agent`;
- `Plant State Agent`;
- `Hydroponics Advisor Agent`;
- visible features and photo quality;
- probable/unknown/conflict state;
- missing-data policy;
- no diagnosis confirmation from agent output alone.

Done when: agents can help interpret observations but cannot invent confirmed facts.

### 27.9. Safety Gate and approvals slice

Цель: physical-action advice is blocked until safe.

Includes:

- physical-action classifier;
- stale/fresh data checks;
- `Safety Block`;
- pending approval task;
- authorized human approval;
- strict separation from `governance approval`.

Done when: unsafe dosing/light/pump/solution wording is blocked or routed to approval.

### 27.10. Companion governance slice

Цель: Companion coordinates discussion without becoming hidden authority.

Includes:

- `IssueStack`;
- `current_issue`;
- `HumanAttentionNeeded`;
- `CompanionConclusion`;
- `CompanionProposal`;
- `DecisionRecord`;
- approved governance summary.

Done when: per chapters 10 and 11.3, unapproved proposals are human-visible only and approved decisions become typed records.

### 27.11. Tasks, follow-up and outcomes slice

Цель: recommendations become trackable work, not loose chat.

Includes:

- `measurement task`;
- `check_task`;
- `pending approval task`;
- human-performed `action_task`;
- assignment;
- 1-3 day follow-up;
- outcome capture.

Done when: every important recommendation has task/outcome path and source refs.

### 27.12. Dataset governance slice

Цель: protect future learning loop.

Includes:

- `dataset.status`;
- `dataset.split`;
- `human_review.status`;
- curator decision;
- evidence refs;
- `can_train_on` guard;
- Farm/Plant export isolation.

Done when: raw/agent-labeled/UI-only data cannot become trainable by accident; UI-only follows the chapter 10/11.3 boundary.

### 27.13. Local security and lazy sync slice

Цель: local-first privacy without pretending a server exists.

Includes:

- `local_only` sync status;
- 200 MB local storage prompt;
- no upload/server implication;
- route-level `ActorContext` / authz always;
- LAN mode auth if enabled;
- redaction across logs, Bus, UI Feed, timeline, manifests, screenshots and exports.

Done when: data stays local/private by default and no UI implies unavailable server sync.

### 27.14. Role-aware Farm PWA slice

Цель: one practical surface for daily work.

Includes:

- login/session state;
- Plant selector;
- daily check-in;
- photo upload;
- measurements;
- chat/feed;
- task cards;
- approval cards;
- safety cards;
- minimal Boss Admin Surface.

Done when: Boss/Engineer can complete the first Plant workflow end to end on `tomato_001`.
