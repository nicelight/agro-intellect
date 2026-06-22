---
description: Active contract router for MVP v2.
status: active
owner: architecture
last_updated: 2026-06-23
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/foundation.md
---
# Contracts Index

## Active Contracts

- [Boundary Map](boundary-map.md): pre-PRD boundary hints retained as context.
- [API Guidelines](api-guidelines.md): global HTTP/API guardrails for FastAPI/Pydantic boundaries.
- [Agent Chat Bus](agent-chat-bus.md): global agent-consumable event stream boundary.
- [MessageEnvelope](message-envelope.md): global structured agent-output boundary.
- [Foundation Critical Path](foundation-critical-path.md): foundation-scoped executable contract set for the Photo/User input -> Bus -> Agent -> Message/UI -> Safety/State/Task -> PostgreSQL/timeline/photo export smoke path.

## Routing

Foundation contract details needed before `FT-000` task slicing live in [Foundation Critical Path](foundation-critical-path.md). Detailed product endpoint schemas, event payloads, message fields, and state-machine contracts still belong to feature-level `/spec-improve FT-<NNN>` unless they become shared enough to promote into this folder.
