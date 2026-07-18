# Аудит `/autopilot` workflow

Дата аудита: 2026-07-18  
Режим: read-only анализ Memory Bank, skills, task schema, `mb-lint`, `mb-doctor`, task records и operational artifacts.

## Краткий итог

Memory Bank хорошо проработан на уровне структуры, canonical SDD routing и traceability, но `/autopilot` пока нельзя считать полностью детерминированным и restart-safe.

Текущая очередь формально проходит механические gates, однако в аварийных и повторных прогонах возможны:

- зависшие задачи в `in_progress`;
- применение устаревшего review или verification evidence;
- ложный PASS из-за исторического успешного verdict;
- неоднозначное восстановление failure budget;
- разные lifecycle-решения в зависимости от того, какой фрагмент противоречащих друг другу инструкций применит агент.

Перед длительным unattended-прогоном рекомендуется устранить findings P1-1 — P1-6.

## Контекст проекта

Agro Intellect — local-first Farm workspace для безопасной работы с растениями: Accounts/RBAC, несколько Plants, check-ins, фото, pH/EC, история, задачи и AI-assisted workflows.

Ключевой архитектурный принцип — не позволять model output, UI Feed, audit или Companion governance становиться runtime authority. Физические действия остаются fail-closed и требуют Safety Gate и human approval.

Основные источники:

- `.memory-bank/product.md`
- `.memory-bank/architecture/system-architecture.md`
- `.memory-bank/constitution.md`
- `.memory-bank/spec-backbone.md`
- `.memory-bank/spec-index.md`

## Проверенная поверхность

Основной workflow:

- `.agents/skills/autopilot/SKILL.md`
- `.memory-bank/workflows/autonomy-policy.md`
- `.memory-bank/workflows/execute-loop.md`
- `.memory-bank/workflows/tier-policy.md`
- `.memory-bank/workflows/mb-sync.md`

Связанные skills:

- `mb`
- `mb-doctor`
- `execute`
- `verify`
- `red-verify`
- `mb-sync`
- `review-tasks-plan`
- `prd-to-tasks`
- `mb-harness`

Executable validation surface:

- `.memory-bank/schemas/task.schema.json`
- `.memory-bank/tasks/index.json`
- `scripts/mb-lint.mjs`
- `scripts/mb-doctor.mjs`
- `.protocols/AUTONOMOUS-RUN/status.md`
- `.tasks/TASK-MB-REVIEW-TASKS-PLAN/`

## Текущее техническое состояние

- 44/44 indexed task records проходят JSON Schema Draft 2020-12.
- `node scripts/mb-lint.mjs` — PASS.
- `node scripts/mb-doctor.mjs --strict --json` — PASS: 0 errors, 11 warnings.
- Все 11 warnings относятся к отсутствующим exact `HUMAN_CHECKPOINT: done` в исторических T3 tasks и трактуются executable doctor как advisory.
- `git diff --check` — PASS.
- Queue snapshot во время аудита: 34 `done`, 1 `ready`, 9 `planned`, 0 `in_progress`, 0 `blocked`, 0 `failed`.
- Ближайшая runnable task: `TASK-034-T3-FT-009-W1`.
- Проверенные skills в `.agents/skills/` и `.claude/skills/` идентичны.
- Отдельных automated tests для `mb-lint`, `mb-doctor` и scheduler edge cases в репозитории не найдено.

## Findings

### P1-1 — Governing policy противоречит executable workflow

`/autopilot` начинается с policy override, согласно которому T2/T3 protocol, verification, semantic review, checkpoint, doctor и sync являются advisory и могут быть waived scheduler/owner.

Ниже тот же skill снова объявляет обязательными для closure:

- full protocol;
- `/verify PASS`;
- T3 `/red-verify semantic-pass`;
- exact `HUMAN_CHECKPOINT: done`;
- strict doctor и wave-boundary sync.

Это противоречит `.memory-bank/workflows/tier-policy.md`, где те же process gates явно не являются universal closure prerequisites.

Executable реализация тоже расходится:

