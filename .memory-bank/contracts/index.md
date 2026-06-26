---
description: Active contract router for MVP v2.
status: active
owner: architecture
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/architecture/system-architecture.md
---
# Contracts Index

## Active Contracts

- [Boundary Map](boundary-map.md): pre-PRD boundary hints retained as context.
- [API Guidelines](api-guidelines.md): global HTTP/API guardrails for FastAPI/Pydantic boundaries.
- [Agent Chat Bus](agent-chat-bus.md): global agent-consumable event stream boundary.
- [MessageEnvelope](message-envelope.md): global structured agent-output boundary.

## Routing

Detailed endpoint schemas, event payloads, message fields, and state-machine
contracts belong to feature-level SDD design inside `/prd-to-tasks FT-<NNN>`
unless they become shared enough to promote into this folder. Standalone
`/spec-improve FT-<NNN>` is a repair or advanced refresh route without task
generation.
