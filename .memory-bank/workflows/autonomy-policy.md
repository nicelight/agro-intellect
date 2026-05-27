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

## Required gates
- latest `/review` verdict must be `APPROVE`
- mandatory `/mb-doctor --strict` before autonomous/autopilot task selection, after `/mb-sync` before promotion, and before final success
- tier-appropriate verification per TASK:
  - T0/T1: compact evidence may be enough
  - Scheduler mode T2/T3: `/verify` PASS and `/red-verify` semantic-pass are required before scheduler marks done
  - Manual mode: `/verify` PASS may close; `/red-verify` may run later and reopen/block/fail
  - T3: human-aware checkpoint plus rollback/recovery note are required
- mandatory `/mb-sync`
- mandatory lint/link consistency before final success, covered by `mb-doctor`

## Failure budgets
- max_retries_per_task: 2
- max_consecutive_failures: 3
- max_open_blockers: 3

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