- `scripts/mb-doctor.mjs` трактует отсутствие T2/T3 protocol/verify/red/checkpoint evidence как warnings;
- `scripts/mb-lint.mjs` по-прежнему создаёт hard errors, если у `T2/T3 in_progress|done|failed` нет полного protocol file set или PASS/FAIL evidence;
- doctor всегда сначала запускает lint, поэтому часть заявленных waivers фактически невозможна.

Риск: одинаковый task state может быть закрыт одним агентом и отклонён другим в зависимости от выбранного фрагмента инструкций.

Evidence:

- `.agents/skills/autopilot/SKILL.md:13`
- `.agents/skills/autopilot/SKILL.md:91`
- `.agents/skills/autopilot/SKILL.md:138`
- `.memory-bank/workflows/tier-policy.md:17`
- `scripts/mb-doctor.mjs:787`
- `scripts/mb-lint.mjs:964`

### P1-2 — Нет recovery path для прерванного `in_progress`

Scheduler сначала записывает `ready -> in_progress`, а затем запускает внешнюю `/execute` session.

Если процесс завершится после status write, но до появления handoff/evidence:

- задача останется `in_progress`;
- selection rule выбирает только `ready`;
- `/autopilot` не определяет, нужно ли повторить `/execute`, продолжить с `/verify`, вернуть task в `ready` или завершить её как failed;
- `mb-doctor` считает наличие любого `in_progress` достаточным, чтобы не возвращать `TASK_QUEUE_DEADLOCK`.

Получается состояние, в котором doctor может вернуть PASS, но scheduler не имеет допустимого следующего transition.

Evidence:

- `.agents/skills/autopilot/SKILL.md:126`
- `.agents/skills/autopilot/SKILL.md:142`
- `scripts/mb-doctor.mjs:1258`

### P1-3 — Failure budget не реализован как восстанавливаемая state machine

`.memory-bank/workflows/autonomy-policy.md` задаёт:

- `max_retries_per_task: 2`;
- `max_consecutive_failures: 3`;
- `max_open_blockers: 3`.

При этом task loop `/autopilot` говорит, что любой functional FAIL или semantic-fail должен немедленно привести к:

- `status: failed`;
- bug record;
- follow-up task;
- failure-budget impact.

Реальные прошлые прогоны работали иначе: после первого FAIL task оставалась `in_progress`, scheduler разрешал bounded retry, а затем повторял verification.

Retry count, consecutive failures и open blockers хранятся только в prose `status.md`, а не в schema-backed current-run state. Новая сессия не может надёжно восстановить остаток budget.

Evidence:

- `.memory-bank/workflows/autonomy-policy.md:45`
- `.agents/skills/autopilot/SKILL.md:154`
- `.protocols/AUTONOMOUS-RUN/status.md:29`

### P1-4 — Historical PASS может маскировать более новый FAIL

`mb-lint` и `mb-doctor` ищут любой подходящий marker среди всех task artifacts:

- любой `VERDICT: PASS` для functional closure;
- любой `SEMANTIC_VERDICT: semantic-pass` для T3 red verification;
- любой `HUMAN_CHECKPOINT: done`;
- любой feature-doc `SEMANTIC_VERDICT: semantic-pass` для T2 feature completion.

Нет понятия:

- execution attempt;
- evidence generation/revision;
- superseded verdict;
- closure decision, ссылающегося на конкретные current reports;
- task planning fingerprint, относительно которого evidence было собрано.

Следствия:

- старый PASS может скрыть более новый FAIL;
- старый checkpoint может быть принят после reopen/retry;
- старый feature semantic-pass может покрыть добавленную позже task.

Evidence:

- `scripts/mb-lint.mjs:948`
- `scripts/mb-doctor.mjs:817`
- `scripts/mb-doctor.mjs:1398`
- `scripts/mb-doctor.mjs:1591`

### P1-5 — Freshness `/review-tasks-plan` не проверяется детерминированно

`/autopilot` требует latest `APPROVE` для каждой task-linked product feature, но:

- review report не содержит fingerprint просмотренной planning surface;
- нет schema-backed manifest: feature, plan, task ids, hashes, verdict, reviewed_at;
- doctor намеренно не проверяет semantic review applicability/freshness;
- выбор «latest» зависит от имени файла, mtime и интерпретации агента;
- изменение task card, spec, requirements или dependency не инвалидирует report автоматически.

