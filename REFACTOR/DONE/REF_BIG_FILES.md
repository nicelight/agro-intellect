# Agro Intellect — аудит крупных файлов и кандидаты на рефакторинг

Статус: результат read-only аудита текущего рабочего дерева на 2026-07-29.
Документ не является нормативной спецификацией, task card или разрешением
начать реализацию.

Размеры ниже относятся к текущему рабочему дереву, включая незакоммиченные
изменения FT-013. Сам размер файла не считается достаточным основанием для
рефакторинга.

## Критерий однозначного кандидата

Файл или группа файлов попадает в основной список, если большой размер
сочетается хотя бы с одним сильным признаком:

- один class/module владеет несколькими самостоятельными lifecycle-командами;
- command, query, projection и serialization responsibilities смешаны;
- есть функции длиннее 100 строк с большим количеством ветвлений;
- один высокорисковый orchestration-каркас скопирован в несколько bounded
  contexts;
- изменение общего правила требует синхронно править несколько почти
  одинаковых реализаций;
- один tooling entrypoint содержит много независимых семейств проверок.

Оценки `CC≈N` ниже являются приближённой AST-оценкой ветвления, а не результатом
формального complexity gate.

## Однозначные production-кандидаты

### 1. `backend/app/task_follow_up/service.py`

Текущее состояние:

- 1227 строк;
- 31 функция/метод;
- 8 функций длиннее 50 строк;
- крупнейшие методы занимают 148–156 строк;
- максимальная приближённая сложность — `CC≈41`.

Один `TaskFollowUpService` сейчас владеет:

- созданием ordinary Task из classified MessageEnvelope;
- созданием ordinary Task из approved governance DecisionRecord;
- materialization и решением Approval;
- созданием action Task;
- завершением Task;
- созданием automatic follow-up;
- записью Outcome;
- чтением Task и Approval;
- четырьмя разными recovery/idempotency paths после `IntegrityError`;
- формированием timeline events.

Это уже god service: перечисленные команды имеют разные inputs, состояния,
ошибки и concurrency semantics.

Предпочтительная граница:

- отдельный handler для ordinary Task creation;
- отдельный approval/action lifecycle handler;
- отдельный completion/outcome handler;
- recovery/idempotency logic размещается рядом с владеющей командой, а не в
  общей нижней половине одного class;
- при необходимости оставить тонкий `TaskFollowUpService` facade, который
  только делегирует публичные операции.

Не менять в рамках structural refactor:

- транзакционные и serialization guards;
- canonical Task writer;
- public error codes;
- request fingerprints и idempotency;
- Safety Gate/human approval boundary;
- timeline event semantics.

Связанные тестовые файлы, которые следует разделять вместе с production-кодом:

- `tests/backend/task_follow_up/test_domain_loop.py`;
- `tests/backend/task_follow_up/test_runtime.py`;
- `tests/backend/api/test_ft012_task_follow_up_routes.py`.

### 2. `backend/app/companion_governance/service.py`

Текущее состояние:

- 1390 строк;
- 31 функция/метод;
- 8 функций длиннее 50 строк;
- `persist_companion_proposal` занимает 199 строк;
- `decide_companion_proposal` занимает 235 строк и имеет `CC≈40`.

Один `CompanionGovernanceService` одновременно владеет:

- persistence/supersede proposal;
- DecisionRecord и workflow effect;
- закрытием Issue;
- list query;
- detail query и aggregate validation;
- approved governance summary;
- timeline append;
- UI/Bus projection orchestration;
- HTTP-facing value serialization;
- cursor encoding/decoding.

Предпочтительная граница:

- command side: proposal persistence, proposal decision, issue close;
- query side: list/detail/approved-summary;
- projection/serialization helpers отдельно от transactional command handlers;
- timeline payload builders рядом с соответствующими командами либо в узком
  domain event builder;
- repository остаётся persistence boundary, а query service не получает write
  responsibilities.

Важное ограничение последовательности:

- `TASK-042-T3-FT-013-W2` сейчас имеет статус `in_progress`;
- `TASK-043-T3-FT-013-W3` имеет статус `planned`;
- не смешивать structural split с текущей W2 implementation;
- предпочтительно выполнить refactor после стабилизации FT-013 W2/W3;
- если operator захочет сделать split до W3, сначала требуется обычное
  перепланирование TASK-043 под новые paths и boundaries.

Связанные тестовые файлы:

- `tests/backend/companion_governance/test_proposal_lifecycle.py`;
- `tests/backend/companion_governance/test_proposal_projection.py`;
- `tests/backend/api/test_ft013_companion_read_routes.py`;
- `tests/backend/api/test_ft013_companion_decision_routes.py`;
- `tests/backend/companion_governance/test_decision_effects.py`.

