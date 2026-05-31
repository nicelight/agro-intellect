---
description: Workflow: PRD → FT → TASK loop (interactive or autonomous).
status: active
---
# Execute loop (PRD → Feature → Tasks)

## Principle: no task explosion
- `/prd` creates L1–L3 only (product/requirements/epics/features/testing/index).
- `/write-prd` = PRD-level ambiguity closure. `/clarify-feature` = optional feature-level ambiguity pass.
- `/spec-init` creates the SDD Design Specs Index after `/write-prd` and before `/prd`.
- `/spec-design` is the mandatory global/backbone SDD gate after `/prd`; `/spec-improve FT-<NNN>` completes or marks unnecessary feature-level design before task decomposition.
- Canonical manual route: `/write-prd -> /spec-init -> /prd -> /spec-design -> /spec-improve FT-<NNN> -> /prd-to-tasks FT-<NNN>`.
- Tasks are created **per feature** via `/prd-to-tasks FT-<NNN>` after `/prd` creates clear feature docs and SDD design status is ready.

## Interactive mode (you stay)
1) `/analysis -> /brief` when idea discovery is needed; use `/brainstorm` before `/brief` only for raw ideas
2) `/constitution` for contextual governing principles when `.memory-bank/constitution.md` is missing or `project_principles` is framework-default|skipped|missing; if principles are already ratified/partial, continue to `/write-prd`; if explicitly skipped, continue with framework-default/skipped principles
3) `/write-prd` (creates clarified .memory-bank/prd.md)
4) `/spec-init` (updates .memory-bank/spec-index.md route map)
5) `/prd` (fills L1–L3)
6) `/spec-design` (updates the global/backbone SDD route map and shared specs)
7) Pick one top feature; use `/clarify-feature FT-001` only for explicit feature blockers
8) `/spec-improve FT-001` (updates only needed feature-level SDD specs or marks not_required/blocked)
9) `/prd-to-tasks FT-001` (creates IMPL plan + TASK-* for this feature)
10) Run `/mb-doctor` when task records change; use `/mb-doctor --strict` before autonomous handoff
11) Execute tasks from `.memory-bank/tasks/index.json` and indexed `*.task.json` records one-by-one:
   - `/execute TASK-001 -> /verify TASK-001 -> /red-verify TASK-001 for T2/T3 -> /mb-sync`
12) After each wave: `/review` (fresh context)

## Autonomous end-to-end mode (start and leave)
1) `/autonomous`
2) command runs `/write-prd -> /spec-auto --init -> /prd -> /spec-design --all -> /spec-auto --all -> /prd-to-tasks --all`, then schedules ready TASKs
3) run `/mb-doctor --strict` before scheduler execution; T2/T3 tasks without SDD spec links are blockers
4) each TASK runs in **fresh CLI sessions**
5) after each `/mb-sync`, run `/mb-doctor --strict` before promoting dependents
6) after each wave: `/review`
7) final success only if last review = `APPROVE`, `/mb-doctor --strict` passes, and no blocking tasks remain

## Autonomous executor only
If JSON task records already exist and review gate already passed, use:
- `/autopilot`

`/autopilot` must run `/mb-doctor --strict` before each task selection pass and after each `/mb-sync` before promotion.

Codex (implement, then verify when the tier requires a separate verifier):
~~~bash
codex exec --ephemeral --full-auto -m gpt-5.2-high \
  'TASK_ID=TASK-123. Read AGENTS.md + task record + tier-policy. Use tier-appropriate .protocols/TASK-123/ state. Implement only scoped changes. Record evidence. Report → .tasks/TASK-123/TASK-123-S-IMPL-final-report-code-01.md.'

codex exec --ephemeral --full-auto -m gpt-5.2-high \
  'TASK_ID=TASK-123. For T2/T3 only: read task record + tier-policy + full protocol + acceptance criteria. Fill .protocols/TASK-123/verification.md. Evidence → .tasks/TASK-123/. VERDICT: PASS/FAIL.'
~~~

Claude (implement, then verify when the tier requires a separate verifier):
~~~bash
claude -p --no-session-persistence --permission-mode acceptEdits --model opus \
  'TASK_ID=TASK-123. Read AGENTS.md + task record + tier-policy. Use tier-appropriate .protocols/TASK-123/ state. Implement only scoped changes. Record evidence. Report → .tasks/TASK-123/TASK-123-S-IMPL-final-report-code-01.md.'

claude -p --no-session-persistence --permission-mode acceptEdits --model opus \
  'TASK_ID=TASK-123. For T2/T3 only: read task record + tier-policy + full protocol + acceptance criteria. Fill .protocols/TASK-123/verification.md. Evidence → .tasks/TASK-123/. VERDICT: PASS/FAIL/NEEDS-CLARIFICATION.'
~~~

## Parallel vs sequential
- Independent tasks (no shared files) MAY run in parallel (separate sessions).
- Dependent or shared-file tasks MUST run sequentially: TASK-A (execute→tier-appropriate verify→red-verify if required→mb-sync) → TASK-B.
