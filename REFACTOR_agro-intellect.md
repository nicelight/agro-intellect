# План безопасной path/naming canonicalization

## Статус и предпосылки

Этот документ определяет execution workflow, а не список новых имён. Полный
`old_path -> new_path` строится agents во время запуска из установленной
naming/path policy, архитектуры и текущего repository.

Запуск разрешён только после того, как:

- установлен следующий project/Memory Bank update;
- его naming/path policy имеет стабильную revision и является authoritative;
- FT-013 полностью завершена и синхронизирована;
- установлен совместимый новый Memory Bank doctor;
- canonical validator или другой authoritative source устранил неоднозначность
  grammar evidence/report filenames;
- repository clean и feature work заморожена на время canonicalization.

Если хотя бы одно условие не выполнено, orchestrator не начинает inventory.

## Цель

Однократно привести входящие в scope project-authored filesystem paths, Python
module identities и связанные references к актуальной policy без legacy
compatibility layer.

После завершения project artifacts должны выглядеть так, будто актуальная
naming/path policy применялась всегда:

- source, tests, scripts и configuration используют только текущие paths;
- Memory Bank, task cards, plans, protocols, reports и changelog используют
  только текущие identities;
- historical prose и path-bearing commands переписаны на текущие names;
- в durable prose нет old/new pairs, rename tables или рассказа о комплексном
  переименовании;
- historical conclusions, statuses, verdicts, chronology и dependencies
  сохранены.

Git history и существующие commit hashes не переписываются. Git остаётся
единственным механическим источником rename lineage.

## Главный naming принцип

Policy не означает глобальную конвертацию в `kebab-case`, `snake_case` или
структуру `src/modules/`.

Для каждого source path agent применяет приоритет:

1. обязательная grammar языка, framework, tooling, generator или scaffold;
2. project architecture и conventions;
3. ближайший локальный паттерн;
4. общие DevRails heuristics.

Решение оценивает целиком:

```text
code root + directories + filename
```

Правила:

- использовать минимальную вложенность, необходимую для owner, boundary,
  capability или технической роли;
- каждый path segment должен добавлять устойчивый смысл;
- не дублировать context директории в filename без причины;
- сохранять обязательные prefixes, suffixes и compound extensions;
- разрешать generic names вроде `service`, `models`, `contracts` и `index`,
  когда роль однозначна из полного path;
- не пытаться искусственно выровнять filesystem path, Python import, package
  export, URL route и build target;
- не нормализовать slugs, регистр или separators без отдельного основания;
- не захватывать unrelated rename, обнаруженный рядом с текущим candidate.

Если current path правдив, соответствует architecture/local pattern и не
нарушает policy, решение должно быть `KEEP`.

## Неизменяемый semantic scope

- Меняются только paths/names и path/name-bearing references.
- Runtime behavior, API routes, URL identity, schemas, persistence semantics и
  authority boundaries не меняются.
- Source split/merge не выполняется.
- Файл с несколькими равноправными responsibilities сохраняет truthful
  neutral/umbrella-name и получает operational решение `NEED_SPLIT`.
- Generated artifacts регенерируются owning tooling, а не редактируются
  вручную.
- Alembic `revision`, `down_revision`, heads и topology не меняются.
- Existing IDs Features, Requirements, Tasks, Behavior examples и ADR не
  перенумеровываются.
- Compatibility wrappers, alias modules и fallback imports запрещены.
- Compatibility symlinks старой структуры запрещены.
- Existing framework-owned `CLAUDE.md`/`GEMINI.md -> AGENTS.md` symlinks
  разрешены и получают `KEEP`. Сам факт допустимости не является основанием
  заменять текущие copies symlinks в рамках refactor.
- Внешняя terminal/shell history за пределами repository не изменяется.

## Ключевые FIXED_KEEP paths

Следующие framework identities не являются rename candidates:

- `AGENTS.md`;
- `CLAUDE.md`;
- `GEMINI.md`;
- `.memory-bank/`;
- `.protocols/`;
- `.tasks/`;
- `.agents/skills/<command-name>/SKILL.md`;
- `.claude/skills/<command-name>/SKILL.md`;
- `scripts/mb-lint.mjs`;
- `scripts/mb-doctor.mjs`;
- fixed Memory Bank core paths, roles, workflows и protocol templates,
  перечисленные в установленной policy.

Дополнительные invariants:

- `SKILL.md` остаётся uppercase;
- command basenames остаются lowercase kebab-case;
- `.agents/skills/` принадлежит Codex;
- `.claude/skills/` принадлежит Claude;
- `.codex/` используется только для project configuration;
- отсутствующие conditional Memory Bank artifacts не создаются только ради
  canonicalization.

Полный fixed set извлекается Inventory Agent из установленной policy. Этот
документ намеренно не дублирует весь список.

## Inventory routing

Inventory Agent относит каждый project-authored candidate ровно к одной группе:

| Группа | Правило |
|---|---|
| `FIXED_KEEP` | Framework/reserved path. Только `KEEP` или `TOOLING_RESERVED`. |
| `PATTERN_VALIDATE` | Feature, task, protocol, report, behavior spec, ADR и другой artifact с canonical pattern. |
| `SUBJECT_CANONICALIZE` | Subject-based SDD spec в architecture/contracts/domains/states/testing/runbooks/guides/adrs. |
| `LOCAL_DECISION` | Application source, tests, scripts и другие paths без exact target rule. |
| `FORBIDDEN_TARGET` | Existing obsolete path или proposed target, запрещённый policy. |

Запрещены:

- массовая нормализация регистра или separators;
- новый `.memory-bank/tech-specs/` target;
- feature-owned `FT-*` design-spec hubs;
- `.memory-bank/commands/`;
- `.memory-bank/tasks/backlog.md`;
- `.memory-bank/modules/`;
- `.memory-bank/graph/`;
- `.memory-bank/verification/`;
- skills внутри `.codex/`;
- второй task registry или durable task-context artifact;
- произвольные protocol filenames;
- `CON-<NNN>-<slug>.md` как новый active target.

Existing legacy `.memory-bank/tech-specs/FT-*.md` не переименовывается только
из-за своего legacy location. Он остаётся brownfield evidence, если отсутствует
другое конкретное основание.

## Exact-pattern validation

Для `PATTERN_VALIDATE` agents не выбирают имена по вкусу. Validator проверяет
canonical grammar, установленную update:

- Feature и Foundation feature;
- Implementation plan;
- Behavior example с обязательной `.behavior.json`;
- ADR;
- exact Task ID и `.task.json` basename;
- task/feature protocol directories и разрешённые protocol filenames;
- evidence/final-report paths и special cases;
- соответствие task ID полям `tier`, `feature`, `wave`;
- уникальность Feature и Implementation plan на Feature ID;
- совпадение frontmatter IDs с filename там, где это требуется.

Existing slugs не меняются только из-за регистра или separator style.

Если evidence/report grammar всё ещё допускает два толкования, включая наличие
или отсутствие сегмента `code|docs`, orchestrator останавливает
`PATTERN_VALIDATE`. Ни один agent не выбирает вариант самостоятельно.

## Subject-based SDD decisions

Перед решением для `SUBJECT_CANONICALIZE` agent читает:

- `.memory-bank/spec-index.md`;
- router соответствующей folder;
- plausible existing subject candidates;
- применимую architecture/domain/contract/state/testing context.

Правила:

- filename описывает concern/subject, а не Feature;
- один concern имеет один canonical filesystem path;
- нельзя создавать `FT-*` design-spec hub;
- нельзя создавать новый spec, если registry/router discovery показывает
  существующего canonical owner;
- существенная convention, влияющая на public/import/build identity или
  ownership, фиксируется как current-state rule в
  `system-architecture.md` через owning architecture workflow.