### 3. `backend/app/safety_gate/service.py`

Текущее состояние:

- 878 строк;
- 32 функции/метода;
- два самостоятельных public services в одном файле;
- `SafetyGateClassificationService.classify` занимает 145 строк;
- `SafetyActionDecisionService.evaluate` занимает 89 строк;
- в том же файле находятся UI Feed projection builders и outcome factories.

Файл смешивает три ответственности:

1. provider-backed project-owned classification;
2. authoritative Safety Action Decision;
3. построение и проверку presentation projection.

Предпочтительная граница:

- classification service;
- action decision service;
- safety projection/value builder;
- общие маленькие value helpers допустимы только там, где они действительно
  принадлежат Safety domain.

Не объединять оба lifecycle в общий универсальный service: classification
evidence не является action decision authority.

Связанные тесты:

- `tests/backend/safety_gate/test_classification_persistence.py`;
- `tests/backend/safety_gate/test_action_routing.py`.

### 4. Общий Agent Runtime orchestration cluster

Файлы:

- `backend/app/agent_runtime/service.py` — 787 строк;
- `backend/app/vision_observation/service.py` — 743 строки;
- `backend/app/plant_state/runtime.py` — 650 строк;
- `backend/app/hydroponics_advisor/runtime.py` — 782 строки;
- `backend/app/task_follow_up/runtime.py` — 1022 строки.

Суммарно: 3984 строки.

Объективные признаки duplication:

- отдельные `invoke` implementations совпадают по нормализованной структуре
  примерно на 65–83%;
- audit methods совпадают на 92–100%;
- повторяются `context_denied`, `not_configured`, executor-result validation,
  UTC/event-ref helpers и transaction cleanup;
- пять реализаций вручную поддерживают один и тот же порядок
  `assemble -> release transaction -> provider I/O -> post-I/O guard ->
  envelope/outcome -> audit`;
- точные копии отдельных failure constructors встречаются в четырёх-пяти
  модулях.

Здесь нужен refactor группы, а не независимое дробление каждого файла.

Предпочтительный минимальный outcome:

- один небольшой shared execution support/kernel внутри `agent_runtime`;
- kernel владеет только механическим порядком provider invocation, типовыми
  fail-closed outcomes, audit append и общими result constructors;
- domain runtime передаёт typed callbacks/hooks для input assembly,
  post-I/O authorization guard и domain result conversion;
- domain contracts, input assemblers, evidence selection и persistence
  остаются в своих bounded contexts;
- сначала извлечь точные дубликаты и общий audit/outcome путь;
- не строить plugin framework, registry или новый durable runtime lifecycle.

Особенно важно сохранить:

- provider I/O вне DB transaction;
- post-I/O authorization/archive/revocation checks;
- provider-neutral unbound production behavior;
- test dependency injection;
- MessageEnvelope pending semantics;
- отсутствие автоматической публикации или физического действия.

## Однозначные tooling-кандидаты

### `scripts/mb-doctor.mjs`

- 2056 строк;
- 105 функций;
- 22 семейства `check*`;
- 39 глобальных constants.

Один CLI entrypoint проверяет Constitution, Backbone, Foundation, feature
clarification, task readiness, protocols, evidence, semantic completion,
dependency state и queue summary.

Fixed entrypoint `scripts/mb-doctor.mjs` нужно сохранить, но implementations
следует разнести по внутренним модулям: parsing, backbone/foundation, task
records, protocol/evidence и report output.

### `scripts/mb-lint.mjs`

- 1116 строк;
- 55 функций;
- 24 семейства `check*`;
- 33 глобальных constants.

Файл одновременно проверяет Memory Bank structure, frontmatter, links,
routers, Feature/PRD metadata, task schema/records, runtime boundaries и
Architecture Spine.

Fixed CLI entrypoint нужно сохранить, выделив внутренние validators по
стабильным concerns.

Оба tooling refactor следует проводить через owning DevRails/framework route
или после проверки, что следующий framework sync не перезапишет локальное
разбиение.

## Крупные тесты, которые нужно дробить

### `tests/backend/safety_gate/test_classification_persistence.py`

- 1094 строки;
- 20 tests;
- в одном файле смешаны contract/persistence behavior и несколько классов
  concurrency/lock-race scenarios.

Разделить минимум на classification persistence/idempotency и current-guard
concurrency.

### `tests/backend/task_follow_up/test_runtime.py`

- 1074 строки;
- 16 tests;
- смешаны input assembly, provider outcomes, concurrency, automatic follow-up
  и exact context behavior.

Разделить по runtime orchestration, provider failures/guards и context
assembly.

### `tests/backend/task_follow_up/test_domain_loop.py`

