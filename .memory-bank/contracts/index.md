---
description: Router for active canonical interface, API, event, security, presentation, and audit contracts.
status: active
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/architecture/system-architecture.md
---
# Contracts Index

## Global contracts

- [Boundary Map](boundary-map.md): decomposition boundary hints.
- [API Guidelines](api-guidelines.md): HTTP/auth/error/origin guardrails.
- [Foundation Smoke API](foundation-smoke-api.md): `/health` and `/ready`.
- [Evidence Redaction](evidence-redaction.md): secret/evidence redaction.
- [Agent Chat Bus](agent-chat-bus.md): agent-consumable event boundary.
- [MessageEnvelope](message-envelope.md): publishable agent output.
- [UI Feed](ui-feed.md): human presentation only.
- [Timeline Event](timeline-event.md): append-only audit/export event.

## Subject contracts

- [Session Security](auth/session-security.md): password/token/transport security.
- [Session HTTP](auth/session-http.md): login/logout/current-session API.
- [ActorContext](access/actor-context.md): actor and Plant authorization context.
- [Boss Admin HTTP](admin/boss-admin-http.md): direct Account creation and personnel/admin/audit API.
- [Plant Management HTTP](farm/plant-management-http.md): Farm/Plant lifecycle and PlantAccessGrant API.
- [Plant Operations HTTP](plant-operations-http.md): daily check-in and manual measurement API.
- [Photo Intake HTTP](photo-intake-http.md): photo upload and catalog API.
- [Plant History HTTP](plant-history-http.md): Plant history card/list API and archived retained-history reads.

## Routing

Discover by registered path and declared scope before extending or creating a
contract. Feature docs compose relevant contracts; they do not own them.
