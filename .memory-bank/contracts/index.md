---
description: Active contract router for MVP v2.
status: active
owner: architecture
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/spec-backbone.md
---
# Contracts Index

## Active Contracts

- [Boundary Map](boundary-map.md): pre-PRD boundary hints retained as context.
- [API Guidelines](api-guidelines.md): global HTTP/API guardrails for FastAPI/Pydantic boundaries.
- [Foundation Smoke API](foundation-smoke-api.md): substrate-level `/health` and `/ready` contract.
- [Evidence Redaction](evidence-redaction.md): Foundation command/test/evidence redaction contract.
- [Agent Chat Bus](agent-chat-bus.md): global agent-consumable event stream boundary.
- [MessageEnvelope](message-envelope.md): global structured agent-output boundary.
- [UI Feed](ui-feed.md): global human-facing projection boundary that must not become agent context or runtime authority.
- [Timeline Event](timeline-event.md): global append-only audit/export event boundary.

## Routing

Detailed product endpoint schemas, event payloads, message fields, and
state-machine contracts belong to feature-level SDD design inside
`/prd-to-tasks FT-<NNN>` unless they become shared enough to promote into this
folder. Foundation Smoke API is the only active concrete HTTP route contract in
this folder before product route implementation. Active shared contracts above
are authoritative owners for cross-feature rules. Standalone `/spec-improve
FT-<NNN>` is a repair or advanced refresh route without task generation.
