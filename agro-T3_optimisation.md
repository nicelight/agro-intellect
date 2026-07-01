# Plan: remove mandatory T3 rollback/recovery gate from Agro Intellect

## Objective

Обновить уже развёрнутый DevRails в Agro Intellect после canonical refactor и
убрать rollback/recovery closure blocker из активной `FT-001` queue.

Целевой T3 contract:

```text
/verify PASS
-> /red-verify semantic-pass
-> HUMAN_CHECKPOINT: done
-> explicit owner/scheduler closure
-> /mb-sync
```

Rollback остаётся допустимым только когда его прямо требует конкретная
migration, spec или task gate.

## Safety boundary

В Agro Intellect уже есть незакоммиченные implementation/test changes и активная
`TASK-005-T3-FT-001-W1`. Перед migration:

```bash
git -C /home/serg/Projects/agro-intellect status --short
```

Не сбрасывать и не переписывать существующие code/test changes. Generated
DevRails files и planning records изменять отдельным, обозримым write set.

`TASK-005-T3-FT-001-W1` и все её task/protocol/evidence artifacts полностью
исключены из этой оптимизации. Она закрывается по уже сформированным правилам,
включая существующие rollback/recovery requirements.

## Preconditions

- Canonical plan `IDEAS/T3_optimisation_workflow.md` реализован.
- DevRails syntax/release checks зелёные.
- Runtime installer берётся из обновлённого DevRails source.

## 1. Update deployed runtime and generated contracts

Обновить в обоих runtime roots:

```text
.agents/skills/
.claude/skills/
```

Skills:

- `autopilot`
- `autonomous`
- `execute`
- `verify`
- `red-verify`
- `mb-sync`
- `mb-doctor`

Также обновить generated project files:

- `AGENTS.md`
- `.memory-bank/workflows/tier-policy.md`
- `.memory-bank/workflows/autonomy-policy.md`
- `.memory-bank/workflows/mb-sync.md`
- `.memory-bank/workflows/execute-loop.md`
- `scripts/mb-doctor.mjs`

Предпочтительный targeted sync из DevRails root:

```bash
node scripts/install-framework.mjs \
  --bootstrap \
  --target /home/serg/Projects/agro-intellect \
  --sync \
  --yes \
  --skill autopilot \
  --skill autonomous \
  --skill execute \
  --skill verify \
  --skill red-verify \
  --skill mb-sync \
  --skill mb-doctor
```

После sync проверить diff до изменения planning artifacts.

## 2. Reconcile active FT-001 planning

Удалить только tier-generated rollback closure boilerplate из:

- `.memory-bank/tasks/plans/IMPL-FT-001.md`
- `.protocols/FT-001/plan.md`
- `.memory-bank/tasks/TASK-006-T3-FT-001-W1.task.json`
- `.memory-bank/tasks/TASK-007-T3-FT-001-W2.task.json`
- `.memory-bank/tasks/TASK-008-T3-FT-001-W2.task.json`
- `.memory-bank/tasks/TASK-009-T3-FT-001-W2.task.json`
- `.memory-bank/tasks/TASK-010-T3-FT-001-W3.task.json`
- `.memory-bank/tasks/TASK-011-T3-FT-001-W3.task.json`

Удалить формулировки вида:

```text
ROLLBACK_RECOVERY_NOTE: present
T3 verify/red-verify/human/recovery evidence
T3 closure includes ... rollback/recovery ...
```

Сохранить:

- реальные migration `upgrade/downgrade` checks;
- task-specific rollback requirement, если оно явно задано canonical spec;
- `/verify`, `/red-verify`, human checkpoint, owner closure и sync;
- task identity, tier, wave, dependencies, status и существующее evidence.

При изменении feature-level plan сохранить все существующие указания и секции,
относящиеся к `TASK-005`, без оптимизации или superseding notes.

## 3. Preserve TASK-005 and historical evidence

Не изменять:

- `.memory-bank/tasks/TASK-005-T3-FT-001-W1.task.json`;
- `.protocols/TASK-005-T3-FT-001-W1/**`;
- `.tasks/TASK-005-T3-FT-001-W1/**`;
- текущие implementation/test changes этой task.

Не переписывать задним числом:

- completed `TASK-003-T3-FT-000-W0`;
- `.memory-bank/tasks/plans/IMPL-FT-000.md`;
- старые `.tasks/*` reports;
- старые changelog entries;
- closure artifacts уже завершённых tasks.

Они фиксируют правила, действовавшие в момент выполнения.

## 4. Validation

Проверить live policy surfaces:

```bash
rg -n 'ROLLBACK_RECOVERY_NOTE|TASK_T3_ROLLBACK_MISSING|human/recovery markers' \
  AGENTS.md \
  .agents/skills \
  .claude/skills \
  .memory-bank/workflows \
  scripts/mb-doctor.mjs
```

Ожидается no matches.

Проверить active FT-001 planning отдельно:

```bash
rg -n 'ROLLBACK_RECOVERY_NOTE|human/recovery|rollback/recovery marker' \
  .memory-bank/tasks/plans/IMPL-FT-001.md \
  .memory-bank/tasks/TASK-006-T3-FT-001-W1.task.json \
  .memory-bank/tasks/TASK-007-T3-FT-001-W2.task.json \
  .memory-bank/tasks/TASK-008-T3-FT-001-W2.task.json \
  .memory-bank/tasks/TASK-009-T3-FT-001-W2.task.json \
  .memory-bank/tasks/TASK-010-T3-FT-001-W3.task.json \
  .memory-bank/tasks/TASK-011-T3-FT-001-W3.task.json \
  .protocols/FT-001/plan.md
```

Затем:

```bash
node scripts/mb-lint.mjs
node scripts/mb-doctor.mjs
git diff --check
```

`mb-doctor --strict` запускать на обычной T3 closure boundary после актуализации
task status/evidence, а не как способ закрыть task.

## Acceptance criteria

- Generated Agro workflow больше не требует rollback/recovery marker для T3.
- Doctor не знает finding `TASK_T3_ROLLBACK_MISSING`.
- Planned `TASK-006`–`TASK-011` не содержат старого closure boilerplate.
- `TASK-005`, её protocols, reports, closure requirements и implementation
  changes остались без изменений.
- Реальные migration downgrade checks сохранены.
- Historical completed evidence не переписано.
- Unrelated Agro implementation/test changes сохранены без модификации.
