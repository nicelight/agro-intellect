# Agro Intellect — KISS simplification candidates

Статус: результат read-only архитектурного аудита, не нормативная
спецификация и не разрешение на реализацию.

Кандидаты расположены от самого важного к наименее важному по совокупности:

- ожидаемое снижение production complexity и coupling;
- снижение verification и maintenance burden;
- реалистичность риска, от которого защищает текущий механизм;
- последствия и восстановимость failure;
- объём решений оператора и изменений accepted requirements.

Каждый нумерованный пункт ниже — один coherent refactoring package, который
удобно передать одному агенту как одну новую task. Поле **Исходный task scope**
указано, если package целиком относится к одной существующей indexed task. Это
ownership reference, а не разрешение повторно открыть `done` task.

## Рациональная граница threat model

Строгая защита остаётся обязательной для:

- authorization и Farm/Plant isolation;
- Safety Gate, human approval и запрета automated actuation;
- PostgreSQL authority и защиты от потери данных;
- secret/auth redaction;
- реальных concurrency и idempotency paths;
- недоверенных provider outputs;
- публичных HTTP contracts.

Согласованная ручная порча PostgreSQL администратором не должна считаться
штатным application state. Если приложение не может породить состояние через
публичный API или нормальный application path, а последствия ограничены
восстанавливаемым UI/diagnostic defect, предпочтительны maintenance и
исправление записи, а не новый production invariant.

## 1. Упростить весь Task Follow-Up runtime/replay package

**Статус:** закрыт 2026-07-27 в рамках
[TASK-040-T3-FT-012-W2](.memory-bank/tasks/TASK-040-T3-FT-012-W2.task.json).
**Приоритет:** максимальный.  
**Confidence:** high.
**Исходный task scope:** [TASK-040-T3-FT-012-W2](.memory-bank/tasks/TASK-040-T3-FT-012-W2.task.json).

### Текущий механизм

Один runtime package одновременно содержит две тесно связанные защиты:

- [task-follow-up lifecycle](.memory-bank/states/task-follow-up-lifecycle.md);
- [runtime contract](.memory-bank/contracts/task-follow-up-runtime.md);
- [runtime replay](backend/app/task_follow_up/runtime.py);
- [runtime dispositions migration](backend/migrations/versions/ft012_runtime_dispositions.py);
- [hostile runtime tests](tests/backend/task_follow_up/test_runtime.py);
- [runtime verification matrix](.memory-bank/testing/task-follow-up.md).

Первая часть — anti-corruption exact replay: expected Task-create fingerprint,
write-once PostgreSQL trigger, повторная загрузка source authority, сборка
source universe и сравнение нескольких fingerprints.

Вторая часть — отдельный runtime disposition ledger с собственной таблицей,
advisory locks, terminal result union, pre/post-I/O resolution, crash windows и
широкой race matrix. При этом public endpoint, worker и scheduler отсутствуют,
а production model binding остаётся unbound.

### Какой failure предотвращается

Package предотвращает два failure:

1. согласованную ручную подмену нескольких Task/classification/disposition rows
   так, чтобы обычные FK, uniqueness и request fingerprint выглядели корректно;
2. конкурентный или crash-retry запуск одного и того же internal runtime run.

- Через публичный API: нет.
- Через штатный production path: runtime caller пока не зарегистрирован.
- Через internal misuse: возможен повторный injected вызов.
- Через прямую порчу БД: да; hostile tests местами удаляют constraint/trigger
  и согласованно изменяют несколько authority rows.

Последствия — лишний model invocation, новый internal run или возврат неверного
ordinary Task после специально подготовленной DB corruption. Automated
actuation или физического эффекта нет. Canonical Task writer, authorization,
current guards и обычная Task idempotency продолжают предотвращать
duplicate/unauthorized Task. Восстановление — новый run, maintenance или
исправление записи.

### Цена

Очень высокая: отдельная DB lifecycle model до появления caller, PL/pgSQL
commitment lifecycle, advisory-lock protocol, replay state machine,
cross-table coupling и большая concurrency/corruption verification matrix.
Раздельный рефакторинг оставил бы временно противоречивую модель: упрощённый
replay поверх ledger, нормативно созданного именно для сложного replay.

### Рекомендация

В одной task:

- удалить independent expected Task-create commitment, его write-once trigger
  и глубокую проверку всей provenance graph на exact retry;
- отложить runtime disposition ledger до появления реального durable
  worker/scheduler, delivery identity и определённой retry/crash семантики;
