---
description: Epic EP-003 for shared AgentHarness, AgentProfiles, context builder, memory, Bus, MessageEnvelope, UI Feed isolation, and real model runtime.
status: draft
lifecycle: planned
epic_id: EP-003
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/boundary-map.md
---
# EP-003 Shared Agent Harness And Context Boundaries

## Value

Turn product-agent behavior into a governed control plane rather than prompt-only
conventions. The model proposes; the shared harness validates, permission-checks,
executes or pauses, records observations/traces, manages scoped memory, and routes
outputs through project contracts.

## Features

- FT-007 Shared AgentHarness And AgentProfile Runtime.
- FT-008 Permission-Aware Context Builder And AgentMemoryRecord.
- FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation.
- FT-010 Real Model-Backed Product Agent Profiles.

## Success Metrics

- All product agents run as AgentProfiles inside one project-owned AgentHarness.
- Tool/action proposals are schema-validated, permission-checked, approval-gated when
  risky, and returned as structured observations.
- Agent memory is source-ref backed, actor/Farm/Plant scoped, stale-aware, and
  non-authoritative by itself.
- UI Feed, raw chat, raw reasoning, unapproved proposals, and admin UI text never
  enter agent working context.
- First-demo agent behavior uses real LLM/model-backed flows over actual scoped Plant
  data; Vision Observation uses real uploaded photo data.

## Acceptance Criteria

- Separate ungoverned product-agent harnesses are absent.
- Agno remains execution layer only, not domain authority or Bus replacement.
- Agent-originated domain output passes runtime decision, MessageEnvelope, Agent Chat
  Bus, and UI Feed projection where applicable.
- Every harness run can produce trace/eval evidence without exposing hidden reasoning
  or secrets.

## Constraints / Invariants

- `agents-best-practices` is doctrine for harness architecture; `/spec-design` owns
  exact loop contracts, tool schemas, permissions, memory lifecycle, traces, evals,
  budgets, and provider adapters.
- Hidden provider memory, UI Feed replay, raw chat history, and unapproved governance
  content cannot become source of truth.

## Verification Targets

- `test:harness.shared-profile-control-plane`
- `test:harness.loop-permission-observation-trace`
- `test:harness.memory-scope-permission-non-authority`
- `test:agent-output.bus-message-ui-isolation`
- `test:agents.real-model-runtime-and-vision`