- 857 строк;
- 14 tests;
- покрывает ordinary tasks, approvals, completion, outcomes, idempotency и
  concurrent collisions.

Разделить в соответствии с будущими command-handler boundaries production
service.

Тестовый split сам по себе не должен менять coverage или удалять
security/safety/concurrency scenarios.

## Memory Bank maintenance

### `.memory-bank/changelog.md`

- 1396 строк;
- 84 dated sections;
- продолжает расти;
- значительно превышает рекомендуемую MBB границу около 500 строк.

Нужен архивный split:

- active changelog оставляет недавнее окно изменений;
- старые записи перемещаются в один или несколько датированных archive files;
- `.memory-bank/index.md` и archive router получают понятную навигацию;
- chronology и текст исторических записей не переписываются.

Это documentation maintenance, а не изменение product/spec authority.

## Repository cleanup, а не refactoring

Следующие tracked root files выглядят как чужие Orca build outputs:

- `index.js`;
- `index-DeYxQluZ.js`;
- `Settings-DF_ztqil.js`;
- `keybindings.js`.

Вместе они занимают 18 664 587 байт — около 72% текущего tracked tree. В
project source/config/docs не найдено входящих ссылок на эти filenames.

Их не нужно рефакторить вручную. После отдельного подтверждения назначения
следует:

- удалить их из repository, если это случайно закоммиченные artifacts;
- либо перенести в явно оформленное artifact/vendor location, если они
  действительно нужны;
- добавить соответствующее ignore/generation rule;
- не редактировать minified/generated output вручную.

Удаление не выполняется без отдельного operator request.

## Крупные файлы, которые пока не являются однозначными кандидатами

### `backend/app/agent_runtime/contracts.py` — 887 строк

Файл велик и содержит тяжёлую outcome matrix, но остаётся связным набором
versioned runtime contracts и имеет высокий fan-in. Split затронет много
imports и пока не доказано, что maintenance cost превышает churn. Допустим
локальный table-driven cleanup, но обязательный file split не доказан.

### `backend/app/plant_history/service.py` — 772 строки

Большая часть файла принадлежит одной read/projection задаче: history card,
timeline entries, cursor и redaction. Разделение возможно, но текущая
responsibility остаётся связной.

### `backend/app/photo_intake/service.py` — 703 строки

Upload, manifest, catalog и cursor относятся к одному Photo Intake boundary.
Нет достаточно сильного доказательства для немедленного split.

### `backend/app/plant_operations/service.py` — 655 строк

Check-in, manual measurement и freshness projection образуют один bounded
operations flow. Размер заметный, но god-service признаки слабее.

### Declarative models, migrations и task JSON

Большой размер SQLAlchemy models, Alembic revisions и schema-backed task cards
сам по себе не является основанием для split. Миграции являются историческими
deployment artifacts и не должны переписываться ради эстетики.

### `project_dossier_v2.md` — 3114 строк

Это большой upstream long-form dossier с оглавлением, а не runtime module.
После promotion решений он не является binding spec layer. Архивация или
декомпозиция может обсуждаться отдельно, но необходимость semantic split
текущим аудитом не доказана.

## Рекомендуемая последовательность

1. Завершить и стабилизировать текущую FT-013 W2/W3 работу либо явно
   перепланировать W3 до изменения Companion paths.
2. Отдельной task разделить `TaskFollowUpService`, сохранив contracts,
   transactions и behavior.
3. Отдельной task разделить `CompanionGovernanceService` на command/query/
   projection boundaries.
4. Отдельной cross-runtime task извлечь только доказанно общий execution
   support и убрать runtime duplication.
5. Отдельной task разделить Safety classification, decision и projection.
6. В тех же packages синхронно разделить крупные tests без потери coverage.
7. Tooling split выполнять отдельно от product/runtime refactoring.
8. Memory Bank changelog archive и root build-artifact cleanup выполнять
   отдельными maintenance changes.

Не объединять перечисленные пункты в один большой refactoring change: у них
разные риски, verification scope и rollback boundary.

## Общие acceptance guardrails для будущих refactoring tasks

- Никаких изменений public HTTP schemas, status codes или error grammar.
- Никаких изменений PostgreSQL schema/migrations без отдельного доказанного
  основания.
- Никакого ослабления authorization, Plant archive/revoke guards, Safety Gate,
  human approval, idempotency и redaction.
- Никакого нового shared mutable state.
- Никаких compatibility wrappers и legacy fallback layers.
- До split зафиксировать green focused baseline.
- После каждого coherent package запускать его focused tests и один итоговый
  deterministic regression gate согласно task tier.
- Оценивать успех по уменьшению responsibilities/copy-paste и сохранению
  behavior, а не по произвольному лимиту строк.