Текущий worktree демонстрирует этот риск: `TASK-040-T3-FT-012-W2.task.json` изменён после сохранённого FT-012 `VERDICT: APPROVE`, но strict doctor продолжает проходить.

Кроме того, изменены смысловые constraints/invariants некоторых уже `done` records, хотя `/prd-to-tasks` требует сохранять semantic goal и acceptance basis terminal tasks.

Evidence:

- `.agents/skills/review-tasks-plan/SKILL.md:174`
- `.agents/skills/prd-to-tasks/SKILL.md:133`
- `.tasks/TASK-MB-REVIEW-TASKS-PLAN/TASK-MB-REVIEW-TASKS-PLAN-S-TASKS-FT-012-final-report-docs-01.md:10`
- `.memory-bank/tasks/TASK-040-T3-FT-012-W2.task.json:103`

### P1-6 — Operational `status.md` не имеет однозначного current run

`.protocols/AUTONOMOUS-RUN/status.md` одновременно содержит:

- `SUCCESS` для очереди из 34 tasks;
- `HALT_DEPENDENCY_DEADLOCK` для очереди из 32 tasks;
- `HALT_FAILURE_BUDGET` и snapshot очереди из 30 tasks;
- historical и current sections без machine-readable active-run marker.

Текущий authoritative task index уже содержит 44 tasks.

`/autopilot` говорит создать `status.md`, только если файла ещё нет, но не определяет:

- reset;
- archive;
- run id;
- current snapshot marker;
- ownership transfer;
- resume semantics.

Риск: новый run может принять historical terminal state или blocking section за текущий либо проигнорировать реально актуальный blocker.

Evidence:

- `.agents/skills/autopilot/SKILL.md:70`
- `.protocols/AUTONOMOUS-RUN/status.md:3`
- `.protocols/AUTONOMOUS-RUN/status.md:55`
- `.protocols/AUTONOMOUS-RUN/status.md:116`
- `.protocols/AUTONOMOUS-RUN/status.md:131`

### P2-1 — `/verify` и `/red-verify` объединены в одну fresh session

Concrete Codex/Claude command предлагает одному worker выполнить `/verify`, а затем `/red-verify` в той же сессии.

Это ослабляет adversarial independence: red reviewer уже видел reasoning и выводы functional verifier и легче anchor-ится на PASS.

Для T3 нужны отдельные fresh sessions:

1. implementation;
2. functional verification;
3. adversarial semantic verification.

Evidence:

- `.agents/skills/autopilot/SKILL.md:210`
- `.agents/skills/autopilot/SKILL.md:217`
- `.agents/skills/red-verify/SKILL.md:18`

### P2-2 — Follow-up path обходит planning gates

После FAIL autopilot предписывает создать follow-up task и подобрать её в том же run.

Но новая task меняет planning surface и должна пройти:

1. `/prd-to-tasks FT-<NNN>` или controlled reconciliation;
2. `/review-tasks-plan FT-<NNN>`;
3. applicable strict doctor;
4. только затем promotion/selection.

Текущий loop не определяет этот порядок и одновременно заявляет, что `/autopilot` не создаёт task queue.

Дополнительный риск: если follow-up будет зависеть через `depends_on` от failed task, она никогда не станет `ready`, поскольку scheduler требует все dependencies в `done`.

Evidence:

- `.agents/skills/autopilot/SKILL.md:17`
- `.agents/skills/autopilot/SKILL.md:158`
- `.agents/skills/autopilot/SKILL.md:198`
- `.agents/skills/verify/SKILL.md:215`

### P2-3 — `wave` неоднозначна в глобальной queue

`wave` входит в task identity, но значения `W1`, `W2`, `W3` повторяются для каждой feature.

В текущем DAG встречается ситуация, когда task `W1` одной feature зависит от task `W2` предыдущей feature. Поэтому выражение «после завершения текущей wave» нельзя однозначно интерпретировать как глобальную группу по `task.wave`.

Нужно определить wave boundary как одно из:

- `(feature, wave)`;
- dependency frontier;
- explicit scheduler batch id.

Без этого разные scheduler sessions могут запускать `/mb-sync` в разные моменты.

Evidence:

- `.agents/skills/autopilot/SKILL.md:182`
- `.memory-bank/tasks/TASK-035-T3-FT-009-W2.task.json`
- `.memory-bank/tasks/TASK-036-T3-FT-010-W1.task.json`

### P2-4 — Schema и scheduler state недостаточны для deterministic ownership

Task schema не имеет canonical structured representation для:

- closure decision;
- selected evidence reports;
- execution attempt;
- retry counters;
- waivers/residual risk;
- active blocker;
- blocking review;
- unresolved semantic concern;
- reviewed planning fingerprint.

`verify` разрешает произвольные objects через `additionalProperties: true`, поэтому разные runs записывают ownership и closure metadata в несовместимых формах.

Одновременно selection rule требует учитывать blockers, review rejects, bugs и semantic concerns, но schema не определяет, где именно scheduler обязан их искать.

Evidence:

- `.memory-bank/schemas/task.schema.json:100`
- `.agents/skills/autopilot/SKILL.md:118`

### P2-5 — JSON Schema и `mb-lint` расходятся для gate objects

В `task.schema.json` у `gates.items` отсутствует `additionalProperties: false`, а `name`/`command` не обязаны быть непустыми.

`mb-lint`, напротив:

- запрещает любые дополнительные keys;
- требует непустые `name` и `command`.

Следовательно, task record может пройти canonical JSON Schema, но упасть на lint.

Evidence:

- `.memory-bank/schemas/task.schema.json:78`
- `scripts/mb-lint.mjs:683`

### P2-6 — Final task-plan review запускается без необходимости

`execute-loop.md` говорит повторять `/review-tasks-plan` после wave только при изменении planning surface. Status/evidence-only closure не должна запускать новый review.

`/autopilot` при полностью закрытой queue требует final review для каждой task-linked feature независимо от наличия planning changes.

Это не ломает correctness напрямую, но:

- расходует fresh reviewer sessions;
- создаёт лишние competing review reports;
- усложняет определение «latest»;
- может породить ложный REJECT на post-execution surface.

Evidence:

- `.memory-bank/workflows/execute-loop.md:52`
- `.agents/skills/autopilot/SKILL.md:131`

### P3-1 — Report numbering не определён для retries

Concrete implementation prompt всегда указывает `...final-report-code-01.md`.

При retry непонятно, должен worker:

- перезаписать `-01`;
- создать `-02`;
- использовать другой stage id.

Исторические artifacts используют `-02`, но это сложившаяся практика, не формализованный scheduler rule.

Evidence:

- `.agents/skills/autopilot/SKILL.md:214`
- `.tasks/TASK-028-T3-FT-007-W1/`
- `.tasks/TASK-033-T3-FT-008-W2/`

### P3-2 — Harness commands недостаточно portable

Concrete commands pin:

- Codex model `gpt-5.2-high`;
- Claude model `opus`.

В проекте отсутствует `.codex/config.toml`, а Claude CLI в текущем окружении не найден. Codex CLI установлен.

Это не blocker для текущего Codex run, но scheduler должен выбирать доступный configured harness, а не считать оба примера гарантированно рабочими.

Evidence:

- `.agents/skills/autopilot/SKILL.md:210`
- `.agents/skills/mb-harness/SKILL.md`

### P3-3 — Нет fixture-tests для scheduler toolchain

В репозитории не найдены automated tests для:

- `scripts/mb-lint.mjs`;
- `scripts/mb-doctor.mjs`;
- queue promotion/deadlock detection;
- stale evidence;
- stale task-plan review;
- crash recovery;
- retry exhaustion;
- follow-up insertion;
- advisory waiver behavior.

С учётом роли этих scripts как autonomous readiness gate отсутствие тестов создаёт высокий regression risk при следующих изменениях Memory Bank framework.

## Что уже сделано хорошо

- Task records действительно schema-backed и индексированы.
- Foundation gate и product dependencies детерминированно проверяются.
- `FT-000/W0`, task ID, tier, feature и wave segments согласованы.
- Canonical SDD specs отделены от feature composition и напрямую линкуются из T2/T3 task cards.
- Ownership между `/execute`, `/verify`, `/red-verify`, scheduler и `/mb-sync` сформулирован явно, хотя process-gate строгость пока расходится.
- `.agents` и `.claude` copies синхронизированы.
- Текущий Memory Bank проходит schema/lint/doctor/link checks.
- Default sequential execution снижает shared-worktree и overlapping-file risks.