- оставить линейный путь
  `invoke → post-I/O guard → classify → canonical Task writer`;
- убрать tests, доказывающие устойчивость к согласованной ручной порче БД;
- уже развёрнутые DB objects сначала перестать использовать, а физическое
  удаление выполнять только отдельной безопасной forward migration после
  проверки данных.

Оставить:

- command/request fingerprint;
- unique natural keys;
- transaction и реальные write-side serialization guards;
- ordinary dispatch disposition;
- current authorization/archive checks;
- Task FK и реальную write-side race/idempotency;
- проверки provider output и write-boundary provenance.

**Residual risk:** privileged SQL operator может согласованно подменить
authority rows; искусственный internal caller может повторно оплатить model
invocation. Это принимается как maintenance/security incident до появления
реального runtime delivery path.

**Требуется:** единое изменение normative lifecycle/runtime/testing specs и
одна новая task decomposition. В этой же task удалять DB objects только если
preflight докажет безопасность для deployment data; иначе оставить их
неиспользуемыми и не расширять scope отдельным cleanup.

## 2. Упростить Companion aggregate, projection и read integrity

**Статус:** закрыт 2026-07-27 в рамках
[TASK-044-T3-FT-013-W1](.memory-bank/tasks/TASK-044-T3-FT-013-W1.task.json).
**Приоритет:** очень высокий.  
**Confidence:** high.
**Исходный task scope:** [TASK-041-T3-FT-013-W1](.memory-bank/tasks/TASK-041-T3-FT-013-W1.task.json).

### Текущий механизм

Один Companion integrity graph содержит три взаимозависимых механизма:

- [integrity validator](backend/app/companion_governance/integrity.py);
- [Companion service](backend/app/companion_governance/service.py);
- [projection implementation](backend/app/companion_governance/projections.py);
- [Companion models](backend/app/companion_governance/models.py);
- [FT-013 migration](backend/migrations/versions/ft013_companion_governance_aggregate.py);
- [read-route corruption tests](tests/backend/api/test_ft013_companion_read_routes.py);
- [projection corruption tests](tests/backend/companion_governance/test_proposal_projection.py);
- [red-verification history](.protocols/TASK-041-T3-FT-013-W1/red-verification.md).

1. Detail/read path доказывает полную непротиворечивость retained graph,
   включая ref grammar, state combinations и proposal sequence.
2. Supersede требует exact equality ранее сохранённой UI projection и
   ожидаемого canonical event; presentation mismatch отменяет authority write.
3. Текущая связь хранится в двух направлениях:
   `proposal.attention_id` и `attention.current_proposal_id`, что требует
   cyclic/deferrable FK, pointer update и дополнительной graph validation.

Последовательные hostile probes уже породили проверки projection conflicts,
noncanonical refs, cross-Plant edges, caller provenance, impossible proposal
sequence, uppercase UUID и соседних duplicated pointers.

### Какой failure предотвращается

Package предотвращает возврат или развитие graph, который sole application
assembler сам не умеет записать:

- Через публичный API: большая часть состояний недостижима.
- Через штатный application path: большая часть недостижима.
- Через internal misuse: частично.
- Через прямую порчу БД: да.

При ослаблении текущего механизма возможны безопасный 500, временно неверный
UI Feed или необходимость rebuild projection. Authority, authorization и
physical safety не изменяются. Presentation rows и duplicated pointer
восстанавливаются из Proposal/Issue authority.

### Цена

Очень высокая: каждый новый probe соседнего поля создаёт invariant, validator,
branches и regression matrix; authority write зависит от полной presentation
schema; duplicated pointer добавляет cyclic schema dependency, version/lock
surface и ещё один consistency lifecycle.

### Рекомендация

В одной task:

- проверять untrusted provider input, Farm/Plant ownership и достижимые
  invariants на owning write boundary;
- оставить DB constraints, FK, one-pending uniqueness и transaction;
- на read path проверять security-sensitive ownership и минимальную
  сериализуемость, но не полную semantic эквивалентность retained graph;
- при supersede пересобирать/перезаписывать derived projection из authority
  вместо exact-equality precondition;
- оставить `proposal.attention_id`, а current Proposal определять как
  единственную pending row;
- при необходимости продолжать возвращать вычисленный `current_proposal_id` в
  прежнем HTTP response;
- не добавлять validators только ради impossible sequence, stored UUID
  spelling или согласованной direct-DB corruption;
