# Agro Intellect — компактный план рефакторинга

## Цель

Снизить сложность и количество дублирующего кода без переписывания проекта, смены FastAPI, SQLAlchemy или PostgreSQL.

Сохранить без упрощения:

- Farm/Plant authorization и isolation;
- Safety Gate и human approval;
- post-I/O authorization checks;
- PostgreSQL transactions и реальные concurrency guards;
- provider-output validation;
- secret/auth redaction;
- публичные HTTP contracts.

---

## 1. Очистить репозиторий и включить автоматические проверки

**Почему:** в репозитории есть generated-мусор и неоднородный стиль кода. Это создаёт шум в diff и затрудняет работу агентов.

**Проблемные места:**

- `agro_intellect.egg-info/` закоммичен в Git;
- `.gitignore` не исключает `*.egg-info/`;
- `backend/app/api/feed.py` содержит длинные однострочные модели и handlers;
- встречаются бессмысленные конструкции вроде `except (IntegrityError, Exception)`.

**Действия:**

- удалить `agro_intellect.egg-info/` из репозитория;
- добавить `*.egg-info/` в `.gitignore`;
- подключить Ruff: lint + format;
- запретить несколько statements в одной строке;
- форматировать наиболее проблемные API-модули;
- логировать неожиданные исключения вместо молчаливого превращения любых ошибок в persistence failure.

---

## 2. Сделать явную composition активных фич

**Почему:** состояние Memory Bank, наличие кода и реальное подключение фич расходятся. Часть фич существует, но помечена `planned`; часть router экспортируется, но не подключена; FT-012 middleware подключён глобально.

**Проблемные места:**

- `backend/app/main.py`;
- `backend/app/api/__init__.py`;
- FT-007, FT-011, FT-012, FT-013 в `.memory-bank/features/`.

**Действия:**

- создать один `FeatureRegistry` или `AppComposition`;
- в одном месте подключать routers, middleware, startup hooks и runtime bindings;
- разделить фичи на `active`, `experimental`, `disabled`;
- отключённые фичи не должны импортироваться стандартным приложением;
- синхронизировать lifecycle в Memory Bank с фактическим состоянием кода.

---

## 3. Убрать дублирование HTTP boilerplate

**Почему:** Companion, Task Follow-Up, History и Feed независимо реализуют одинаковые проверки UUID, query parameters, error envelope, `no-store` и обработку исключений.

**Проблемные места:**

- `backend/app/api/companion.py`;
- `backend/app/api/task_follow_up.py`;
- `backend/app/api/history.py`;
- `backend/app/api/feed.py`.

**Действия:**

Создать небольшие общие модули:

```text
backend/app/api/common/
├── errors.py
├── path_ids.py
├── query.py
├── responses.py
└── execution.py
```

Вынести туда:

- `ErrorEnvelope`;
- canonical UUID type и при необходимости один общий raw-path middleware;
- typed query dependencies;
- `Cache-Control: no-store`;
- преобразование domain errors в HTTP responses;
- единый crash shield на HTTP boundary.

Не создавать собственный framework поверх FastAPI.

---

## 4. Исправить пагинацию Plant History

**Почему:** текущая пагинация загружает всю историю растения из четырёх таблиц, преобразует записи в Python, сортирует весь список и только потом применяет `cursor` и `limit`.

Стоимость запроса растёт от общего количества записей, а не от размера страницы.

**Проблемные места:**

- `backend/app/plant_history/service.py`;
- `backend/app/plant_history/repository.py`.

**Действия:**

- перенести сортировку и cursor filtering в PostgreSQL;
- использовать `UNION ALL` общей проекции четырёх источников;
- применять keyset pagination;
- запрашивать `limit + 1` строк;
- добавить composite indexes по `farm_id`, `plant_id`, времени и ID;
- добавить benchmark и тест стабильности cursor.

Пока не создавать отдельную таблицу read-model: сначала проверить производительность `UNION ALL`.

---

## 5. Свести Agent Runtime к одному pipeline

**Почему:** `TaskFollowUpRuntimeService` фактически дублирует общий `AgentRuntimeService` и формирует второй runtime framework со своими executor, assembler, authorization guard, audit, contracts и lifecycle.

**Проблемные места:**

- `backend/app/agent_runtime/service.py`;
- `backend/app/agent_runtime/contracts.py`;
- `backend/app/task_follow_up/runtime.py`;
- `backend/app/task_follow_up/runtime_contracts.py`.