Architecture update не содержит old/new mapping или migration narrative.

## LOCAL_DECISION protocol

Новая policy намеренно не задаёт автоматический target для большинства
application source files. Поэтому `LOCAL_DECISION` проходит отдельный
proposal/review gate.

Decision Agent для каждого coherent boundary:

1. определяет language/framework/tooling constraints;
2. читает owning architecture boundary;
3. определяет owner, capability и technical role;
4. сравнивает полный current path с ближайшими peer paths;
5. проверяет минимальность nesting и смысл каждого segment;
6. проверяет, не дублирует ли filename directory context;
7. выбирает `KEEP`, если нет положительного основания для rename;
8. выбирает `RENAME` только при одном однозначном target;
9. выбирает `NEED_SPLIT`, если truthful filename невозможен без split;
10. возвращает blocker при нескольких равноценных targets.

Каждое `RENAME` должно иметь structured basis:

- `TOOLING_GRAMMAR`;
- `ARCHITECTURE_OWNER`;
- `PROJECT_CONVENTION`;
- `LOCAL_PATTERN`;
- или допустимую ordered combination.

`basis_refs` содержат только ссылки на policy/architecture и representative
peer paths. Это временное execution evidence, а не новый naming registry.

Fresh Mapping Reviewer независимо проверяет:

- полный path, а не только basename;
- достаточность basis;
- отсутствие unrelated normalization;
- truthful ownership;
- consistency с peer paths;
- отсутствие более дешёвого `KEEP`;
- collisions и public/import/build consequences.

Только reviewer `PASS` разрешает включить local rename во frozen map.

## Router simulation

До первого Memory Bank move orchestrator строит simulated final tree и отдельный
`router-plan.tsv`:

```text
folder	final_markdown_count	rule	decision	router_path	packet_id	status
```

`decision`:

- `KEEP`
- `CREATE`
- `UPDATE`
- `DELETE`
- `NOT_APPLICABLE`

Проверяются правила:

- project-owned Memory Bank folder с более чем тремя Markdown files имеет
  router `index.md`;
- `analysis/index.md` обязателен при существующей `analysis/`;
- `templates/protocols/` освобождён от threshold rule;
- `architecture/index.md` существует только при более чем трёх architecture
  docs;
- `.memory-bank/index.md` остаётся root router.

Router creation/deletion является узким разрешённым structural consequence
document moves и не разрешает создавать другие отсутствующие conditional
artifacts.

Если удаляемый router содержит unique non-routing knowledge, agent не переносит
и не удаляет её самостоятельно: это blocker, потому что потребовался бы
semantic merge.

## Green baseline

Green baseline — воспроизводимое доказательство, что состояние проекта до
первого move исправно по tooling, установленному после Memory Bank update и
завершения FT-013.

В чистой временной копии baseline commit должны пройти:

- default test collection;
- полный deterministic test suite;
- применимые PostgreSQL/migration checks;
- import/application startup smoke;
- Memory Bank lint и новая strict doctor;
- применимые project-native lint/type/build checks.

Orchestrator сохраняет:

- baseline commit SHA;
- policy revision/hash;
- tracked paths;
- test collection;
- package exports;
- canonical FastAPI OpenAPI;
- Alembic revisions/heads/topology;
- executable file modes;
- check commands, exit codes и output digests.

Baseline нужен для различения rename regression и уже существовавшего failure.
Если baseline не green, refactor не начинается.

## Временный run workspace

Bulk inventory/ledger нельзя размещать в `.protocols/`: новые правила разрешают
там только canonical protocol paths и filenames.

Orchestrator создаёт через `mktemp -d` временный workspace вне project root. В
нём находятся:

- `run-state.json`;
- `baseline-manifest.json`;
- `path-inventory.tsv`;
- `router-plan.tsv`;
- `reference-ledger.tsv`;
- `need_SPLIT.tsv`;
- packet JSON;
- agent reports;
- snapshots и verification outputs.

