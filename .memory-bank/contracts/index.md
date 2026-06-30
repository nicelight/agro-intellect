---
description: Active contract router for MVP v2.
status: active
owner: architecture
last_updated: 2026-06-29
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
- [Local Session Security](local-session-security.md): FT-001 credential, token, lifecycle, cookie, and optional bearer security contract.
- [Local Session API](local-session-api.md): FT-001 login/logout/me, activation handoff, and auth error contract.
- [ActorContext](actor-context.md): role policy, ActorContext, PlantPermissionContext interface, and context-builder authorization contract.

## Routing

Detailed product endpoint schemas, event payloads, message fields, and
state-machine contracts belong to feature-level SDD design inside
`/prd-to-tasks FT-<NNN>`. They may live here when a separate contract owner is
clearer than a feature hub, as with the FT-001 session and ActorContext
boundaries. Active contracts above are authoritative only for their declared
scope. Standalone `/spec-improve FT-<NNN>` is a repair or advanced refresh
route without task generation.