- если schema уже развёрнута, reverse pointer сначала перестать считать
  authority и удалять только безопасной forward migration.

Оставить атомарное создание authority и новой projection, ограничения
`visible_to_agents`, `consumable_by_agents=false`, authorization, Plant
isolation и безопасную сериализацию.

**Residual risk:** ручная порча DB/projection может привести к 500 или
maintenance/rebuild; current Proposal требует индексированного query.

**Требуется:** сначала зафиксировать operator threat-model/schema decision,
затем одной task сузить Companion domain/state/testing specs, aggregate,
projection и integrity tests. Публичный response contract можно сохранить.

## 3. Вернуть production model composition в нормативно unbound состояние

**Статус:** закрыт 2026-07-28 в рамках
[TASK-045-T3-FT-007-W3](.memory-bank/tasks/TASK-045-T3-FT-007-W3.task.json).
**Приоритет:** высокий.  
**Confidence:** high.
**Исходный task scope:** [TASK-031-T3-FT-007-W2](.memory-bank/tasks/TASK-031-T3-FT-007-W2.task.json).

### Текущий механизм

Активный provider contract не выбирает provider, model, endpoint, credentials
или egress policy и запрещает изобретать production configuration до решения
оператора:

- [provider profile contract](.memory-bank/contracts/agent-model-provider-profiles.md);
- [production provider composition](backend/app/agent_runtime/providers.py);
- [runtime configuration](backend/app/config.py);
- [provider composition tests](tests/backend/agent_runtime/test_ft007_roster_providers.py).

Несмотря на это, implementation уже содержит DeepSeek, Gemini и ChatGPT OAuth
factories, native imports, provider-specific environment bindings и production
composition. Production application caller для этого composition не найден.

### Какой failure предотвращается

Будущий deployment сможет выбрать один из нескольких providers без нового
adapter slice.

- Через публичный API: сейчас недостижимо.
- Через штатный production path: binding отсутствует.
- Через internal misuse/configuration: возможно случайно активировать
  неутверждённый egress.
- Authority/safety consequence: прямой пользы сейчас нет; ошибочное включение
  увеличивает credential и data-egress surface.

### Цена

Средне-высокая: преждевременные adapters, configuration grammar, dependency
coupling и tests для нескольких вариантов, ни один из которых не принят
deployment contract.

### Рекомендация

- Удалить или отложить provider-specific production factories и неактивные
  config fields.
- Оставить provider-neutral `ModelExecutor`, strict result validation, test DI
  и fail-closed unbound production result.
- После выбора оператора реализовать один adapter под реальный endpoint,
  authentication и egress policy.

**Residual risk:** после выбора provider потребуется отдельный небольшой
implementation slice. До этого реальный product outcome не теряется.

**Требуется:** implementation alignment с уже активным contract; выбор
конкретного provider остаётся решением оператора.

## 4. Упростить durable introduction batch из восьми roster events

**Статус:** закрыт 2026-07-29 в рамках
[TASK-046-T3-FT-008-W3](.memory-bank/tasks/TASK-046-T3-FT-008-W3.task.json).
**Приоритет:** высокий, но зависит от решения оператора.  
**Confidence:** high.

### Текущий механизм

После создания Plant система создаёт строго восемь introduction events,
детерминированные UUID, batch state и content digests, а при startup сканирует
Plants и выполняет reconciliation:

- [roster bootstrap contract](.memory-bank/contracts/agent-roster-bootstrap.md);
- [bootstrap implementation](backend/app/agent_runtime/bootstrap.py);
- [introduction sink](backend/app/agent_chat/introduction_sink.py);
- [reconciliation tests](tests/backend/agent_chat/test_ft008_reconciliation.py).

### Какой failure предотвращается

После crash или частичного внутреннего сбоя пользователь не теряет introduction
cards агентов.

- Через публичный API: возможен запуск Plant creation.
- Через штатный application path: частичный сбой возможен.
- Последствие: отсутствующие или неполные introduction cards.
- Authority/safety consequence: отсутствует.
- Восстановление: повторная генерация, lazy repair или повторный вход.

### Цена

Высокая для presentation-only outcome: batch lifecycle, восемь durable events
на Plant, digest contract, startup scan, reconciliation и большая test matrix.

### Рекомендация

Предпочтительный новый outcome:

- UI строит roster introduction из canonical static roster; либо
- отсутствующие presentation rows лениво upsert-ятся при первом открытии Feed.

Тогда можно удалить batch digest, startup reconciliation и строгую
all-eight-or-nothing семантику. Запрет agent consumption должен сохраниться.

