# Agro Intellect — KISS simplification candidates

Статус: результат read-only архитектурного аудита, не нормативная
спецификация и не разрешение на реализацию.

Кандидаты расположены от самого важного к наименее важному по совокупности:

- ожидаемое снижение production complexity и coupling;
- снижение verification и maintenance burden;
- реалистичность риска, от которого защищает текущий механизм;
- последствия и восстановимость failure;
- объём решений оператора и изменений accepted requirements.

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

## 1. Упростить anti-corruption replay в Task Follow-Up

**Приоритет:** максимальный.  
**Confidence:** high.

### Текущий механизм

Exact retry проверяет не только реальную idempotency, но и согласованность
Task, classification, disposition, source refs и независимого commitment:

- [task-follow-up lifecycle](.memory-bank/states/task-follow-up-lifecycle.md);
- [runtime replay](backend/app/task_follow_up/runtime.py);
- [runtime dispositions migration](backend/migrations/versions/ft012_runtime_dispositions.py);
- [hostile runtime tests](tests/backend/task_follow_up/test_runtime.py).

Механизм включает отдельный expected Task-create fingerprint, write-once
PostgreSQL trigger, повторную загрузку source authority, повторную сборку
source universe и сравнение нескольких fingerprints.

### Какой failure предотвращается

Согласованная ручная подмена нескольких связанных записей так, чтобы обычные
FK, uniqueness и request fingerprint продолжали выглядеть корректно.

- Через публичный API: нет.
- Через штатный application path: практически нет.
- Через internal misuse: только при обходе service boundary.
- Через прямую порчу БД: да; hostile tests местами удаляют constraint/trigger.

Последствие — возврат неверного ordinary Task при retry. Это не создаёт
automated actuation или физического эффекта. Состояние восстанавливается
maintenance, исправлением записи или новым run.

### Цена

Высокая: production code, PL/pgSQL lifecycle, cross-table coupling, сложная
миграция, большая hostile-test matrix и высокая стоимость любого изменения
Task/provenance contracts.

### Рекомендация

Удалить:

- independent expected Task-create commitment;
- write-once trigger, существующий только для этого commitment;
- глубокую повторную проверку всей provenance graph на exact retry;
- tests, которые доказывают устойчивость к согласованной ручной порче БД.

Оставить:

- command/request fingerprint;
- unique natural keys;
- advisory lock и transaction;
- terminal disposition;
- current authorization/archive checks;
- Task FK и реальную race/crash idempotency;
- проверки provider output и write-boundary provenance.

**Residual risk:** оператор с прямым SQL-доступом может согласованно подменить
несколько authority rows. Это принимается как maintenance/security incident.

**Требуется:** изменение normative lifecycle/testing specs и отдельная
task decomposition до реализации.

## 2. Остановить hostile-probe ratchet в Companion read integrity

**Приоритет:** очень высокий.  
**Confidence:** high.

### Текущий механизм

Companion detail/read path загружает и проверяет целый retained graph, включая
точную ref grammar, state combinations и последовательность proposal records:

- [integrity validator](backend/app/companion_governance/integrity.py);
- [Companion service](backend/app/companion_governance/service.py);
- [read-route corruption tests](tests/backend/api/test_ft013_companion_read_routes.py);
- [red-verification history](.protocols/TASK-041-T3-FT-013-W1/red-verification.md).

Последовательные hostile probes уже породили проверки projection conflicts,
noncanonical refs, cross-Plant edges, caller provenance, impossible proposal
sequence и uppercase UUID в сохранённой записи.

### Какой failure предотвращается

GET не возвращает graph, который приложение само не умеет записать.

- Через публичный API: большая часть состояний недостижима.
- Через штатный application path: большая часть недостижима.
- Через internal misuse: частично.
- Через прямую порчу БД: да.

Для impossible sequence или нестандартного spelling сохранённого UUID
последствия — 500 либо плохой UI. Authority, authorization и physical safety не
изменяются. Восстановление — исправление записи или maintenance.

### Цена

Высокая и растущая: каждый новый probe соседнего поля создаёт invariant,
validator, дополнительные branches и новую regression matrix.

### Рекомендация

- Не добавлять bespoke validators только для impossible sequence или stored
  UUID spelling.
- Проверять untrusted provider input и Farm/Plant ownership на write boundary.
- Оставить DB constraints, FK, uniqueness и transaction для достижимых
  invariants.