Временный workspace не является project artifact и удаляется после финальной
проверки. Если он потерян, orchestrator восстанавливает run из baseline SHA,
policy hash и последнего checkpoint commit, повторяя read-only discovery.

Никакие custom run files не создаются внутри reserved `.protocols/` или
`.tasks/`.

## `path-inventory.tsv`

Schema:

```text
inventory_group	path_kind	artifact_class	old_path	decision	new_path	basis_kind	basis_refs	packet_id	status
```

`path_kind`:

- `FILE`
- `DIRECTORY`

`decision`:

- `KEEP`
- `RENAME`
- `NEED_SPLIT`
- `TOOLING_RESERVED`
- `EXCLUDE`
- `BLOCKED`

`status`:

- `DISCOVERED`
- `VALIDATED`
- `REVIEWED`
- `PACKET_ASSIGNED`
- `MOVED`
- `REFERENCES_REWRITTEN`
- `VERIFIED`

Правила:

- каждый in-scope file представлен ровно один раз;
- каждая changing/referenced directory identity представлена ровно один раз;
- `FIXED_KEEP` не получает rename target;
- `PATTERN_VALIDATE` ссылается на exact policy/validator rule;
- `SUBJECT_CANONICALIZE` ссылается на spec-index/router evidence;
- `LOCAL_DECISION` содержит structured basis и peer refs;
- `FORBIDDEN_TARGET` никогда не становится `new_path`;
- два `RENAME` не имеют одного target;
- mapping freeze выполняется до первого move.

Inventory временный и после выполнения удаляется. Он не является naming
registry.

## `need_SPLIT.tsv`

`NEED_SPLIT` rows во время исполнения хранятся во временном workspace:

```text
current_path	responsibilities	basis_refs
```

Перед финальной интеграцией они экспортируются в current-path-only
`need_SPLIT.tsv` в разрешённом policy/operator location. Файл не содержит
mapping и не является naming registry. Если rows отсутствуют, пустой artifact
не создаётся. Отдельная split-задача может быть создана только через обычный
workflow и явное решение operator.

## `reference-ledger.tsv`

Ledger автоматически создаётся для frozen `RENAME` map:

```text
reference_id	old_identity	reference_file	reference_location	reference_form	packet_id	status
```

Он покрывает:

- filesystem и directory paths;
- Python absolute/relative imports;
- package reexports;
- dynamic strings;
- shell commands, selectors и globs;
- Markdown/frontmatter links;
- JSON task fields;
- prose.

У ledger нет ручного action и нет `PRESERVE_RAW`: каждое совпадение должно быть
переписано.

Workflow:

1. scanner создаёт rows;
2. orchestrator группирует их по file и packet;
3. writer получает только bounded slice;
4. post-rewrite scanner проверяет old identity;
5. verifier переводит rows в `VERIFIED`.

Неоднозначная substitution является blocker, а не новым action type.

## TASK cards и historical artifacts

Task cards переписываются только в path/name-bearing locations, разрешённых
новой task schema:

- `touched_files`;
- path-bearing `source_artifacts`;
- path/name-bearing constraints, invariants и verification targets;
- filenames в evidence references;
- executable/path-bearing commands;
- другие fields только при прямом разрешении schema.

Не меняются:

- Task ID;
- status, tier, wave, feature;
- Task-ID dependencies;
- verdicts и timestamps;
- evidence conclusions;
- lifecycle, gate ownership и gate semantics.

Validator сравнивает before/after JSON:

1. schema validation;
2. structural diff по JSON pointers;
3. changed-pointer allowlist;
4. доказательство exact substitution из frozen map;
5. structural equivalence остальных fields.

Historical prose canonicalized in place:

- old names заменяются current names;
- links и commands становятся executable по текущим paths;
- chronology и conclusions сохраняются;
- old/new pairs и migration commentary запрещены;
- документ не сообщает, что project или artifact был переименован.

