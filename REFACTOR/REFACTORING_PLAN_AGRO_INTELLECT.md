# Agro Intellect — план рефакторинга

## Цель

Снизить связанность, дублирование и стоимость изменений в backend, не меняя продуктовую модель и не ослабляя критические гарантии.

Рефакторинг должен привести к тому, чтобы:

- каждый модуль отвечал за ограниченный набор связанных задач;
- общий runtime-каркас не копировался между агентными компетенциями;
- HTTP-слой не дублировал одну и ту же техническую механику;
- тесты проверяли поведение и реальные риски, а не случайные детали реализации;
- стоимость развития новой фичи не росла из-за существующего boilerplate.

Имплементатор самостоятельно выбирает конкретные внутренние границы и порядок локальных изменений, если сохраняются цели и ограничения этого плана.

---

## Общие ограничения

Рефакторинг не должен сам по себе изменять:

- публичные HTTP-контракты, error grammar и status codes;
- PostgreSQL schema и исторические migrations;
- authorization и Farm/Plant isolation;
- Safety Gate и обязательное human approval;
- idempotency и реальные concurrency guards;
- post-I/O проверки archive/revoke/authorization;
- provider-output validation;
- secret redaction и правила работы с чувствительными данными.

Изменения поведения, требований или схемы должны оформляться отдельно и иметь самостоятельное обоснование.

---

## 1. Подготовить устойчивую основу для рефакторинга

Перед крупными изменениями привести repository hygiene и автоматические проверки в состояние, при котором структурные регрессии быстро обнаруживаются.

Основные направления:

- убрать случайно отслеживаемые generated artifacts;
- закрепить единый формат и базовые lint-правила;
- зафиксировать рабочий baseline ключевых тестов;
- отделить технический cleanup от изменения product behavior.

Причина: без чистого baseline дальнейшие failures трудно отличить от уже существующих проблем и шума репозитория.

---

## 2. Разделить Task Follow-Up domain service

Основное проблемное место:

- `backend/app/task_follow_up/service.py`

Сейчас модуль совмещает несколько самостоятельных lifecycle: ordinary tasks, approvals, action tasks, completion, automatic follow-up, outcomes, queries, idempotency recovery и Timeline events.

Нужно разделить ответственность по устойчивым доменным операциям, сохранив единый публичный facade только там, где он действительно упрощает использование.

Цель:

- локализовать транзакции и recovery logic рядом с соответствующими командами;
- уменьшить количество причин изменения одного класса;
- упростить независимое тестирование lifecycle;
- подготовить Task Follow-Up к последующей унификации agent runtime.

Это первый основной production-refactor, поскольку проблема хорошо локализована и не требует новой архитектуры.

---

## 3. Стабилизировать и разделить Companion Governance

Основное проблемное место:

- `backend/app/companion_governance/service.py`

Перед структурным refactor необходимо убедиться, что активная реализация FT-013 стабилизирована и не находится в процессе изменения тех же файлов и boundaries.

После стабилизации разделить:

- command-side lifecycle;
- query/read side;
- projections и serialization;
- формирование domain/audit events.

Причина: текущий service одновременно управляет authority writes, read model, projections, cursors и HTTP-facing values. Это увеличивает связанность и делает любое изменение Companion дорогостоящим.

Не следует возвращать сложные проверки состояний, достижимых только через согласованную ручную порчу БД, если они не защищают authority, безопасность или поддерживаемый application flow.

---

## 4. Убрать дублирование Agent Runtime orchestration

Основные проблемные места:

- `backend/app/agent_runtime/service.py`
- `backend/app/vision_observation/service.py`
- `backend/app/plant_state/runtime.py`
- `backend/app/hydroponics_advisor/runtime.py`
- `backend/app/task_follow_up/runtime.py`

В этих модулях повторяется общий порядок:

```text
input assembly
→ завершение DB transaction
→ provider I/O
→ post-I/O authorization guard
→ validation и outcome
→ audit
```

Нужно выделить небольшой общий execution support внутри `agent_runtime`.

Общий слой должен владеть только механикой, реально одинаковой во всех runtime:

- последовательностью вызова;
- безопасным выходом из DB transaction перед внешним I/O;
- типовыми fail-closed outcomes;
- audit append;
- общей технической обработкой provider execution.

В bounded contexts должны остаться:

- domain contracts;
- выбор evidence;
- input assembly;
- domain authorization policy;
- преобразование model result;
- persistence и публикация результата.

Цель — убрать копирование, не создавая универсальную plugin-платформу или новый durable runtime lifecycle.

---

## 5. Разделить Safety classification, decision и projection

Основное проблемное место:

- `backend/app/safety_gate/service.py`

Сейчас рядом находятся разные по смыслу процессы:

- классификация model output;
- authoritative решение по физическому действию;
- построение presentation projection.

Их следует развести по ответственности, сохранив строгую связь через явные typed contracts.

