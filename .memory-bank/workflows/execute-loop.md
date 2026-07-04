---
description: Workflow: PRD → FT → TASK loop (interactive or autonomous).
status: active
---
# Execute loop (PRD → Feature → Tasks)

## Principle: no task explosion
- `/prd` creates L1–L3 only (product/requirements/epics/features/testing/index).
- `/write-prd` = PRD-level ambiguity closure. `/clarify-feature` = optional feature-level ambiguity pass.
- `/spec-init` creates lightweight pre-PRD framing state in `.memory-bank/spec-backbone.md` after `/write-prd` and before `/prd`, while `.memory-bank/spec-index.md` remains a pure spec registry/index.
- `/spec-design` is mandatory after `/prd`; it records a minimal backbone for local/simple feature-set pressure or a full architecture scaffold for shared-boundary, contract, state/data/runtime/security, or strict pressure, and records `.memory-bank/foundation.md` when a Foundation Dev Path is needed.
- `/foundation-to-tasks` creates normal `FT-000` foundation JSON tasks and the final foundation gate when foundation is required; execute/verify that queue before product feature tasking.
- `/prd-to-tasks FT-<NNN>` performs registry-first canonical concern discovery before task slicing, then creates the implementation plan and complete JSON task records with direct relevant spec links.
- Rerun `/prd-to-tasks FT-<NNN>` to reconcile subject-based canonical specs, task cards,
  and plans.
- After the current feature task set is decomposed, run
  `/review-tasks-plan FT-<NNN>` in a fresh-context reviewer / separate fresh
  session. Then run `/mb-doctor` at the feature/task-queue boundary when the
  queue has T3 work, autonomous/autopilot handoff, or complex
  T2/foundation/dependency/stale-doc/risky-link conditions. Simple manual
  T0/T1 queues do not require `/mb-doctor` by default.

## Interactive mode (you stay)
1) `/brainstorm -> /brief` when raw idea discovery is needed, or `/brief` directly for clear concepts
2) `/constitution` for contextual governing principles when `.memory-bank/constitution.md` is missing or `project_principles` is framework-default|skipped|missing; if principles are already ratified/partial, continue to `/write-prd`; if explicitly skipped, continue with framework-default/skipped principles
3) `/write-prd` (creates clarified .memory-bank/prd.md)
4) `/spec-init` (updates .memory-bank/spec-backbone.md framing and .memory-bank/spec-index.md registry)
5) `/prd` (fills L1–L3)
6) `/review-feat-plan` for high-risk, large, or autonomous-boundary work; optional/recommended for small manual flows
7) `/spec-design` (mandatory; minimal is valid for local/simple feature-set pressure)
8) If foundation is required, run `/foundation-to-tasks`, `/mb-doctor --strict`, then execute/verify `FT-000` tasks until the final foundation gate is `done`
9) Pick one top feature; use `/clarify-feature FT-001` only for explicit feature blockers
10) `/prd-to-tasks FT-001` (resolves feature design concerns through subject-based canonical specs and creates IMPL plan + complete `TASK-NNN-TN-FT-NNN-WN` records for this feature)
11) Run `/review-tasks-plan FT-001`, then run `/mb-doctor` at the
feature/task-queue boundary only when T3, autonomous/autopilot handoff, or
complex T2/foundation/dependency/stale-doc/risky-link conditions apply;
use `/mb-doctor --strict` before autonomous handoff
12) Execute tasks from `.memory-bank/tasks/index.json` and indexed `*.task.json` records. Recommended defaults:
   - T0/T1 manual: `/execute TASK`, compact evidence or no-runnable-check note, optional local closure by explicit owner
   - T2 manual: `/execute TASK -> /verify TASK`; consider sync at a useful wave/feature boundary
   - T3 manual: `/execute TASK -> /verify TASK -> /red-verify TASK`; consider a human checkpoint and wave-boundary `/mb-sync`
   - after all tasks for a T2 feature are implemented, consider `/red-verify --feature FT-<ID>` when semantic drift risk is material
   - these T2/T3 sequences are advisory; the explicit owner may combine,
     reorder, skip, or replace steps and close using accepted evidence
   - start `/execute` only after the current feature task set has been decomposed and any required/conditional feature/task-queue doctor gate has passed
   - `/execute` reads the indexed task card and direct task-linked canonical specs; structural single-card readiness is owned by `/mb-doctor`, while semantic contradictions remain implementer blockers
   - if `/execute` or `/verify` discovers a required higher tier, stop the
     current run and route the original task ID through
     `/prd-to-tasks FT-<NNN>` for controlled rebuild/split; rerun
     `/review-tasks-plan`, applicable `/mb-doctor`, and `/execute` with the
     replacement task ID
13) Rerun `/review-tasks-plan FT-<NNN>` after a wave only when execution changed
the planning surface: task cards, specs, dependencies, tier, scope, or
unresolved plan assumptions. Status/evidence-only closure does not
trigger another task-plan review.

