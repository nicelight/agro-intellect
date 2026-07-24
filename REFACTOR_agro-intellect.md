# План безопасного path/naming refactor

## Цель

Однократно привести project-authored source paths и связанные references к
актуальной naming/path policy без compatibility wrappers, aliases, symlinks,
fallback imports и поддержки старой структуры.

Refactor выполняется после завершения текущей волны FT-013 и получения чистого
green baseline. Git history не переписывается.

## Границы

- В scope входят project-authored source, tests, scripts и все связанные
  references в актуальных и исторических project artifacts.
- Generated, vendored и tooling-reserved paths не переименовываются.
- Migrations сохраняют executable identity и обязательную ecosystem grammar.
- Split и merge файлов в этом refactor не выполняются.
- Файл с несколькими равноправными responsibilities нельзя называть только по
  одной из них. Такой файл сохраняет правдивое нейтральное или umbrella-name и
  регистрируется в `need_SPLIT.tsv`.
- Raw commands в terminal history сохраняются без изменений.
- Raw commands в non-terminal task cards, актуальных runbooks и CI остаются
  executable и поэтому обновляются при изменении адресуемого пути.

## Контрольные artifacts

### `source-path-inventory.tsv`

Одна временная machine-readable таблица со строкой для каждого входящего в
scope source-файла:

```text
old_path	decision	new_path	status
```

Допустимые `decision`:

- `KEEP`
- `RENAME`
- `NEED_SPLIT`
- `EXCLUDE`

Каждый файл должен присутствовать ровно один раз и получить конечный status.
Свободная колонка с обоснованием не используется. Агент обрабатывает только
текущую строку или отфильтрованный набор `RENAME`, не загружая весь inventory в
контекст.

`source-path-inventory.tsv` является временным operational artifact. После
успешной проверки он удаляется; rename lineage сохраняется в Git.

### `need_SPLIT.tsv`

Отдельная таблица отложенных структурных проблем:

```text
current_path	responsibilities
```

Она содержит только актуальные пути после refactor и краткие стабильные имена
responsibilities. Split не выполняется и не маскируется вводящим в заблуждение
filename.

### `reference-ledger.tsv`

Автоматически создаваемая таблица всех найденных references:

```text
old_identity	reference_file	reference_location	reference_form	action	status
```

Допустимые `action`:

- `REWRITE`
- `PRESERVE_RAW`

Ledger используется механически и не должен целиком загружаться в контекст.
Каждое совпадение обязано получить action и конечный status.

## Формы identity и references

Для каждой строки `RENAME` проверить:

- filesystem path;
- dotted Python module identity;
- relative imports;
- package reexports в `__init__.py`;
- dynamic string references, включая `monkeypatch.setattr` и `patch`;
- shell commands, test selectors и path globs;
- task cards, implementation plans и Memory Bank;
- protocols, reports и changelog;
- directory-level references, если меняется directory path.

Python imports проверяются через AST; одного text search недостаточно.

## Работа с историей

В исторических prose, path lists, plans, protocols, reports, changelog и task
fields старые paths и filenames заменяются актуальными без сохранения старого
варианта.

Исключение — raw historical commands: они сохраняются как свидетельство реально
выполненной команды. Old-identity scanner игнорирует только явно распознанные
raw command blocks и terminal command fields, зарегистрированные в
`reference-ledger.tsv` как `PRESERVE_RAW`.

Git commits и commit hashes не переписываются. Все one-to-one moves выполняются
через `git mv` и проверяются с rename detection.

## TASK cards

В task cards разрешено менять только path/name-bearing содержимое:

- `touched_files`;
- path-bearing `source_artifacts`;
- path-bearing prose в constraints, invariants и verification targets;
- filenames в evidence references, если соответствующие evidence-файлы
  переименованы;
- executable commands в non-terminal cards.

Нельзя менять:

- task ID;
- status;
- tier, wave и feature;
- dependencies;
- verdicts;
- timestamps;
- evidence conclusions;
- lifecycle, gate ownership и gate semantics.

После substitutions JSON validator сравнивает исходную и итоговую task card,
маскируя только разрешённые path/name changes. Все остальные поля должны быть
структурно эквивалентны.