## Agent execution model

Работу выполняет один orchestrator через последовательных fresh Codex agents.
Одновременно разрешён только один writer.

### Orchestrator

Владеет:

- precondition/baseline gates;
- inventory grouping;
- local decision review;
- mapping freeze;
- router simulation;
- collision graph и packet DAG;
- единственным writer lease;
- checkpoints и retries;
- independent verification;
- squash integration и итоговым commit.

### Inventory Agent

Read-only. Строит inventory groups, exact-pattern validation candidates,
reserved/fixed set, forbidden targets и collision report.

### Local Decision Agent

Read-only. Предлагает bounded `KEEP|RENAME|NEED_SPLIT` для одного application
boundary с structured basis.

### Mapping Reviewer

Read-only fresh agent. Проверяет policy compliance, exact patterns, local
decisions, subject ownership, routers, collisions и scope completeness.

### Writer Agent

Получает:

- policy revision и baseline SHA;
- inventory/ledger slice;
- exact `write_boundary`;
- forbidden scope;
- predecessor checkpoint;
- targeted checks и stop conditions.

Не меняет mapping, не расширяет scope и не коммитит.

### Task-card Writer

Работает только через snapshots, schema, pointer allowlist и frozen mapping.

### History Writer

Выполняет только canonical substitutions и link repair в bounded artifact set.

### Independent Verifier

Не доверяет writer reports и самостоятельно проверяет final tree, baseline
comparisons, old-identity absence, validators и Git rename detection.

## Context discipline для окна 250k

Ни один agent не должен загружать весь repository, Memory Bank, inventory или
ledger в context.

Fresh agents запускаются без inherited conversation history. Они получают
только:

- короткий immutable packet prompt;
- применимые policy excerpts;
- inventory/ledger slice;
- непосредственно нужные architecture/local-pattern refs;
- targeted files и checks.

Перед запуском orchestrator оценивает packet:

```text
estimated_input_tokens = ceil(text_input_bytes / 3.5)
```

Коэффициент является conservative operational estimate для смешанного
code/Markdown/JSON и не заменяет model tokenizer.

Рекомендуемые budgets:

- до 110k estimated input tokens;
- до 150k total context после discovery;
- hard reslice до 170k;
- минимум 80k оставляется на tool output, reasoning, edits, checks и report.

Практический byte ceiling для заранее читаемого text packet — около
350–400 KiB. Large files, verbose test output и broad diffs уменьшают ceiling.

Context rules:

- search сначала возвращает filenames/counts, затем bounded snippets;
- test/build logs фильтруются до summary и errors;
- agents не печатают полный inventory/ledger;
- agent report — compact machine-readable summary без повторения входов;
- writer завершает один packet и не продолжает на следующий boundary;
- при достижении budget agent записывает partial status и возвращает packet на
  reslice, не пытаясь «дожать» работу в переполненном context.

Orchestrator context также ограничен:

- принимает только packet status, changed files, check summaries и blockers;
- не принимает полные diffs/logs от subagents;
- durable truth находится во временном run workspace и checkpoint commits;
- после 10–15 writer packets или примерно 60% context orchestrator передаёт
  управление fresh orchestrator session через `run-state.json`.

Full-history forks запрещены. Для subagents используется fresh session,
`fork_turns=none` или эквивалентный механизм с явным packet handoff.

## Packet write boundary

Каждый packet содержит `write_boundary`, прошедший автоматическую validation.

Каждый boundary path:

- project-root-relative;
- POSIX и использует только `/`;
- не содержит glob `*` или `?`;
- не является absolute или drive-qualified;
- не содержит `.`, `..`, `//` или backslash;
- сравнивается case-sensitive и lexical;
- может иметь не более одного trailing `/`.

Для каждого move и old path, и new path обязаны входить в packet boundary.

Writer перед изменениями подтверждает:

