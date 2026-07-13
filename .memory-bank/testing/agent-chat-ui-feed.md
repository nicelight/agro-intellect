---
description: Verification contract for FT-008 Bus/UI persistence, reconciliation, context hygiene, and Plant feed API.
status: active
type: testing_spec
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/states/safety-action-lifecycle.md
---
# Agent Chat Bus And UI Feed Verification

## Scope

Defines executable FT-008 verification for durable introductions, guarded
Bus/UI writes, authorized context/feed reads, and context isolation. Frontend
DOM/e2e rendering remains an FT-016 consumer check over this exact API.

## Required matrix

| Area | Assertions |
|---|---|
| Migration/models | Native UUID parity, restricted FKs, exact constraints, introduction uniqueness, Bus dedupe, and fixed consumability flags. |
| Introduction sink | Exact strict eight-item input; accepted/duplicate/rejected/failed 8-or-0 matrix; no partial writes; conflicting content fails closed. |
| Reconciliation | Missing active Plant batch converges to eight UI rows after restart; repeated runs do not duplicate; archive race writes none; restore needs a fresh scan. |
| Safe publication | Matching `safe_information` plus current guard atomically creates one typed Bus quotation and one literal UI message; duplicate is idempotent and conflict fails closed. |
| Other classes | `blocked_uncertain` creates only a generic UI notice; task/physical classes create no FT-008 effect. |
| Context builder | Current ActorContext/PlantAccessGrant and active Plant required; UI Feed/raw chat/admin/unapproved content absent; typed quotation stays data and never enters instruction/routing fields. |
| Feed API | Auth/no-leak, retained-history read, stable pagination, strict cursor/limit errors, no-store, OpenAPI, and both agent flags fixed false. |
| Security | No secrets/auth/provider history/hidden reasoning; markup/prompt/URL-looking text remains unchanged inert data. |

## Behavior traceability

- `FT-008-BHV-001`: deterministic introduction delivery converges after
  failure/restart and remains exactly once.
- `FT-008-BHV-002`: archived Plant blocks new projection/context and restore
  requires fresh reconciliation.
- `FT-008-BHV-003`: classified candidate text is literal UI data and typed Bus
  quotation, never an instruction or routing authority.

## Commands

- Focused backend suite: `.venv/bin/python -m pytest tests/backend/agent_chat -q`
- Access/Agent Runtime regression: `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_runtime tests/backend/agent_chat -m "not real_model" -q`
- Full deterministic regression: `.venv/bin/python -m pytest tests -m "not real_model" -q`
- Memory Bank lint: `node scripts/mb-lint.mjs`
- Diff check: `git diff --check`

FT-016 later adds browser-level text-node/no-active-link verification without
changing this backend contract or making UI Feed agent-consumable.

