---
description: Router for active canonical interface, API, event, security, presentation, and audit contracts.
status: active
last_updated: 2026-07-18
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
- [Agent Runtime Adapter](agent-runtime-adapter.md): real model invocation,
  typed input, runtime decision, failure, audit, and envelope handoff.
- [Agent Model Provider Profiles](agent-model-provider-profiles.md): explicit
  provider/model binding, credential isolation, typed egress, and no fallback.
- [Agent Roster And Plant Bootstrap](agent-roster-bootstrap.md): canonical
  identities and deterministic post-commit introduction handoff.
- [Vision Observation Runtime](vision-observation-runtime.md): authorized
  real-photo input, Gemini-only v1 execution, and pending observation handoff.
- [Plant State Runtime](plant-state-runtime.md): authorized trust-record input
  and structured trend/conflict/unknown assessment handoff.
- [Hydroponics Advisor Runtime](hydroponics-advisor-runtime.md): authorized
  pH/EC and Plant-state input, missing-data policy, and pending advisor handoff.
- [Safety Gate Runtime](safety-gate-runtime.md): strict model-backed semantic
  candidate and project-owned classification mapping.
- [Task And Follow-Up Agent Runtime](task-follow-up-runtime.md): strict
  authorized Task/Outcome/evidence input, typed ordinary-task proposal, and
  classified Task handoff.
- [Companion Runtime](companion-runtime.md): explicit authorized real-model
  input/result, closed trigger policy, classification, and proposal handoff.
- [MessageEnvelope](message-envelope.md): validated pending pre-safety agent
  output.
- [UI Feed](ui-feed.md): human presentation only.
- [Timeline Event](timeline-event.md): append-only audit/export event.

## Subject contracts

- [Session Security](auth/session-security.md): password/token/transport security.
- [Session HTTP](auth/session-http.md): login/logout/current-session API.
- [ActorContext](access/actor-context.md): actor and Plant authorization context.
- [Boss Admin HTTP](admin/boss-admin-http.md): direct Account creation and personnel/admin/audit API.
- [Plant Management HTTP](farm/plant-management-http.md): Farm/Plant lifecycle and PlantAccessGrant API.
- [Plant Operations HTTP](plant-operations-http.md): daily check-in and manual measurement API.
- [Task And Approval HTTP](task-approval-http.md): protected Approval decision,
  Task read/completion/follow-up API and the one canonical internal
  ordinary-task source union.
- [Companion Governance HTTP](companion-governance-http.md): protected
  IssueStack/detail reads, explicit model run, proposal decision, and close.
- [Photo Intake HTTP](photo-intake-http.md): photo upload and catalog API.
- [Plant History HTTP](plant-history-http.md): Plant history card/list API and archived retained-history reads.
- [Plant Feed HTTP](plant-feed-http.md): protected UI Feed pagination and archived retained-history reads.
- [Plant State HTTP](plant-state-http.md): protected Plant trust records and human review.

## Routing

Discover by registered path and declared scope before extending or creating a
contract. Feature docs compose relevant contracts; they do not own them.