## Autonomous end-to-end mode (start and leave)
1) `/autonomous`
2) command runs `/write-prd -> /spec-auto --init -> /prd -> /review-feat-plan -> /spec-design --all -> /foundation-to-tasks when required -> /mb-doctor --strict at foundation/task-queue boundary -> execute/verify FT-000 until the final foundation gate is done -> /spec-auto --all -> /prd-to-tasks --all -> /review-tasks-plan FT-<NNN> for each task-linked product feature`, then schedules ready TASKs
3) consider `/mb-doctor --strict` again before product scheduler execution; missing T2/T3 SDD links should be reviewed as warnings unless they expose a real spec contradiction
4) before `/execute`, the scheduler should consider `/mb-doctor --strict`; structurally incomplete T2/T3 cards should produce repair recommendations rather than automatic process-only stops
5) each TASK runs in **fresh CLI sessions**
6) after each task, record status, closure decision, and evidence immediately;
when the last task of a T2 product feature closes, consider feature-level
`/red-verify --feature FT-<ID>` and a wave-boundary `/mb-sync`; lint and
`/mb-doctor --strict` are recommended before promoting dependents
7) after a wave, rerun `/review-tasks-plan FT-<NNN>` only for product features
whose task/spec/dependency/tier/scope planning surface changed; do not
rerun it for status/evidence-only closure
8) final success only if every task-linked product feature has latest
`/review-tasks-plan FT-<NNN>` = `APPROVE`, `/mb-doctor --strict` passes, and no
blocking tasks remain

## Autonomous executor only
If JSON task records already exist and `/review-tasks-plan FT-<NNN>` already
approved every task-linked product feature, use:
- `/autopilot`

`/autopilot` should run `/mb-doctor --strict` before task selection and after a
wave-boundary `/mb-sync`; the owner/scheduler may waive these advisory checks.

Codex (manual execution, tier-routed minimal context):
~~~bash
codex exec --ephemeral --full-auto -m gpt-5.2-high \
  'TASK_ID=TASK-123-T2-FT-001-W1. Use the installed /execute project skill. Read AGENTS.md, the indexed task record, .memory-bank/workflows/tier-policy.md, and direct task-linked canonical specs. Do not load broad planning/global docs by default for T0/T1. Assume structural readiness was checked by the applicable boundary gate. Stop on semantic contradictions, unverifiable success, or scope/public-contract ambiguity. Use tier-appropriate .protocols/TASK-123-T2-FT-001-W1/ state. Implement only scoped changes. Record evidence. For manual T0/T1, close only if explicit top-level owner fast-lane conditions are met; otherwise hand off. Report → .tasks/TASK-123-T2-FT-001-W1/TASK-123-T2-FT-001-W1-S-IMPL-final-report-code-01.md.'

codex exec --ephemeral --full-auto -m gpt-5.2-high \
  'TASK_ID=TASK-123-T2-FT-001-W1. Read AGENTS.md, the indexed task record, .memory-bank/workflows/tier-policy.md, task-scoped acceptance/REQ basis, and direct task-linked canonical specs. Treat T2/T3 protocol, task gates, /verify, /red-verify, human checkpoint, strict doctor, and /mb-sync as advisory confidence tools. The owner may combine, skip, reorder, or waive them. Keep product/spec/safety/scope rules binding and record accepted evidence when practical.'
~~~

Claude (manual execution, tier-routed minimal context):
~~~bash
claude -p --no-session-persistence --permission-mode acceptEdits --model opus \
  'TASK_ID=TASK-123-T2-FT-001-W1. Use the installed /execute project skill. Read AGENTS.md, the indexed task record, .memory-bank/workflows/tier-policy.md, and direct task-linked canonical specs. Do not load broad planning/global docs by default for T0/T1. Assume structural readiness was checked by the applicable boundary gate. Stop on semantic contradictions, unverifiable success, or scope/public-contract ambiguity. Use tier-appropriate .protocols/TASK-123-T2-FT-001-W1/ state. Implement only scoped changes. Record evidence. For manual T0/T1, close only if explicit top-level owner fast-lane conditions are met; otherwise hand off. Report → .tasks/TASK-123-T2-FT-001-W1/TASK-123-T2-FT-001-W1-S-IMPL-final-report-code-01.md.'

claude -p --no-session-persistence --permission-mode acceptEdits --model opus \
  'TASK_ID=TASK-123-T2-FT-001-W1. Read AGENTS.md, the indexed task record, .memory-bank/workflows/tier-policy.md, task-scoped acceptance/REQ basis, and direct task-linked canonical specs. Treat T2/T3 protocol, task gates, /verify, /red-verify, human checkpoint, strict doctor, and /mb-sync as advisory confidence tools. The owner may combine, skip, reorder, or waive them. Keep product/spec/safety/scope rules binding and record accepted evidence when practical.'
~~~

## Parallel vs sequential
- Independent tasks (no shared files) MAY run in parallel (separate sessions).
- Dependent or shared-file tasks SHOULD run sequentially unless the owner accepts
  the coordination risk. Each task should record its
  authoritative closure/evidence immediately; full `/mb-sync` remains a wave
  boundary unless TASK-B requires reconciled durable state or the owner requests
  an early sync.
