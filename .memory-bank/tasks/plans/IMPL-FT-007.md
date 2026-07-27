---
description: Implementation plan for the provider-neutral Agent Runtime and MessageEnvelope boundary.
status: active
type: implementation_plan
feature_id: FT-007
last_updated: 2026-07-27
source_of_truth:
  - .memory-bank/features/FT-007-agent-runtime-decisions-message-envelope.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/testing/agent-runtime.md
---
# IMPL FT-007 Agent Runtime Decisions And MessageEnvelope

## Goal

Keep the completed project-owned Agent Runtime, strict MessageEnvelope handoff,
and deterministic roster/bootstrap behavior while making production model
composition match the accepted current code phase: no endpoint is selected and
missing executors fail closed before I/O.

## Current scope

- Preserve the narrow provider-neutral executor protocols, strict
  competence-specific request/result validation, authorization guards, audit,
  MessageEnvelope semantics, and explicit test fake/spy injection.
- Preserve the exact roster, UUIDv5 introduction identities, one-batch sink,
  and post-commit Plant bootstrap.
- Remove premature DeepSeek/Gemini/ChatGPT OAuth factories, provider binding
  configuration, credential/egress environment fields, provider SDK
  dependencies, and live-provider smoke tests.
- Generalize the Vision executor reference check to the existing safe
  `provider:model` grammar without selecting a provider.
- Align only current FT-007 planning/contracts and the deferred future endpoint
  behavior example. Historical terminal task evidence remains unchanged.

## Non-goals

- No provider, model, base URL, authentication, credential source, egress
  field, timeout, budget, or live-network selection.
- No replacement provider registry/factory, `UnboundExecutor`, compatibility
  shim, state, storage, migration, or public API change.
- No Bus/UI, Safety, Task, Companion, Plant-state, or actuation behavior.

## Normative inputs

- `.memory-bank/architecture/system-architecture.md`
- `.memory-bank/contracts/agent-model-provider-profiles.md`
- `.memory-bank/contracts/agent-runtime-adapter.md`
- `.memory-bank/contracts/vision-observation-runtime.md`
- `.memory-bank/contracts/agent-roster-bootstrap.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/evidence-redaction.md`
- `.memory-bank/testing/agent-runtime.md`
- `.memory-bank/runbooks/agent-runtime-providers.md`

## Dependencies and history

- TASK-028 through TASK-031 are terminal historical FT-007 records and are not
  reopened or rewritten.
- TASK-031 is the completed source of the provider/config surface removed by
  W3.
- TASK-034 is the completed source of the Gemini-only Vision composition drift
  removed by W3.

## W3 implementation

`TASK-045-T3-FT-007-W3` depends on completed TASK-031 and TASK-034.

1. Delete provider factories and their exports.
2. Delete provider-specific settings, environment examples, direct SDK
   dependencies, live smoke tests, and factory/transport-only tests.
3. Retain service-level fake/spy coverage, unbound not-configured coverage,
   roster/bootstrap coverage, strict validation, and outbound media identity.
4. Use `None` as the production unbound executor state; add no replacement
   abstraction.
5. Mark finding 3 closed only after independent verify, red-verify, and the
   T3 human checkpoint succeed.

## Verification

- `.venv/bin/python -m pytest tests/backend/agent_runtime tests/backend/vision_observation -q`
- `.venv/bin/python -m pytest tests -q`
- static scan for provider SDK imports, binding/egress env fields, credential
  reads, profile names, fallback, and real-model smoke paths;
- `node scripts/mb-lint.mjs`
- `git diff --check`

Acceptance requires unchanged strict runtime/media behavior, explicit
test-only executor injection, and stable not-configured production outcomes
before I/O. Deterministic evidence must not claim a real endpoint.

## Queue handoff

- Active task: `TASK-045-T3-FT-007-W3` (`planned`).
- Next gate: fresh `/review-tasks-plan FT-007`.
- Execution starts only after `VERDICT: APPROVE`; T3 closure requires
  `/verify`, task-level `/red-verify`, and `HUMAN_CHECKPOINT: done`.