- текущий checkpoint SHA;
- отсутствие другого active writer;
- отсутствие dirty paths вне expected predecessor diff;
- доступность обоих move endpoints в boundary.

Любое write за boundary завершает packet как failed.

## Packet construction

Packets строятся по coherent boundaries:

- application package вместе с его tests;
- shared substrate отдельно;
- migrations отдельно;
- scripts/config отдельно;
- exact-pattern Memory Bank artifacts;
- subject-based specs вместе с routers;
- task cards отдельным schema-controlled batch;
- historical prose и local operational artifacts bounded batches.

File count не является основным лимитом packet. Orchestrator использует
context byte/token budget и уменьшает packet для shared entrypoints, large
files, migrations и high-density references.

Packet DAG учитывает parent/child moves, imports, reexports, entrypoints,
Alembic, test identities, task/report patterns и routers.

## Move strategy

- Collision, case-fold и Unicode-normalization checks проходят до moves.
- One-to-one tracked moves выполняются через `git mv`.
- Case-only rename использует зарегистрированный temporary intermediate path
  внутри того же packet.
- Nested moves получают детерминированный order.
- Executable bits сохраняются.
- Generated references регенерируются owning tooling.
- После packet old source отсутствует, target существует, imports parse,
  reference rows закрыты и targeted checks проходят.
- Existing framework-owned symlinks сохраняются и проверяются; другие symlinks
  не создаются.

## Последовательность выполнения

1. Установить update и зафиксировать policy revision/hash.
2. Завершить FT-013 и synchronization.
3. Проверить, что report grammar ambiguity устранена authoritative validator.
4. Заморозить feature work и получить clean repository.
5. Создать dedicated branch и внешний temporary run workspace.
6. Получить green baseline в чистой копии.
7. Inventory Agent строит пять inventory groups.
8. Exact validators проверяют fixed, product, task, protocol, report и forbidden
   patterns.
9. Subject agents проверяют spec-index, routers и canonical owners.
10. Local Decision Agents готовят bounded source decisions.
11. Fresh Mapping Reviewer проверяет полный inventory и local proposals.
12. Orchestrator строит simulated final tree и `router-plan.tsv`.
13. Проверить collisions, forbidden targets, package/build effects и
    write-boundary feasibility.
14. Заморозить mapping.
15. Сгенерировать identity map и `reference-ledger.tsv`.
16. Назначить каждую inventory/ledger/router row одному packet.
17. Последовательно выполнить source/test packets.
18. Выполнить scripts/config/migration packets.
19. Выполнить exact-pattern и subject-based Memory Bank/router packets.
20. Выполнить schema-controlled Task-card packets.
21. Выполнить historical prose и operational-artifact packets.
22. Регенерировать generated artifacts.
23. Выполнить полный old-identity и forbidden-target scans.
24. Запустить fresh Independent Verifier.
25. В clean integration copy от baseline SHA squash-применить verified
    checkpoint chain.
26. Повторить весь verification suite.
27. Экспортировать non-empty current-path-only `need_SPLIT.tsv` в разрешённый
    location.
28. Удалить temporary workspace и этот execution plan из final tree.
29. Создать один orchestrator-owned atomic commit.
30. Проверить итоговый commit из новой чистой копии.

## Checkpoints и recovery

Subagents не коммитят. После PASS каждого packet orchestrator:

1. сверяет diff с boundary;
2. проверяет inventory/ledger/router status;
3. запускает targeted checks;
4. создаёт checkpoint commit в dedicated branch;
5. обновляет внешний `run-state.json`.

Checkpoint chain временная. Итоговый target получает один squashed commit без
temporary inventory или naming registry.

При failed packet:

- phase не продвигается;
- repair agent получает последний verified checkpoint;
- predecessor packets не повторяются;
- изменение mapping возвращает affected graph в review и reference discovery.

