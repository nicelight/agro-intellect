# Todo / Chat Summary

## Context

- Communication preference: reply in Russian.
- Project: `/home/serg/Projects/agro-intellect`.
- Active role for top-level work: `ROLE GENERAL`.
- The project uses Memory Bank as durable source of project knowledge.
- Current high-level goal: integrate the updated design SDD specs layer and reconcile existing feature/task documents with the newer workflow rules.

## Initial State Assessment From This Chat

- Active Memory Bank is MVP v2, post-PRD-decomposition, post-global-SDD-backbone, and post-Foundation.
- MVP v1 spec layer is archived and must not be used as current source of truth.
- Global SDD backbone was already marked complete.
- Foundation `FT-000` exists as a reserved pseudo-feature, not as a product feature.
- `FT-000` Foundation task queue exists and its tasks were already completed.
- Final Foundation gate `TASK-004-T2-FT-000-W0` was done with latest `VERDICT: PASS`.
- W0 semantic verification had `SEMANTIC_VERDICT: semantic-pass`.
- Product tasking was unblocked for features with completed feature-level SDD designs.
- Feature-level specs existed for `FT-001`, `FT-002`, and `FT-003`.
- Product task records existed only for `FT-001`: `TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3`.
- `FT-001` tasks are T3, packet-backed, and require task-plan review before execution.
- `FT-002` and `FT-003` have normative feature designs but their generated task artifacts had been intentionally removed.
- `FT-004` through `FT-016` remained draft L3 features needing feature-level SDD design during `/prd-to-tasks`.

## Checks Mentioned In Chat

- `node scripts/mb-lint.mjs` passed.
- `node scripts/mb-doctor.mjs` passed.
- `python -m pytest tests` passed with 30 tests.
- `git diff --check` failed only because of pre-existing trailing whitespace in `notes_agro-prj.md`, not because of Memory Bank changes.

## Important Workflow Clarifications

- The correct canonical order is:

```text
/spec-init -> /prd -> /review-feat-plan when needed -> /spec-design -> /foundation-to-tasks when needed -> /prd-to-tasks FT-...
```

- `/spec-design` runs after `/prd`, because it requires requirements, epics, and features.
- `/spec-init` is pre-PRD framing only; it does not own global architecture.
- `/prd` owns L1-L3 decomposition, not tasks or architecture design.
- `/spec-design` owns the global SDD architecture backbone and Foundation decision.
- `/foundation-to-tasks` owns `FT-000` task generation or verification routing.
- `/prd-to-tasks` now owns full feature-level SDD design before task slicing.
- `/spec-improve FT-<NNN>` is now best treated as repair/advanced refresh without task generation, not as the mandatory default gate before every `/prd-to-tasks`.
- `/prd-to-tasks FT-000` is invalid. `FT-000` is reserved for Foundation and must route through `/foundation-to-tasks`.

## User Work Reported During Chat

The user reported that `/prd refresh check` was completed and passed.

Reported results:

- `.memory-bank/prd.md` has `type: prd`, `clarification_status: complete`, and `constitution_checked: true`.
- `.memory-bank/spec-backbone.md` has `Pre-PRD Spec Status: ready_for_prd`.
- `.memory-bank/spec-index.md` remains a pure registry.
- No PRD vs Constitution conflict was found.
- Existing L1-L3 decomposition was preserved: 6 epics, 16 product features, and reserved `FT-000`.
- Product scope and REQ IDs did not change.

Reported changes:

- Routing language in active derived PRD docs was updated.
- `/prd-to-tasks FT-<NNN>` now explicitly owns feature-level SDD design before task slicing.
- `/spec-improve FT-<NNN>` is described as repair/advanced refresh without task generation.
- Updated docs included Memory Bank routers, EP-002..EP-006, FT-004..FT-016, PRD bootstrap protocols, and changelog.

Reported non-actions:

- No task records, packets, or implementation plans were created.
- No feature-local tech specs were created.
- PRD scope, REQ IDs, and epic/feature composition were not changed.
- `/spec-design` was not executed yet.

Reported checks:

- `node scripts/mb-lint.mjs` PASS.
- `node scripts/mb-doctor.mjs` PASS.
- `git diff --check` still FAIL only due to pre-existing trailing whitespace in `notes_agro-prj.md`.

## Files Already Touched During Partial Work

These files were already touched while partially executing the updated SDD/workflow refresh:

- `.memory-bank/architecture/system-architecture.md`
- `.memory-bank/foundation.md`
- `.memory-bank/spec-backbone.md`
- `.memory-bank/spec-index.md`
- `.memory-bank/index.md`
- `.memory-bank/features/index.md`
- `.memory-bank/domains/runtime-data-model.md`
- `.memory-bank/contracts/api-guidelines.md`
- `.memory-bank/contracts/agent-chat-bus.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/index.md`
- `.memory-bank/contracts/boundary-map.md`
- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
- `.memory-bank/tasks/plans/IMPL-FT-001.md`
- `.memory-bank/changelog.md`

## Agreed Next Direction

The next meaningful step is `/spec-design --all refresh`, but it must not be treated as greenfield.

The task should be framed as a brownfield-aware global SDD backbone refresh because:

- `FT-000` tasks already exist and are done.
- `FT-000` produced verified executable baseline code and evidence.
- `FT-001` task records, implementation plan, behavior specs, and packets already exist.
- `FT-001` implementation has not started.
- New global contracts must not silently contradict verified foundation code.

Expected behavior after `/spec-design --all`:

- If backbone is blocked: resolve the blocker and rerun `/spec-design`.
- If backbone is complete and Foundation is still sufficient: run `/prd-to-tasks FT-001` refresh before `/review-tasks-plan FT-001`.
- If backbone is complete but a Foundation gap is found: run `/foundation-to-tasks` for delta/probe work, then `/mb-doctor`, then continue.

## Assignment: Brownfield-Aware Global SDD Backbone Refresh

Run:

```text
/spec-design --all
```

Use this task framing:

```text
Run a brownfield-aware global SDD backbone refresh.

Context:
- FT-000 Foundation tasks already exist and are done.
- FT-000 produced verified executable baseline code and evidence.
- FT-001 task records, implementation plan, behavior specs, and packets already exist, but FT-001 implementation has not started.
- /prd refresh check already passed and preserved the current L1-L3 decomposition.
- Do not treat the project as greenfield.

Rules:
1. Read existing code and verified FT-000 evidence before changing global contracts.
2. Preserve verified FT-000 history and Foundation task closure unless a real contradiction or missing executable baseline gap is found.
3. Existing verified code/baseline is a source of truth below Constitution and explicit user decisions, but above older speculative specs.
4. Do not generate contracts that contradict current verified code unless the contract records an explicit required migration/fix task or blocks downstream work.
5. Use FT-001 generated task records as planning context, not final implementation truth. If refreshed global specs change FT-001 assumptions, route the next step to /prd-to-tasks FT-001 refresh before execution.
6. Do not create product task records, implementation plans, packets, or feature-local FT tech specs in this command.
7. Route feature-local design gaps to /prd-to-tasks FT-<NNN>.
8. Route shared/global gaps into global specs, or mark /spec-design blocked if a safe contract cannot be written.
9. Re-evaluate Foundation Dev Path / FT-000 sufficiency against current code and evidence, not from scratch.
10. Finish with backbone status complete|minimal|blocked, foundation decision, affected specs/docs, blockers if any, and exact next command.

If a proposed global contract differs from the verified FT-000 code baseline, classify it explicitly:
- align the contract to current verified code;
- or record a required foundation/code migration before product tasks;
- or block if the difference affects safety, data authority, auth/security, runtime, or executable readiness.

Do not silently write a contract that future tasks would implement against while the current verified baseline violates it.
```