Причина: classification evidence и action decision имеют разные authority и lifecycle. Их объединение затрудняет развитие Safety domain и повышает риск случайного смешения ролей.

---

## 6. Упростить HTTP boundary

Основные проблемные места:

- `backend/app/api/task_follow_up.py`
- `backend/app/api/companion.py`
- `backend/app/api/feed.py`
- `backend/app/api/history.py`

Нужно убрать повторение технической логики:

- canonical path identifiers;
- query validation;
- error envelopes;
- domain-error mapping;
- `Cache-Control`;
- одинаковые service/session wrappers;
- broad exception handling.

Общий HTTP support должен оставаться небольшим и прозрачным. Не следует строить отдельный framework поверх FastAPI.

Цель — сделать endpoints тонкими адаптерами между HTTP contracts и domain services.

---

## 7. Сделать application composition явной

Router, middleware, startup hooks и runtime bindings должны подключаться через одну понятную composition boundary.

Нужно устранить состояния, когда:

- модуль реализован, но не подключён;
- middleware активен для фичи с неопределённым lifecycle;
- experimental runtime случайно входит в production composition;
- документация, код и фактическое приложение показывают разные статусы.

Причина: явная composition уменьшает риск полумёртвого или случайно активированного кода и упрощает последующее включение новых компетенций.

---

## 8. Исправить масштабирование Plant History

Основные проблемные места:

- `backend/app/plant_history/service.py`
- `backend/app/plant_history/repository.py`

Текущая pagination загружает и сортирует полную историю в Python до применения cursor и limit.

Нужно перенести ограничение выборки и keyset pagination ближе к PostgreSQL, сохранив общий порядок элементов и стабильность cursor.

Цель — чтобы стоимость запроса зависела от размера страницы, а не от всей накопленной истории.

Отдельный materialized read model следует вводить только при доказанной необходимости.

---

## 9. Перевести agent context на allowlisted typed data

Основное проблемное место:

- `backend/app/access_admin/context_builders.py`

Сейчас shared context builder принимает произвольные nested mappings и пытается обнаруживать запрещённые данные через recursive filtering и наборы эвристик.

Нужно двигаться к модели, где каждый domain producer формирует разрешённый typed context DTO, а общий builder отвечает за scope, authorization и объединение уже безопасных records.

Redaction остаётся дополнительной защитой, но не основным способом определения допустимого контекста.

Причина: allowlist лучше масштабируется, уменьшает ложные срабатывания и делает provider boundary понятнее.

---

## 10. Перестроить тесты вокруг ответственности и рисков

Крупные тестовые файлы следует разделять вместе с production boundaries.

Основные проблемные места:

- `tests/backend/task_follow_up/test_runtime.py`
- `tests/backend/task_follow_up/test_domain_loop.py`
- `tests/backend/safety_gate/test_classification_persistence.py`
- Companion lifecycle и API suites

Цель:

- contract tests проверяют внешние contracts;
- domain tests проверяют transitions;
- integration tests проверяют DB, authorization, idempotency и concurrency;
- migration tests проверяют собственную revision и data preservation;
- полный regression gate не дублируется после каждого локального шага.

Не удалять security, safety и реальные race scenarios. Убирать следует дублирование и проверки случайных деталей реализации.

---

## 11. Отдельно привести в порядок tooling и repository maintenance

После product/runtime refactoring:

- разделить внутренности `mb-doctor.mjs` и `mb-lint.mjs`, сохранив их CLI entrypoints;
- архивировать старую часть растущего changelog;
- проверить крупные root build artifacts и удалить либо явно оформить их назначение;
- отделить generated DevRails tooling от product-code review и метрик.

Эти изменения не следует смешивать с production refactoring, поскольку у них другой риск и другой rollback boundary.

---

## Рекомендуемая последовательность

1. Repository hygiene и baseline.
2. Task Follow-Up service decomposition.
3. Стабилизация FT-013 и Companion decomposition.
4. Shared Agent Runtime execution support.
5. Safety service decomposition.
6. HTTP boundary cleanup и явная feature composition.
7. Plant History pagination.
8. Typed agent context.
9. Test architecture cleanup.
10. Tooling и repository maintenance.

Порядок может корректироваться по состоянию активной разработки, но cross-runtime abstractions не следует вводить раньше, чем станут понятны и устойчивы доменные границы.

---

## Критерии результата

Рефакторинг считается успешным, если:

- крупные services перестали владеть независимыми lifecycle;
- runtime duplication существенно уменьшилось;
- новые endpoints и agent competencies используют существующие простые boundaries;
- критические safety, authorization и idempotency гарантии сохранены;
- тесты стали легче локализовать и поддерживать;
- изменение одного bounded context не требует механических правок во множестве несвязанных модулей;
- итоговая архитектура стала проще без появления новых compatibility layers и преждевременных abstractions.