- На read path проверять security-sensitive ownership и минимальную
  сериализуемость, но не доказывать полную непротиворечивость retained graph.
- Не считать red-verify finding самостоятельным product requirement.

**Residual risk:** ручная порча БД может привести к безопасному 500 или
maintenance incident.

**Требуется:** сначала зафиксировать operator threat-model decision; затем
сузить Companion testing/integrity specs.

## 3. Не позволять повреждённой UI projection блокировать authority write

**Приоритет:** высокий.  
**Confidence:** high.

### Текущий механизм

При supersede система требует точного совпадения ранее сохранённой UI Feed
projection с ожидаемым canonical event. Несовпадение presentation row отменяет
всю transaction:

- [projection implementation](backend/app/companion_governance/projections.py);
- [proposal service](backend/app/companion_governance/service.py);
- [projection corruption tests](tests/backend/companion_governance/test_proposal_projection.py).

### Какой failure предотвращается

Новая authority proposal не создаётся поверх вручную изменённой presentation
projection.

- Через публичный API: нет.
- Через штатный application path: нет при корректном producer.
- Через internal misuse: возможно.
- Через прямую порчу БД: да.

Без fail-closed поведения возможен временно неверный UI Feed. Projection
неавторитетна и может быть восстановлена из authority.

### Цена

Средне-высокая: authority зависит от полной presentation schema, каждое
изменение UI event расширяет transaction failure surface и тестовую матрицу.

### Рекомендация

- Сохранить атомарное создание authority и новой projection.
- При supersede пересобирать/перезаписывать derived projection из authority
  вместо exact-equality precondition.
- Оставить ограничения `visible_to_agents`, `consumable_by_agents=false`,
  authorization и Plant isolation.

**Residual risk:** при внутреннем defect UI projection может быть временно
исправлена перезаписью без отдельного сигнала о старой рассинхронизации. Это
допустимо при логировании.

**Требуется:** проверить формулировку atomic projection requirement; product
outcome менять не требуется.

## 4. Упростить durable introduction batch из восьми roster events

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

## 5. Централизовать проверку глобального Alembic head

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

## 6. Убрать domain-specific state matrices из общего Timeline writer

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

## 7. Вычислять provider `source_refs` из records

**Приоритет:** средне-низкий.  
**Confidence:** high.

### Текущий механизм

Несколько provider request contracts передают source references дважды:

- в каждом input record;
- отдельным outer `source_refs`, который должен точно совпасть с records.

Пример:

- [agent runtime adapter contract](.memory-bank/contracts/agent-runtime-adapter.md);
- [generic runtime contracts](backend/app/agent_runtime/contracts.py);
- [vision contracts](backend/app/vision_observation/contracts.py);
- [plant-state contract tests](tests/backend/plant_state/test_contracts.py).

### Какой failure предотвращается

Единственный trusted assembler создаёт две несовпадающие коллекции.

- Через публичный API: нет.
- Через штатный path: только coding defect assembler.
- Последствие: ранний 500.
- Output provenance всё равно отдельно проверяется.

### Цена

Средняя совокупно: дублированные fields, validators, serialization contracts и
tests в нескольких runtimes.

### Рекомендация

Request принимает только records, а `source_refs`:

- вычисляется как property; либо
- формируется непосредственно перед provider call из records.

Проверки того, что provider output ссылается только на разрешённые inputs,
должны сохраниться.

**Residual risk:** отсутствует отдельный сигнал о bug, при котором assembler
хотел передать refs, которых нет в records; такой intent сам по себе не является
полезным контрактом.

**Требуется:** согласованное изменение adapter spec и contracts до выбора
внешнего production provider.

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
- provider-output validation;
- secret/auth redaction;
- data-preservation migration tests;
- публичные HTTP response/error/cache contracts.

## Рекомендуемая последовательность решения

1. Оператор фиксирует threat model: ручная согласованная порча PostgreSQL —
   maintenance/security incident, не поддерживаемый application state.
2. Отдельно пересматриваются normative Task Follow-Up и Companion integrity
   requirements для кандидатов 1–3.
3. Оператор решает, менять ли product outcome introduction batch из кандидата
   4.
4. После spec decisions планируются независимые simplification tasks.
5. Кандидаты 5–8 выполняются как последующие ограниченные cleanup/workflow
   changes без смешивания с authority/security границами.