Если temporary workspace потерян, read-only artifacts перестраиваются из
baseline/policy/checkpoint. Выполненные moves повторно не применяются.

## Механические инварианты

- Policy revision/hash соответствуют frozen run.
- Каждый project-authored path относится ровно к одной inventory group.
- `FIXED_KEEP` и `TOOLING_RESERVED` paths не изменены.
- Every local rename имеет structured basis и independent review PASS.
- Нет массовой case/slug/separator normalization.
- Каждый in-scope file и changing directory представлены ровно один раз.
- Каждый `RENAME` source отсутствует, target существует.
- Нет exact, case-fold, Unicode, module или target collisions.
- Ни один target не нарушает forbidden-path rules.
- Product/task/protocol/report artifacts проходят canonical validators.
- Existing IDs и slugs не изменены без отдельного основания.
- Subject specs сохраняют one-concern/one-canonical-path.
- Router final tree соответствует threshold/special rules.
- Каждый reference row получает `VERIFIED`.
- В final in-scope tree нет old paths, module identities, links, commands или
  prose names.
- Нет `PRESERVE_RAW`, old/new pairs или migration commentary.
- Нет compatibility wrappers, alias modules или fallback imports.
- Framework symlinks ограничены `CLAUDE.md`/`GEMINI.md` policy.
- Task lifecycle semantics и evidence conclusions неизменны.
- API routes, package symbols, build targets и Alembic topology не изменены
  непреднамеренно.
- Temporary workspace, inventory, ledger и execution plan отсутствуют в final
  tree.

## Финальная проверка

В чистой копии итогового squashed tree выполняются:

- default test collection;
- mapping-normalized comparison collection с baseline;
- targeted suites всех affected boundaries;
- полный deterministic test suite;
- import/application startup smoke;
- FastAPI OpenAPI canonical comparison;
- public package symbol и mapped-module comparison;
- build target/entrypoint comparison;
- Alembic revisions, heads, topology и migration tests;
- executable-bit и allowed-symlink validation;
- AST import graph validation;
- Task schema и JSON-pointer substitution equivalence;
- Feature/plan/behavior/ADR/task/protocol/report validators;
- router threshold/special-case validation;
- forbidden-target scan;
- Memory Bank link/frontmatter scan;
- Memory Bank lint и новая strict doctor;
- project-native lint/type/build checks;
- `git diff --check`;
- `git diff --find-renames --summary`;
- `git diff -M`;
- полный old-identity scan по source и project artifacts;
- отдельный scan local ignored operational artifacts;
- отсутствие temporary control artifacts и execution plan.

Canonicalization завершена только после всех PASS без old-identity allowlist и
незарегистрированных исключений.

## Оценка agent workload

Ожидаемый порядок для repository текущего масштаба после update:

- 2–4 fresh runs для inventory/exact validators;
- 4–8 Local Decision Agent runs;
- 1–2 Mapping Reviewer runs;
- 8–16 source/test writer packets;
- 4–8 Memory Bank/protocol/report/router packets;
- 1–3 Task-card packets;
- 4–10 historical prose/operational packets;
- 2 independent verification runs;
- 2–8 bounded repair runs.

Итого: ориентировочно 25–50 последовательных fresh Codex runs.

Ожидаемый agent wall-clock — 12–36 часов, либо 1–4 календарных суток с полными
test suites и retries. Человеческая реализация кода не требуется. Operator
нужен только при:

- unresolved report grammar;
- нескольких равноценных local targets;
- semantic merge/split;
- необходимости зафиксировать новую существенную architecture convention;
- contract conflict, который нельзя решить rename-only изменением.

После устранения precondition blockers, при green baseline, frozen mapping,
single-writer packets и independent verification вероятность завершения с
bounded retries оценивается как высокая. Основные риски — ошибочный
`LOCAL_DECISION`, пропущенная reference form и many-to-one protocol/report
mapping; план закрывает их отдельным review gate, exact validators и negative
scans.
