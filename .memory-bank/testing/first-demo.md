---
description: First demo verification plan for the global MVP backbone.
status: active
owner: quality
last_updated: 2026-05-31
---
# First Demo Verification

## Scope

This plan covers the first demonstrable daily `tomato_001` flow after feature-local design and implementation begin.

## Required Gates

- Memory Bank changes: `node scripts/mb-lint.mjs` and `node scripts/mb-doctor.mjs`.
- Backend code: affected lint/typecheck/build gates once code exists.
- Schema validation for timeline events, photo manifests, Bus events, MessageEnvelope, UI Feed events, and dataset lifecycle fields.
- Policy tests for pH/EC freshness, Safety Gate fail-closed behavior, dataset trainability, `silent` audit, and UI Feed filtering.
- Integration tests for photo upload, PostgreSQL authority, timeline append, agent adapter, and approval/task transitions.
- Workflow smoke for daily check-in, photo upload, optional pH/EC, agent conclusions, Safety Gate, task/follow-up, and timeline entry.
- UI/e2e smoke once the Next/PWA flow exists.

## Anti-Cheat Checks

- Raw Agno output cannot enter Agent Chat Bus.
- UI Feed and spoiler notes cannot enter agent working context.
- Photo manifests and `timeline.jsonl` cannot be used as mutable state authority.
- Physical-action wording cannot be displayed or converted to action task without Safety Gate and human approval.
- `can_train_on=true` cannot be set for raw, agent-labeled, eval, holdout, or weak-evidence items.
- Local photos/manifests are not uploaded or synced without explicit user approval.
