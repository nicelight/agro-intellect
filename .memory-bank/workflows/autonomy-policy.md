---
description: Guardrails and terminal states for unattended autonomous runs.
status: active
---
# Autonomy policy

## Default mode
- Prefer interactive mode unless the user explicitly requested unattended execution.

## Hard-stop categories
- security / compliance ambiguity
- external contracts or partner APIs with unknown behavior
- destructive data migrations
- secret reads / prod writes / deploys

## Allowed assumptions
- naming / wording / non-critical UX defaults
- low-impact implementation details that can be verified later

Non-blocking gaps must be written as explicit assumptions in `.protocols/AUTONOMOUS-RUN/decision-log.md`.

## Recommended gates
- Prefer `/review-tasks-plan FT-<NNN>` immediately before the first runnable
  task of that feature. A change to its task cards, specs, dependencies, tier,
  scope, or implementation plan invalidates the review; status/evidence-only
  updates do not.
- Prefer `/mb-doctor --strict` before task selection, after synchronization,
  and before final success.
- Use tier-appropriate evidence as a default profile:
  - T0/T1: compact evidence may be enough.
  - T2: protocol, applicable gates, `/verify`, and optional feature semantic
    review are recommended according to actual risk.
  - T3: focused/regression checks, `/verify`, per-task `/red-verify`, and a
    human checkpoint are strongly recommended for critical changes.
  - `FT-000`: foundation pseudo-feature; product feature-completion semantics
    normally do not apply.
- Prefer `/mb-sync` at useful wave boundaries and lint/link consistency before
  final success.

These recommendations are not automatic scheduler blockers. The scheduler or
explicit owner may waive, combine, reorder, or replace them and may finish a
run without converting a skipped T2/T3 recommendation into
`HALT_POLICY_VIOLATION` or `HALT_QUALITY_GATES`. Product/spec contradictions,
unsafe actions, missing authority, and destructive-operation ambiguity remain
hard-stop categories.

## Failure budgets
- max_attempts_per_task: 5
- max_consecutive_failures: 5
- max_open_blockers: 3

Attempt, retry, closure, and recovery semantics are defined only in
`.memory-bank/workflows/tier-policy.md`.

## Run status

- `.protocols/AUTONOMOUS-RUN/status.md` is a snapshot of the current run, not an
  append-only multi-run log.
- Starting a new run replaces the previous snapshot. Historical evidence stays
  in per-task protocols, numbered reports, and Git history.

## Terminal states
- `SUCCESS`
- `HALT_BLOCKING_QUESTIONS`
- `HALT_CLARIFICATION_REQUIRED`
- `HALT_REVIEW_REJECT`
- `HALT_FAILURE_BUDGET`
- `HALT_DEPENDENCY_DEADLOCK`
- `HALT_POLICY_VIOLATION`
- `HALT_QUALITY_GATES`
- `HALT_BUDGET_EXCEEDED`