## Модель исполнения

Refactor выполняет orchestrator через последовательных fresh subagents.

Orchestrator владеет baseline, inventory, ledger, packet statuses, blockers,
интеграцией, финальной проверкой и итоговым commit. Subagents работают
последовательно; одновременно разрешён только один writer.

Packets:

1. Сгенерировать полный source inventory без изменений файлов.
2. Проверить решения `RENAME`, `KEEP` и `NEED_SPLIT`.
3. Выполнить rename по отдельным coherent module boundaries с targeted checks.
4. Переписать TASK cards и исторические project artifacts.
5. Независимо проверить итог read-only fresh verifier.
6. Выполнить orchestrator-owned clean-tree verification и интеграцию.

Каждый subagent получает только свой packet, применимые строки inventory и
ledger, разрешённые файлы, stop conditions и checks. Результат записывается в
durable artifacts; в orchestrator возвращаются только completed rows, changed
files, checks и blockers.

Новый rename-кандидат сначала возвращается orchestrator и регистрируется в
inventory и ledger. Subagent не расширяет scope самостоятельно.

## Порядок выполнения

1. Завершить FT-013 и зафиксировать clean green baseline.
2. Сохранить baseline commit SHA, tracked source inventory, public package
   exports, FastAPI OpenAPI, Alembic heads и test collection.
3. Сгенерировать полный `source-path-inventory.tsv`.
4. Назначить каждой строке `KEEP`, `RENAME`, `NEED_SPLIT` или `EXCLUDE`.
5. Проверить полноту inventory и заморозить decisions.
6. Сгенерировать `reference-ledger.tsv` для всех `RENAME` identities.
7. Последовательно выполнять `git mv` строго по inventory.
8. Обновлять imports, exports, dynamic references, актуальные commands и
   зарегистрированные project artifacts.
9. Любой новый кандидат сначала добавлять в inventory и ledger; не выполнять
   незарегистрированный rename импровизационно.
10. Переписать TASK cards с отдельной проверкой неизменности workflow contract.
11. Обновить историческую прозу и path lists; raw terminal commands сохранить.
12. Выполнить negative scan старых identities с единственным исключением
    `PRESERVE_RAW`.
13. Проверить Git rename detection.
14. Выполнить финальную проверку в чистой временной копии итогового tree.
15. Удалить временный `source-path-inventory.tsv`; сохранить только необходимые
    current-path результаты и `need_SPLIT.tsv`.
16. Схлопнуть refactor в один атомарный commit.

## Механические инварианты

- Каждый входящий в scope source-файл представлен в inventory ровно один раз.
- У каждой inventory-строки есть конечные decision и status.
- Каждый `RENAME` source отсутствует после move, а target существует.
- New paths уникальны и не создают case-sensitive или module collisions.
- Каждый найденный reference зарегистрирован и обработан.
- Старые identities отсутствуют в source, prose, task fields и актуальных
  commands.
- Старые identities допустимы только в зарегистрированных raw terminal
  commands.
- `need_SPLIT.tsv` использует только current paths.
- Нет compatibility wrappers, aliases, symlinks или fallback imports.
- Task lifecycle, statuses, verdicts, gates и evidence conclusions не меняются.
- API routes, package exports, Alembic topology и runtime behavior не меняются
  вследствие filesystem/module rename.

## Финальная проверка

Проверку выполнять в чистой временной копии, чтобы удалённые modules,
`__pycache__` и локальные artifacts не маскировали ошибки:

- default pytest collection;
- targeted suites для всех затронутых boundaries;
- полный deterministic test suite;
- import/application startup smoke;
- FastAPI OpenAPI comparison;
- public package export comparison;
- Alembic head и migration tests;
- TASK-card schema и path-substitution equivalence check;
- Memory Bank lint;
- strict doctor;
- `git diff --check`;
- `git diff --find-renames --summary`;
- `git diff -M`;
- полный old-identity scan по source и project artifacts с учётом
  `PRESERVE_RAW`.

Refactor считается завершённым только после прохождения всех инвариантов и
проверок без незарегистрированных исключений.