**Residual risk:** после локального сбоя introduction cards могут появиться
только после следующего открытия UI/retry.

**Требуется:** явное решение оператора и изменение принятого REQ-013/контракта.
Текущая implementation в основном соответствует принятой спецификации.

## 5. Упростить provider provenance и `source_refs` contracts

**Приоритет:** средне-высокий.
**Confidence:** very high.

### Текущий механизм

Один provider-boundary package содержит две формы дублирования provenance:

1. Vision provider result возвращает authority-bearing `source_refs`, после
   чего несколько слоёв проверяют foreign, duplicate, reordered и
   noncanonical combinations.
2. Несколько provider request contracts передают одни source references и в
   input records, и в отдельном outer `source_refs`, после чего trusted
   assembler доказывает их exact equality.

- [vision runtime contract](.memory-bank/contracts/vision-observation-runtime.md);
- [vision result contracts](backend/app/vision_observation/contracts.py);
- [vision service](backend/app/vision_observation/service.py);
- [Plant State promotion](backend/app/plant_state/service.py);
- [vision contract tests](tests/backend/vision_observation/test_contracts.py);
- [agent runtime adapter contract](.memory-bank/contracts/agent-runtime-adapter.md);
- [generic runtime contracts](backend/app/agent_runtime/contracts.py);
- [plant-state contract tests](tests/backend/plant_state/test_contracts.py).

При этом текущий invocation уже относится ровно к одному Photo, которое
application проверило по ActorContext, Plant, path containment, size и hash.
Provider является недоверенным интерпретатором bytes, но не должен выбирать
identity authoritative evidence.

### Какой failure предотвращается

Provider возвращает observation с foreign/duplicated Photo ref либо trusted
assembler создаёт две несовпадающие request collections.

- Через публичный API: напрямую нет.
- Через реальный provider output: да только для result refs.
- Через штатный request path: mismatch возможен только как coding defect
  assembler.
- Consequence: неверная provenance observation; automated actuation всё равно
  запрещено. Для request mismatch consequence — ранний 500.
- Восстановление: отклонение результата и новый run.

Failure реалистичен, но текущий механизм защищает неверный boundary: authority
identity сначала отдаётся provider, а затем дорого проверяется.

### Цена

Средне-высокая: duplicated request fields, result grammar, canonicalization,
cross-layer validators, serialization coupling и combinatorial test matrices
для identities, которые application уже знает.

### Рекомендация

- Удалить `source_refs` из Vision provider result либо игнорировать это поле.
- После успешной проверки model content trusted assembler добавляет ровно
  `photo:<photo_id>` из invocation context.
- В provider requests оставить input records; outer `source_refs` вычислять как
  property или непосредственно перед вызовом provider.
- Для contracts, где provider действительно возвращает несколько citations,
  проверять их только против authoritative refs, вычисленных из input records.
- Сохранить strict validation model-produced content, message/run binding,
  Photo byte integrity, same-Plant checks и human promotion.

**Residual risk:** single-photo invocation не выражает provider-selected
дополнительный источник, а duplicated request intent больше не валидируется
отдельно. Оба поведения не являются принятым outcome; при multi-photo input
authoritative ref list по-прежнему формирует application.

**Требуется:** одна cross-runtime contract task для request/result models,
assemblers и tests. Authorization и safety requirements не меняются.

## 6. Централизовать проверку глобального Alembic head

**Приоритет:** средне-высокий.  
**Confidence:** high.

### Текущий механизм

Старые feature-specific migration tests знают имя текущего глобального head.
Каждая новая migration требует механически менять множество несвязанных тестов.
Целостность цепочки уже проверяет:

- [central database contract test](tests/backend/test_foundation_database_contract.py).

Exact-head assertions также распределены по feature migration suites.

### Какой failure предотвращается

Незамеченная Alembic branch или неправильный `down_revision`.

Это реальный deployment risk с потенциально серьёзным последствием, но
дублированные assertions не дают пропорционального дополнительного покрытия.

### Цена

Постоянный verification fan-out: каждая новая migration меняет исторические
тесты, создаёт шум diff и риск механических ошибок.

### Рекомендация

- Оставить одну центральную проверку единственного head и всей ancestry chain.
- Feature tests должны проверять собственную revision, parent, schema/data
  transition и downgrade, но не имя будущего глобального head.
- Сохранить upgrade/downgrade и data-preservation tests.