## Рекомендуемый порядок исправлений

### Шаг 1 — Свести advisory/hard policy к одному контракту

Выбрать одну governing модель и синхронизировать:

- `AGENTS.md`;
- Constitution;
- `tier-policy.md`;
- `autonomy-policy.md`;
- `autopilot`;
- `execute`;
- `verify`;
- `red-verify`;
- `mb-sync`;
- `mb-doctor` skill;
- `mb-lint` и `mb-doctor` scripts.

При текущей Constitution наиболее прямой вариант:

- process-only T2/T3 gaps — warning;
- product/spec/safety/scope/authorization violations — hard blocker;
- конкретный gate становится hard только после explicit owner/run decision.

### Шаг 2 — Ввести минимальный structured current-run state

Минимальные поля:

- `run_id`;
- `started_at`;
- `queue_fingerprint`;
- `active_task`;
- `active_stage`;
- `attempt`;
- retry/failure counters;
- review coverage;
- accepted waivers;
- terminal state.

Historical run state следует архивировать отдельно, не накапливать несколько active snapshots в одном `status.md`.

### Шаг 3 — Определить restart/resume algorithm

Перед normal promotion pass scheduler должен обрабатывать существующие `in_progress` tasks:

1. определить последнюю завершённую stage;
2. проверить наличие current attempt handoff;
3. продолжить `/execute`, `/verify` или `/red-verify`;
4. либо записать explicit recovery decision;
5. никогда не игнорировать `in_progress` только потому, что ready queue пуста.

### Шаг 4 — Привязать closure к конкретному evidence generation

Closure record должен ссылаться на:

- attempt number;
- implementation report;
- functional verification report;
- semantic verification report;
- checkpoint/waiver;
- planning fingerprint;
- final decision и timestamp.

Doctor должен проверять именно referenced current evidence, а не любой исторический PASS.

### Шаг 5 — Добавить review freshness fingerprint

`/review-tasks-plan` report должен фиксировать fingerprint как минимум для:

- feature doc;
- implementation plan;
- reviewed task records;
- direct canonical specs или их manifest;
- dependency ids/status-independent planning fields;
- task schema version.

Status/evidence-only task updates не должны инвалидировать planning approval; изменение task scope, constraints, specs, dependencies, tier или acceptance basis должно.

### Шаг 6 — Исправить failure/follow-up flow

Рекомендуемая последовательность:

1. FAIL при доступном retry budget — task остаётся `in_progress`, increment attempt, bounded repair, fresh verification;
2. budget exhausted — task становится `failed`, dependents блокируются;
3. follow-up планируется через `/prd-to-tasks`;
4. выполняется fresh `/review-tasks-plan`;
5. запускается strict doctor;
6. только после этого follow-up участвует в promotion pass.

### Шаг 7 — Разделить fresh sessions

Для T3:

1. `/execute` session;
2. независимая `/verify` session;
3. независимая `/red-verify` session;
4. scheduler closure decision.

### Шаг 8 — Добавить минимальный test harness

Приоритетные fixtures:

1. crash после `ready -> in_progress`;
2. historical PASS, затем новый FAIL;
3. stale feature semantic-pass после добавления task;
4. changed task card после task-plan approval;
5. retry budget exhaustion;
6. failed task + follow-up replacement;
7. advisory process waiver;
8. schema-valid, но lint-invalid gate object;
9. repeated feature-local waves в общем DAG.

## Финальный verdict

Текущая task queue структурно здорова, и механический `/autopilot` preflight способен выбрать `TASK-034-T3-FT-009-W1`.

Тем не менее unattended run пока имеет существенные workflow risks. Наибольшую вероятность неправильного lifecycle решения создают:

1. противоречие advisory и hard process gates;
2. отсутствие `in_progress` recovery;
3. неструктурированный failure budget;
4. принятие любого исторического PASS;
5. отсутствие task-plan review freshness;
6. неоднозначный multi-run `status.md`.

До исправления этих пунктов `/autopilot` лучше использовать только под наблюдением owner/scheduler с явной фиксацией recovery, retry, waiver и evidence-selection решений.
