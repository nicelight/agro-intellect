# Memory Bank structure templates

Use these templates to initialize a repo.

> Note: Templates are intentionally **short** and **structural**.
> The Memory Bank will be expanded by the agent based on PRD/codebase.

---

## 1) `AGENTS.md` (repo root)

Keep it ~100 lines. It must be a **map**, not an encyclopedia.

```markdown
# Agent Operating Guide (Project Map)

## Prime before work
1. Read `AGENTS.md` (this guide)
2. Read `.memory-bank/constitution.md` (top governing policy)
3. Read `.memory-bank/mbb/index.md` (Memory Bank rules)
4. Read `.memory-bank/spec-backbone.md` (spec readiness/backbone state)
5. Read `.memory-bank/spec-index.md` (normative spec registry)
6. Read `.memory-bank/index.md` (table of contents)
7. Read task/feature-specific docs

## Preferred context routing
- Start with `.memory-bank/architecture/*` and `.memory-bank/guides/*` for concept priming.
- If present, prefer explicit normative docs such as `.memory-bank/constitution.md`, `.memory-bank/spec-backbone.md`, `.memory-bank/spec-index.md`, `.memory-bank/invariants.md`, `.memory-bank/glossary.md`, `.memory-bank/contracts/*`, `.memory-bank/states/*`, `.memory-bank/runbooks/*`, and `.memory-bank/testing/*`.
- Normative docs enrich the Memory Bank; they do not invalidate valid duo docs.
- Before serious work, read `.memory-bank/spec-backbone.md`, `.memory-bank/spec-index.md`, and follow linked SDD specs.
- Do not create a new spec before checking existing specs through `.memory-bank/spec-index.md`.
- For any tier, if the task record or linked feature contains authoritative SDD
  spec links, read `.memory-bank/spec-backbone.md`, `.memory-bank/spec-index.md`, and those linked specs before
  implementation or verification.
- For `T2` / `T3` tasks, linked SDD specs are normative inputs; missing linked specs are a blocker for serious work.

## Docs First
After finishing a meaningful unit of work:
1) Update `.memory-bank/` (WHY/WHERE + navigation)
2) Then commit code changes

## Runtime vs durable memory
- Durable knowledge base: `.memory-bank/`
- Operational artifacts: `.tasks/` (NOT part of Memory Bank)
- Long-running plans/logs: `.protocols/`

## Subagents (orchestrator → workers)
When a task requires reading many files or producing long output:
- spawn subagents (max depth = 2)
- each subagent writes details into `.tasks/TASK-XXX/`
- orchestrator reads only short summaries

## Clean context (recommended)
- Route each `TASK-XXX` by `task.tier` and `.memory-bank/workflows/tier-policy.md`.
- T0/T1 may use compact `.protocols/TASK-XXX/run.md`; compact evidence can be enough.
- Scheduler mode: T2/T3 require full protocol state plus `/verify` `VERDICT: PASS` and `/red-verify` `SEMANTIC_VERDICT: semantic-pass` before the scheduler marks `done`.
- Scheduler mode: T3 also requires exact marker lines `HUMAN_CHECKPOINT: done` and `ROLLBACK_RECOVERY_NOTE: present`.
- Manual mode: T0/T1 may close after `/verify PASS` only with explicit closure ownership and completed evidence; T2/T3 must run `/red-verify` before final closure/`/mb-sync`.
- If running in **Claude Code**: execute each `TASK-XXX` in a **fresh Claude session** using tier-appropriate `.protocols/TASK-XXX/` state.
- If running in **Codex**: you can run each `TASK-XXX` in a fresh session via `codex exec` (see `/execute`).
- Sequencing: independent tasks may run in parallel clean sessions; dependent/shared-file tasks must run sequentially.

Codex (fresh session):
- `codex exec --ephemeral --full-auto -m gpt-5.2-high 'TASK_ID=TASK-123. Read AGENTS.md + task record + tier-policy. Use tier-appropriate .protocols/TASK-123/ state. Implement. Record evidence. Report → .tasks/TASK-123/…'`

Claude (fresh session):
- `claude -p --no-session-persistence --permission-mode acceptEdits --model opus 'TASK_ID=TASK-123. Read AGENTS.md + task record + tier-policy. Use tier-appropriate .protocols/TASK-123/ state. Implement. Record evidence. Report → .tasks/TASK-123/…'`

## Two modes (manual vs scheduler)
- **Manual**: run `/analysis` → `/brief` → `/constitution` if `project_principles` is not `ratified|partial` → `/write-prd` → `/spec-init` → `/prd` → `/spec-design` → `/spec-improve FT-<NNN>` → `/prd-to-tasks FT-<NNN>` → execute tasks one-by-one with `/execute TASK-<ID>` → `/verify TASK-<ID>`; run `/red-verify` for T2/T3 tasks; `/mb-sync` only when durable Memory Bank docs/state changed. `/spec-design` is mandatory after `/prd`, but simple T0/T1 projects may record a minimal backbone with irrelevant areas `not_applicable`. Use `/brainstorm` before `/brief` only for raw ideas, and use `/clarify-feature FT-<NNN>` only for explicit feature blockers.
- **Autonomous (batch)**: use `/autonomous` for full `PRD → done`; it runs `/spec-auto --init`, mandatory `/spec-design --all`, and `/spec-auto --all`. Use `/autopilot` only if JSON task records and required SDD spec links already exist. See: `.memory-bank/workflows/execute-loop.md` and `.memory-bank/workflows/autonomy-policy.md`.

`.tasks/` naming:
- Folder per process: `.tasks/TASK-<ID>/`
- Files: `TASK-<ID>-S-<STAGE>-final-report-<code|docs>-<NN>.md`
- Keep each report to ≤ 3–5 files worth of analysis to avoid context overflow

## Quality gates (before merge)
- lint / typecheck / build
- unit tests
- e2e tests (if UI/flow)

## Memory Bank entry points
Command specs live in `skills/_shared/references/commands/*.md`.
`skills/_shared/scripts/init-mb.js` generates `.memory-bank/commands/*`, runtime proxy skills, and the current entrypoints in generated `AGENTS.md`.

Representative commands:
- `/analysis`
- `/brief`
- `/constitution`
- `/write-prd`
- `/spec-init`
- `/prd`
- `/spec-design`
- `/spec-improve`
- `/spec-auto`
- `/clarify-feature`
- `/prd-to-tasks`
- `/autopilot`
- `/mb-doctor`

> Keep this file small. Deep docs live under `.memory-bank/`.
```

Create symlinks (or copies if symlink not supported):
- `CLAUDE.md` → `AGENTS.md`
- `GEMINI.md` → `AGENTS.md` *(optional)*

### Native skills (proxy commands for all runtimes)

Create thin proxy skills so commands work natively across tools:

| Directory | Runtime |
|-----------|---------|
| `.claude/skills/<name>/SKILL.md` | Claude Code + OpenCode |
| `.agents/skills/<name>/SKILL.md` | Codex CLI + OpenCode |

> Note: `.codex/` is **not** a skills directory. It is used for Codex **project configuration** (e.g. `.codex/config.toml`).

Each `SKILL.md` follows this pattern:
```yaml
---
name: <command-name>
description: <what it does>
---

Read and follow the instructions in `.memory-bank/commands/<command-name>.md`
```

This keeps `.memory-bank/commands/` as SSOT while giving each runtime native integration:
- Claude Code: `/command-name` in autocomplete
- Codex CLI: `$command-name` or via `/skills` browser
- OpenCode: `/command-name` in TUI (reads both `.claude/` and `.agents/`)

The `init-mb.js` script creates both sets automatically.

---

## 2) `.memory-bank/index.md`

```markdown
---
description: Главная карта знаний проекта (table of contents) для агентов.
status: active
---
# Memory Bank Index

Этот файл — **главная точка входа**. Он должен оставаться коротким.

## Навигация

- [.memory-bank/constitution.md](constitution.md): Project Constitution — top governing policy for agents.
- [.memory-bank/mbb/index.md](mbb/index.md): Правила ведения Memory Bank (MBB).
- [.memory-bank/product.md](product.md): Продукт, аудитория, core value (C4 L1).
- [.memory-bank/requirements.md](requirements.md): Требования (REQ-IDs) + RTM.
- [.memory-bank/epics/](epics/): Эпики (C4 L2).
- [.memory-bank/features/](features/): Фичи (C4 L3).
- [.memory-bank/tasks/index.json](tasks/index.json): Authoritative JSON task record index.
- [.memory-bank/schemas/task.schema.json](schemas/task.schema.json): JSON schema for task records.

- [.memory-bank/spec-index.md](spec-index.md): Pure SDD spec registry and planned-spec index.
- [.memory-bank/spec-backbone.md](spec-backbone.md): Pre-PRD framing status and global backbone state for `/prd` and `/spec-design`.
- [.memory-bank/user-scenarios.md](user-scenarios.md): User scenarios and architecture implications when created by `/spec-init` or `/spec-design`.
- [.memory-bank/glossary.md](glossary.md): Общий словарь терминов и доменных значений.
- [.memory-bank/invariants.md](invariants.md): Глобальные MUST/NEVER правила.
- [.memory-bank/architecture/](architecture/): Duo + boundaries (WHAT/WHY).
- [.memory-bank/guides/](guides/): Valid HOW docs для использования, запуска и troubleshooting.
- [.memory-bank/adrs/](adrs/): ADR-решения.

- [.memory-bank/contracts/](contracts/): Контракты и boundary specs (prefer when present).
- [.memory-bank/states/](states/): Lifecycle/state rules (prefer when present).
- [.memory-bank/runbooks/](runbooks/): Runbooks (setup, dev, deploy).
- [.memory-bank/testing/index.md](testing/index.md): Стратегия тестирования.

- [.memory-bank/skills/index.md](skills/index.md): Реестр скиллов.

## Known gaps
- TBD
```

---

## 3) `.memory-bank/mbb/index.md`

```markdown
---
description: Memory Bank Bible — правила, инварианты и стандарты документации.
status: active
---
# Memory Bank Bible (MBB)

## Constitution precedence
- [.memory-bank/constitution.md](../constitution.md) is the top governing policy for agent decisions.
- MBB, spec-index, spec-backbone, invariants, contracts, states, testing, and workflow docs refine the Constitution and MUST NOT contradict it.

## SSOT pyramid
- **Code**: WHAT/HOW — implementation truth.
- **Docstrings**: contracts + `@docs` pointers.
- **Memory Bank**: WHY/WHERE — boundaries, invariants, navigation.

## Hard rules
1. Every `.memory-bank/**/*.md` file MUST have frontmatter with `description:`.
2. If a folder has >3 docs, add an `index.md` router.
3. Use annotated links: `[.memory-bank/path](rel-path): короткое описание`.
4. Atomic docs: one concept per doc; keep ~≤500 lines.
5. Duo docs remain valid: `architecture/` (WHAT/WHY) + `guides/` (HOW), cross-link both ways for concepts that use the classic pair model.
6. C4 layering: L1 product → L2 epics → L3 features → L4 plans/tasks.
7. Docs First: update MB immediately after finishing a task.
8. Refactor MB every 5–10 updates (split, merge, archive).
9. Separate facts from interpretations: mark hypotheses explicitly ("предположительно", "требует проверки").
10. After merge/rebase conflicts: re-check MB consistency.
11. MB-SYNC after each wave/significant change (see `workflows/mb-sync.md`).
12. When present, `constitution.md`, `spec-backbone.md`, `spec-index.md`, `glossary.md`, `invariants.md`, `contracts/*`, `states/*`, `runbooks/*`, and `testing/*` act as an explicit normative layer and should be linked from relevant docs.

## Forbidden
- Copy-paste implementation details / pseudocode
- Duplicating configs (timeouts, constants) instead of linking to source
- Speculative claims without evidence from code/metrics/tests

## Allowed / encouraged
- Invariants (MUST/NEVER)
- Contracts at boundaries
- Decision rationale + pointers
- Runbooks and verification procedures
```

---

## 3a) `.memory-bank/spec-index.md`

```markdown
---
description: Pure SDD spec registry and planned-spec index.
status: active
---
# SDD Spec Index

## Purpose
- Keep a concise registry of existing and planned SDD specs.
- Read this index before creating new specs or doing serious T2/T3 work.
- Keep readiness, open design questions, backbone status, and routing handoffs in [.memory-bank/spec-backbone.md](spec-backbone.md).
- Feature `spec_design_status` lives in feature frontmatter, not in this index.

## Spec Registry
| Spec | Type | Path | Status | Owner command | Scope |
|---|---|---|---|---|---|
| Project Constitution | governance | [.memory-bank/constitution.md](constitution.md) | active | /constitution | Top governing policy. |
| Invariants | invariants | [.memory-bank/invariants.md](invariants.md) | planned | /spec-init or /spec-design | Global MUST/NEVER rules when evidence exists. |
| Glossary | glossary | [.memory-bank/glossary.md](glossary.md) | planned | /spec-init or /spec-design | Shared vocabulary when needed. |
| Testing Index | testing | [.memory-bank/testing/index.md](testing/index.md) | planned | /prd or /spec-design | Verification strategy and quality gates. |

## Planned Specs
| Area | Expected path | Needed by | Notes |
|---|---|---|---|
| user_scenarios | .memory-bank/user-scenarios.md | /prd, /spec-design | Create only when scenario evidence exists or gaps must be explicit. |
| core_domain | .memory-bank/domains/core-domain.md | /prd, /spec-design | Create only when domain model affects decomposition or shared design. |
| boundary_hints | .memory-bank/contracts/boundary-map.md | /prd, /spec-design | Preliminary boundary hints only; no endpoint/OpenAPI details. |
| lifecycle_hints | .memory-bank/states/lifecycle-map.md | /prd, /spec-design | Create only when lifecycles affect feature boundaries. |
| system_architecture | .memory-bank/architecture/system-architecture.md | /spec-design | Default global architecture hub after /prd. |
| feature_design | .memory-bank/tech-specs/FT-<NNN>-<slug>.md | /spec-improve | Feature-local specs only when needed before task decomposition. |

## Broken / Missing Links
- TBD

## Update Rules
- Keep this file as index/registry only: names, paths, statuses, owners, scopes, and broken links.
- Do not add global backbone status, backbone matrices, feature status maps, long hard rules, or open design question dumps here.
- Use [.memory-bank/spec-backbone.md](spec-backbone.md) for pre-PRD readiness, decomposition inputs, global backbone status, matrix, and handoffs.
- Use linked specs or ADRs for detailed decisions, rationale, contracts, state transitions, schemas, invariants, and testing rules.
```

---

## 3b) `.memory-bank/spec-backbone.md`

```markdown
---
description: Pre-PRD spec framing and global SDD backbone state.
status: active
---
# SDD Spec Backbone

## Pre-PRD Spec Status
- Status: blocked
- Last updated: YYYY-MM-DD
- Notes: Run /spec-init after /write-prd to determine whether PRD decomposition is safe.

## Decomposition Inputs
- User scenarios: not_started
- Domain model: not_started
- Constraints: not_started
- Non-goals: not_started
- Risks: not_started
- Boundary hints: not_started
- Lifecycle hints: not_started

## Open Design Questions
- TBD

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | blocked | - | Decide in /spec-design after /prd. |
| source_of_truth | blocked | - | Decide in /spec-design after /prd. |
| module_boundaries | blocked | - | Decide in /spec-design after /prd. |
| user_scenarios | blocked | .memory-bank/user-scenarios.md | Create/review when scenarios affect decomposition or architecture. |
| constraints | blocked | - | Capture in /spec-init and refine in /spec-design. |
| non_goals | blocked | - | Capture in /spec-init and refine in /spec-design. |
| domain_model | blocked | .memory-bank/domains/core-domain.md | Create only when domain model affects decomposition or shared design. |
| data_flow | blocked | - | Decide in /spec-design after /prd. |
| storage | blocked | - | Decide in /spec-design after /prd. |
| api_contracts | blocked | - | Decide authoritative/needed/not_applicable/blocked in /spec-design. |
| event_message_contracts | blocked | - | Decide authoritative/needed/not_applicable/blocked in /spec-design. |
| agent_io_contracts | blocked | - | Decide authoritative/needed/not_applicable/blocked in /spec-design. |
| security_safety | blocked | - | Decide in /spec-design after /prd. |
| testing_strategy | blocked | .memory-bank/testing/index.md | Decide in /spec-design after /prd. |
| deployment | blocked | - | Decide in /spec-design after /prd. |
| risks | blocked | - | Capture in /spec-init and refine in /spec-design. |
| open_questions | blocked | - | Resolve or keep blocked. |

## Handoff To /prd
- Ready: no
- Required reads: .memory-bank/prd.md, .memory-bank/spec-index.md, this file, and linked pre-PRD specs.
- Stop conditions: Pre-PRD Spec Status is missing, stale, or blocked.

## Handoff To /spec-design
- Backbone areas to revisit: all
- Candidate specs: see .memory-bank/spec-index.md Planned Specs.

## Global Backbone Status
- Status: blocked
- Mode: standard_ai_first
- Architecture artifact strategy: single-file
- Not applicable areas:
  - TBD
- Notes: /spec-design has not completed the global AI-first architecture guardrails yet.
```

---

## 3c) `.memory-bank/constitution.md`

```markdown
---
description: Project Constitution — governing principles for AI-first development.
status: active
version: 1
project_principles: framework-default
ratified: null
last_updated: YYYY-MM-DD
---
# Project Constitution

## Purpose

This Constitution defines the non-negotiable principles that guide AI agents when planning, implementing, verifying, and synchronizing project work.

## Core Principles

### 0. Project Principles Status

This skeleton uses framework-default principles until `/constitution` runs the contextual interview. `ratified: null` means project principles are not ratified yet. When `/constitution` sets `project_principles: ratified` or `project_principles: partial`, it must fill `ratified: YYYY-MM-DD`. If the user explicitly skips that interview, keep or set `project_principles: skipped`, keep `ratified: null`, and continue; revisit `/constitution` later.

### I. AI-First Spec-Driven Development

Agents MUST derive implementation work from explicit product, requirement, feature, task, and workflow artifacts. Agents MUST NOT invent product scope without evidence or user instruction.

### II. Memory Bank Is Durable Project Knowledge

`.memory-bank/` is the durable source of project knowledge. Chat context is temporary. Agents MUST update Memory Bank after meaningful changes.

### III. Schema-Backed Task Execution

Tasks MUST use the current schema-backed JSON task record model. If the framework uses `tier: T0|T1|T2|T3`, agents MUST route execution and verification through that tier model.

### IV. Minimal Verifiable Change

Agents SHOULD prefer the smallest change that satisfies the task. Every completed task MUST have clear checks or evidence.

### V. Evidence Before Done

A task MUST NOT be marked done without verification evidence appropriate to its tier and scope.

### VI. No Legacy Fallback and No Speculation

Agents MUST NOT rely on deprecated task formats, old risk models, or undocumented assumptions. Unknowns MUST be recorded as blockers or explicit assumptions.

### VII. Context Discipline

Agents SHOULD read the smallest sufficient context for the task. Higher-tier or cross-cutting tasks MUST read relevant normative docs such as invariants, contracts, states, testing, and workflow policies.

### VIII. Synchronization

After meaningful changes, agents MUST synchronize affected Memory Bank docs, task state, changelog, and routing files.

## Governance

- Constitution has precedence over workflow habits and generated plans.
- MBB, spec-index, spec-backbone, invariants, contracts, states, testing, and workflow docs refine this Constitution; they must not contradict it.
- Amendments must include rationale and update affected docs if needed.
- Constitution should stay short. Put concrete project rules into `invariants.md`, `contracts/*`, `states/*`, or workflow policy docs.

**Version**: 1 | **Ratified**: YYYY-MM-DD | **Last updated**: YYYY-MM-DD
```

---

## 3c) `.memory-bank/glossary.md`

```markdown
---
description: Словарь терминов, сущностей и agreed vocabulary проекта.
status: draft
---
# Glossary

## Terms
- Term: definition

## Notes
- Используй этот файл для устранения неоднозначностей в названиях и статусах.
```

---

## 3d) `.memory-bank/invariants.md`

```markdown
---
description: Глобальные инварианты и запреты проекта (MUST/NEVER).
status: draft
---
# Invariants

## MUST
- TBD

## NEVER
- TBD

## Notes
- Ссылайся на этот файл из архитектурных, контрактных и execution docs, если правило является cross-cutting.
```

---

## 4) `.memory-bank/product.md`

```markdown
---
description: Product brief (C4 L1): что это, для кого, core value, ограничения.
status: draft
---
# Product

## What this is
<!-- 2–3 предложения словами пользователя -->

## Core value
<!-- 1 thing that MUST work -->

## Audience

## Primary user flow

## Constraints
- Tech stack:
- Timeline:
- Non-goals:

## Key decisions
| Decision | Rationale | Status |
|---|---|---|
| | | pending |
```

---

## 5) `.memory-bank/requirements.md`

```markdown
---
description: Требования (REQ-IDs) + traceability matrix (RTM).
status: draft
---
# Requirements

## REQ list
- (fill from PRD; do not invent requirements without evidence)

## Out of scope
- ...

## Traceability (RTM)
| REQ | Epic | Feature | Test | Lifecycle |
|---|---|---|---|---|
| REQ-XXX | EP-XXX | FT-XXX | test:... | planned |
```

---

## 6) `.memory-bank/schemas/task.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Memory Bank Task Record",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "title", "status", "wave", "feature", "reqs", "depends_on", "touched_files", "tier", "gates", "verify", "docs", "evidence_required", "source_artifacts", "normative_inputs", "constraints", "invariants", "verification_targets"],
  "properties": {
    "id": { "type": "string", "pattern": "^TASK-[0-9]{3,}$" },
    "title": { "type": "string" },
    "status": { "type": "string", "enum": ["planned", "ready", "in_progress", "blocked", "done", "failed"] },
    "wave": { "type": "string" },
    "feature": { "type": "string" },
    "reqs": { "type": "array", "items": { "type": "string" } },
    "depends_on": { "type": "array", "items": { "type": "string" } },
    "touched_files": { "type": "array", "items": { "type": "string" } },
    "tier": { "type": "string", "enum": ["T0", "T1", "T2", "T3"] },
    "gates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "command", "required"],
        "properties": {
          "name": { "type": "string" },
          "command": { "type": "string" },
          "required": { "type": "boolean" }
        }
      }
    },
    "verify": {
      "type": "array",
      "items": {
        "anyOf": [
          { "type": "string" },
          { "type": "object", "additionalProperties": true }
        ]
      }
    },
    "docs": { "type": "array", "items": { "type": "string" } },
    "evidence_required": { "type": "array", "items": { "type": "string" } },
    "source_artifacts": { "type": "array", "items": { "type": "string" } },
    "normative_inputs": { "type": "array", "items": { "type": "string" } },
    "constraints": { "type": "array", "items": { "type": "string" } },
    "invariants": { "type": "array", "items": { "type": "string" } },
    "verification_targets": { "type": "array", "items": { "type": "string" } }
  }
}
```

## 6a) `.memory-bank/tasks/index.json`

```json
{
  "version": 1,
  "tasks": []
}
```

## 6b) Example task record template

The skeleton does not generate this file. `/prd-to-tasks FT-<NNN>` creates real `.memory-bank/tasks/TASK-*.task.json` records only after `/spec-design` is `complete|minimal` and `/spec-improve FT-<NNN>` has completed, blocked, or marked SDD design `not_required`.

```json
{
  "id": "TASK-001",
  "title": "Short task title",
  "status": "planned",
  "wave": "W1",
  "feature": "FT-001",
  "reqs": ["REQ-001"],
  "depends_on": [],
  "touched_files": [],
  "tier": "T0",
  "gates": [
    {
      "name": "unit tests",
      "command": "npm test",
      "required": true
    }
  ],
  "verify": [],
  "docs": [],
  "evidence_required": [],
  "source_artifacts": [],
  "normative_inputs": [],
  "constraints": [],
  "invariants": [],
  "verification_targets": []
}
```

Optional (but recommended) plans folder:
- `.memory-bank/tasks/plans/` — IMPL plans like `IMPL-FT-XXX.md`

---

## 7) `.memory-bank/testing/index.md`

```markdown
---
description: Стратегия тестирования и верификации (quality gates, anti-cheat, UI/e2e).
status: active
---
# Testing & Verification

## Quality gates
- lint / typecheck
- unit tests
- integration tests (if applicable)
- e2e tests for critical user flows

## UI verification
- Prefer Playwright / agent-browser / CDP for UI flows when available
- Store screenshots/videos/traces in `.tasks/TASK-XXX/`
- In Memory Bank keep only links + short conclusions

## Anti-cheat
- Don’t "green" failing tests by weakening assertions without approval.
- If a test reveals a bug: log it (and fix only with explicit scope).

## Artifacts
- Put screenshots/logs/videos in `.tasks/TASK-XXX/`
- In Memory Bank store only links + short conclusions
```

---

## 8) `.memory-bank/skills/index.md`

```markdown
---
description: Реестр доступных скиллов (когда применять) в этом репозитории.
status: active
---
# Skills

## Installed
- cold-start

## When to use
- Bootstrap / memory: cold-start, mb-init
- SDD design: /spec-init, mandatory adaptive /spec-design, /spec-improve, /spec-auto
- PRD decomposition: mb-from-prd
- Codebase mapping: mb-map-codebase
- Execution: mb-execute
- Verification (UAT): mb-verify
- Semantic adversarial verification: mb-red-verify
- Review: mb-review
- Maintenance: mb-garden
- Harness: mb-harness
```

---

## 9) `.memory-bank/changelog.md`

```markdown
---
description: Лог изменений Memory Bank.
status: active
---
# Changelog

## [YYYY-MM-DD] Initial setup
- Created Memory Bank skeleton
- Seeded core docs (product, requirements, testing, task registry)
```

---

## 10) `.memory-bank/workflows/mb-sync.md`

```markdown
---
description: Чеклист синхронизации Memory Bank после wave/изменений.
status: active
---
# MB-SYNC Checklist

- [ ] Duo docs consistent where the classic pair model is used (architecture ↔ guides)
- [ ] Optional normative docs, if present, are linked and do not contradict duo docs
- [ ] RTM up to date (requirements.md)
- [ ] Feature statuses updated
- [ ] JSON task records and `.memory-bank/tasks/index.json` updated
- [ ] Changelog entry added
- [ ] index.md links valid
- [ ] Lint passes (0 errors)
```
