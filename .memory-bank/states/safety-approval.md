---
description: Safety Gate and human approval lifecycle for physical-action advice.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Safety Approval

## Physical Actions

Physical actions include changing pH, changing EC, changing solution, changing pumps, changing dosing, changing light regime, pruning, transplanting, root trimming, and similar plant-system interventions.

## Freshness Windows

- pH/EC measurements are fresh for analysis for up to 24 hours.
- pH/EC measurements are fresh for physical-action approval for up to 2 hours.
- Non-pH/EC physical actions still require fresh relevant evidence before approval. For the MVP, pump, light, and high-risk manual interventions require an explicit current-session or <=24-hour context ref, such as a user observation, photo, task/outcome, or setup note that matches the proposed action.
- If a physical-action category has no explicit freshness policy or lacks the required fresh context refs, Safety Gate must return `needs_data` or `block`, never cleared `pass` or actionable `pending_approval`.

Fresh data is necessary for relevant approvals, but never sufficient by itself.

## Safety Gate Outcomes

- `pass`: wording/action is safe under current constraints.
- `block`: immediate action is forbidden.
- `pending_approval`: risky recommendation is converted into a pending action proposal or approval task.
- `needs_data`: missing/stale critical data requires measurement or check task.

If classification is uncertain or Safety Gate is unavailable, fail closed.

## Approval Semantics

- Human approval is required before a physical action can become an actionable human-performed task.
- Approval unlocks only task tracking/status transition for an MVP `action_task`.
- Approval does not authorize automated device execution.
- Rejection keeps the proposal unapproved and may leave only safe checks/follow-up tasks.
- Stale approval conditions must route back through Safety Gate.

## User-Visible Wording

Any user-visible phrase that instructs or implies physical action must pass Safety Gate. If not cleared, it must be blocked or rewritten as a pending approval/check request.