**Residual risk:** отсутствует существенное ослабление, если центральный gate
остаётся обязательным.

**Требуется:** implementation/testing cleanup; product/spec decision не нужен,
если testing spec не требует fan-out явно. FT-013 testing wording следует
скорректировать.

## 7. Убрать domain-specific state matrices из общего Timeline writer

**Приоритет:** средний.  
**Confidence:** high.

### Текущий механизм

Общий JSONL writer повторно знает payload/state invariants Companion, Task
Follow-Up и Agent Runtime:

- [timeline writer](backend/app/timeline/writer.py).

Те же данные уже формируются доверенными typed producers и проверяются в их
domain/service boundary.

### Какой failure предотвращается

Внутренний producer записывает malformed audit payload.

- Через публичный API напрямую: нет.
- Через штатный path: только при coding defect.
- Последствие: неточная timeline/diagnostics.
- Authority/safety consequence: отсутствует.
- Восстановление: повторный export, maintenance или исправление producer.

### Цена

Высокая cross-module coupling: shared writer должен изменяться при каждом
domain evolution и может блокировать authority operation из-за presentation/
audit schema drift.

### Рекомендация

Оставить в writer:

- общий event envelope;
- event type/source registry;
- Farm/Plant/source identifiers;
- sanitizer и secret/auth redaction;
- append/error handling.

Domain payload/state validation оставить producer tests и typed constructors.

**Residual risk:** coding defect producer может записать структурно допустимый,
но семантически неточный audit event.

**Требуется:** локальное архитектурное изменение и корректировка timeline tests;
traceability outcome сохраняется.

## 8. Сократить перекрывающиеся verification matrices

**Приоритет:** наименьший из отобранных, но с постоянной стоимостью.  
**Confidence:** medium-high.

### Текущий механизм

После каждого локального ремонта повторяются focused tests, широкая feature
regression, migration suite, full deterministic suite и исторические hostile
probes. В T3 `/verify` и `/red-verify` частично повторяют одинаковое runtime
покрытие.

### Какой failure предотвращается

Локальный fix незаметно ломает соседний boundary.

Failure реалистичен, однако ценность многократного повторения неизменных матриц
ниже стоимости. Семантическая независимость verifier остаётся полезной.

### Цена

Высокая по времени и review throughput; hostile probes становятся фактическим
источником новых requirements и расширяют последующую regression surface.

### Рекомендация

- На repair attempt запускать changed-boundary tests и regression конкретного
  finding.
- Исторический probe, ставший обязательным, хранить как один canonical test, а
  не дублировать отдельным verifier script.
- Полный deterministic suite запускать один раз перед task closure или на wave
  boundary.
- Сохранить независимый semantic `/red-verify` для T3, но отделить оценку
  accepted requirements от поиска произвольной DB corruption.

**Residual risk:** соседняя регрессия может обнаружиться только на итоговом
полном прогоне, а не после каждого промежуточного repair.

**Требуется:** решение владельца workflow/testing policy. Это не должно
ослаблять обязательные T3 closure gates без явного изменения процесса.

## Не упрощать в рамках этих кандидатов

Даже если реализация выглядит сложной, не сокращать:

- post-I/O authorization rechecks и archive/revoke race protection;
- Farm/Plant ownership checks для входных evidence;
- Safety Gate classification evidence и human approval;
- PostgreSQL transactions/constraints для реальных lifecycle races;
- request/run/message idempotency;
- provider-output validation для model-produced content;
- secret/auth redaction;
- data-preservation migration tests;
- публичные HTTP response/error/cache contracts.

## Рекомендуемая последовательность решения

1. Оператор фиксирует threat model: ручная согласованная порча PostgreSQL —
   maintenance/security incident, не поддерживаемый application state.
2. Оператор одновременно подтверждает Companion schema decision из кандидата
   2; после этого кандидаты 1 и 2 планируются как две независимые T3
   refactoring tasks.
3. Кандидат 3 выполняется отдельной task как alignment implementation с уже
   активным unbound provider contract.
4. Оператор отдельно решает, менять ли introduction outcome из кандидата 4;
   при принятии весь bootstrap/persistence/reconciliation package меняется
   одной task.
5. Кандидат 5 выполняется одной cross-runtime provider-contract task с
   сохранением Photo integrity и model-content validation.
6. Кандидаты 6 и 7 выполняются как две независимые low-coupling cleanup tasks.
7. Кандидат 8 остаётся отдельным workflow-policy change и не смешивается с
   product/runtime refactoring.
