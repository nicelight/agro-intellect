---
description: Router for active MVP v2 contract specs.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/spec-backbone.md
---
# Contracts Index

Active MVP v2 contract specs:

- [api-guidelines.md](api-guidelines.md): frontend/backend API rules, auth, errors, uploads, CORS, and OpenAPI generation policy.
- [agent-harness.md](agent-harness.md): shared AgentHarness loop, AgentProfile, tool/action proposal, permission, observation, budget, trace, and memory rules.
- [agent-chat-bus.md](agent-chat-bus.md): BusEventEnvelope and agent-consumable working event rules.
- [message-envelope.md](message-envelope.md): MessageEnvelope, runtime decisions, UI Feed projection, and presentation isolation.
- [safety-gate.md](safety-gate.md): physical-action advice, Safety Gate decision, human approval, and action_task unlock rules.
- [boundary-map.md](boundary-map.md): pre-PRD boundary hints retained as framing evidence.

Detailed endpoint schemas, Pydantic models, DB migrations, feature-local state machines,
and UI component contracts belong to `/spec-improve FT-<NNN>` and task records.