**Целевой pipeline:**

```text
authorize before I/O
→ assemble typed input
→ invoke provider
→ validate output
→ re-authorize after I/O
→ audit
→ publish through feature policy
```

**Действия:**

- оставить один общий runtime pipeline;
- превратить Task Follow-Up в specialization/policy;
- оставить feature-specific input projector, output schema и publisher;
- унифицировать provider invocation и audit boundary;
- удалить повторные validators и повторяющиеся state matrices;
- явно определить реальный caller: HTTP, worker, scheduler или пока `unbound`.

Не проектировать durable worker/retry lifecycle до появления настоящего worker или scheduler.

---

## 6. Заменить generic context filtering на typed DTO

**Почему:** context builder принимает произвольные nested mappings, затем пытается обнаруживать секреты через forbidden-key lists, regex и рекурсивный обход. Это сложно и создаёт ложное ощущение полной защиты.

**Проблемное место:**

- `backend/app/access_admin/context_builders.py`.

**Действия:**

- каждый domain producer формирует allowlisted typed DTO;
- context builder проверяет scope и объединяет уже безопасные DTO;
- raw ORM rows и произвольные mappings не должны пересекать agent boundary;
- redaction оставить дополнительной защитой для logs и external outputs.

---

## 7. Разделить тесты по уровням

**Почему:** некоторые тесты одновременно проверяют публичный contract, provider payload, количество строк в таблицах, внутренние disposition, Timeline events и реализацию DTO. Такие тесты ломаются при любом внутреннем рефакторинге.

**Проблемные места:**

- `tests/backend/task_follow_up/test_runtime.py`;
- feature-specific migration tests;
- повторяющиеся hostile/corruption probes.

**Целевая структура:**

```text
tests/
├── contracts/
├── domain/
├── integration/
├── migrations/
└── e2e/
```

**Действия:**

- contract tests проверяют только внешний contract;
- domain tests проверяют state transitions;
- integration tests проверяют DB, transactions, authorization и реальные races;
- оставить один центральный тест глобального Alembic head;
- feature migration test проверяет только собственную revision, parent и schema/data effects;
- удалить тесты, защищающие только от согласованной ручной порчи БД, если это не часть threat model;
- полный suite запускать перед closure или на wave boundary, а не после каждого локального исправления.

---

## 8. Локально расчленить Companion service

**Почему:** `CompanionGovernanceService` остаётся крупным и смешивает validation, state transition, persistence, projection и audit.

**Проблемные места:**

- `backend/app/companion_governance/service.py`;
- `backend/app/companion_governance/integrity.py`;
- `backend/app/companion_governance/projections.py`.

**Действия:**

Разделить flow:

```text
command validation
→ pure transition planner
→ atomic persistence
→ projection update
→ audit
```

Pure planner должен возвращать план изменений без доступа к БД. Persistence применяет его в одной транзакции.

Не возвращать удалённые full-graph validators и exact projection equality.

---

## 9. Отделить product code от DevRails tooling

**Почему:** product diff и контекст агентов перегружены `.agents`, Memory Bank и workflow-файлами. Небольшое изменение продукта превращается в тяжёлый формальный процесс.

**Проблемные места:**

- `AGENTS.md`;
- `.agents/`;
- `.memory-bank/`;
- workflow и generated operational artifacts.

**Действия:**

- явно отделить generated/vendor-owned tooling;
- исключать его из product code review и метрик по умолчанию;
- сократить обязательный priming context для локальных T0/T1 задач;
- не требовать полный spec/workflow lifecycle для небольших технических исправлений.

---

# Рекомендуемая последовательность

1. Hygiene, `.gitignore`, Ruff и форматирование.
2. Явная composition активных фич.
3. Общий HTTP boundary.
4. SQL pagination для Plant History.
5. Consolidation Agent Runtime.
6. Разделение тестов.
7. Typed context DTO.
8. Companion decomposition.
9. Изоляция DevRails tooling.

---

# Ожидаемый результат

- без смены backend и persistence;
- без переписывания Farm/Plant/Auth/Safety ядра;
- удаление примерно 25–40% кода в основных hotspot-модулях;
- снижение общего product backend ориентировочно на 10–20%;
- меньше дублирующих validators, middleware и runtime abstractions;
- более дешёвое добавление новых endpoint и agent competence;
- тесты проверяют поведение, а не случайную внутреннюю структуру.
