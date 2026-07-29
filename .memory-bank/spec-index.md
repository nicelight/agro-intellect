---
description: Registry and discovery map for active subject-based SDD specifications.
status: active
last_updated: 2026-07-28
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-backbone.md
---
# SDD Spec Index

## Purpose

- Register one active canonical path for each concrete design concern.
- Support registry-first discovery before specs are created or extended.
- Keep readiness and handoff state in `spec-backbone.md`; feature composition
  remains in feature `spec_design_links`.
- `Change route` names an allowed workflow, not a file owner.

## Spec Registry

| Type | Path | Status | Scope | Change route |
|---|---|---|---|---|
| governance | [.memory-bank/constitution.md](constitution.md) | active | Top project policy | `/constitution` |
| invariants | [.memory-bank/invariants.md](invariants.md) | active | Cross-cutting MUST/NEVER rules | `/spec-init` or `/spec-design` |
| glossary | [.memory-bank/glossary.md](glossary.md) | active | Shared vocabulary | `/spec-init` or `/spec-design` |
| scenarios | [.memory-bank/user-scenarios.md](user-scenarios.md) | active | Actors and scenario implications | `/spec-init` |
| domain | [.memory-bank/domains/core-domain.md](domains/core-domain.md) | active | PRD-level entities and rules | `/spec-init` |
| boundary_hints | [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) | active | Preliminary decomposition boundaries | `/spec-init` or `/spec-design` |
| lifecycle_hints | [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) | active | Preliminary lifecycle boundaries | `/spec-init` or `/spec-design` |
| architecture | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | active | Global architecture and Architecture Spine | `/spec-design` |
| architecture | [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md) | active | Verified backend runtime substrate | `/foundation-to-tasks` or `/spec-design` |
| foundation_decision | [.memory-bank/foundation.md](foundation.md) | active | Foundation gate and pressure map | `/spec-design` |
| data_spec | [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md) | active | Global runtime authority and shared identity | `/spec-design` |
| data_spec | [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md) | active | DB/session/Alembic/runtime-root substrate | `/foundation-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/plant-operations.md](domains/plant-operations.md) | active | Daily check-in, observation, manual pH/EC, and freshness persistence | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md) | active | Local photo artifact authority, catalog, layout, and capture manifests | `/spec-design` or `/feature-to-tasks` |
| data_spec | [.memory-bank/domains/plant-history.md](domains/plant-history.md) | active | Plant card/history projections, retained-history access, and timeline-ref authority boundaries | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/agent-chat-ui-feed-storage.md](domains/agent-chat-ui-feed-storage.md) | active | Agent Chat Bus/UI Feed PostgreSQL rows, atomic publication, and lazy active-Feed roster-introduction materialization | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/plant-state-observations.md](domains/plant-state-observations.md) | active | Plant-state observations, assessments, conflicts, and human promotion | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/safety-action-routing.md](domains/safety-action-routing.md) | active | Immutable Safety classifications, action decisions, approval-input evidence, and pending proposal persistence | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/task-approval-outcomes.md](domains/task-approval-outcomes.md) | active | Approval, ordinary/action Task, automatic follow-up, Outcome, idempotency, and audit-ref persistence | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/companion-governance.md](domains/companion-governance.md) | active | Companion IssueStack, HumanAttentionNeeded, proposal, DecisionRecord, transactions, and projections | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/identity/account-membership.md](domains/identity/account-membership.md) | active | Account and FarmMembership persistence | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/auth/session-storage.md](domains/auth/session-storage.md) | active | LocalSession digest-only persistence | `/feature-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/farm/farm-plant-access-storage.md](domains/farm/farm-plant-access-storage.md) | active | Exact Farm/Plant/grant persistence, migration, bootstrap, and transaction rules | `/feature-to-tasks` or `/spec-design` |
| data_contract | [.memory-bank/domains/admin/admin-audit.md](domains/admin/admin-audit.md) | active | Durable admin audit record and transaction semantics | `/feature-to-tasks` or `/spec-design` |
| api_guidelines | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | active | Global HTTP/auth/error/origin rules | `/spec-design` |
| api_contract | [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md) | active | `/health` and `/ready` substrate boundary | `/foundation-to-tasks` or `/spec-design` |
| evidence_contract | [.memory-bank/contracts/evidence-redaction.md](contracts/evidence-redaction.md) | active | Secret/evidence redaction | `/foundation-to-tasks` or `/spec-design` |
| event_contract | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md) | active | Agent-consumable event boundary | `/spec-design` |
| interface_contract | [.memory-bank/contracts/agent-runtime-adapter.md](contracts/agent-runtime-adapter.md) | active | Authorized typed model invocation, runtime decision, failure, audit, and envelope handoff | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/agent-model-provider-profiles.md](contracts/agent-model-provider-profiles.md) | active | Provider-neutral binding, typed egress, fail-closed production, and future OpenAI-compatible selection | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/agent-roster-bootstrap.md](contracts/agent-roster-bootstrap.md) | active | Canonical ordered agent roster and deterministic introduction metadata | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/vision-observation-runtime.md](contracts/vision-observation-runtime.md) | active | Authorized real-photo Vision Observation input and pending model handoff | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/plant-state-runtime.md](contracts/plant-state-runtime.md) | active | Authorized Plant State trend/conflict/unknown model assessment handoff | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/hydroponics-advisor-runtime.md](contracts/hydroponics-advisor-runtime.md) | active | Authorized pH/EC and Plant-state input, missing-data policy, and pending advisor handoff | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/safety-gate-runtime.md](contracts/safety-gate-runtime.md) | active | Strict provider-neutral Safety candidate and project-owned classification mapping | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/task-follow-up-runtime.md](contracts/task-follow-up-runtime.md) | active | Strict authorized Task/Outcome input, provider-neutral proposal/classification, and ordinary-task handoff | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/companion-runtime.md](contracts/companion-runtime.md) | active | Explicit provider-neutral Companion input, result, classification, trigger, and proposal handoff | `/feature-to-tasks` or `/spec-design` |
| agent_io_contract | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | active | Structured pending pre-safety agent output | `/feature-to-tasks` or `/spec-design` |
| presentation_contract | [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md) | active | Human-facing non-authoritative projection | `/spec-design` |
| audit_contract | [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md) | active | Append-only timeline event, current event registry, and minimal append writer seam | `/spec-design` or `/feature-to-tasks` |
| security_contract | [.memory-bank/contracts/auth/session-security.md](contracts/auth/session-security.md) | active | Password/token/cookie/bearer security | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/auth/session-http.md](contracts/auth/session-http.md) | active | Login/logout/current-session HTTP | `/feature-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/access/actor-context.md](contracts/access/actor-context.md) | active | ActorContext and Plant permission resolution | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/admin/boss-admin-http.md](contracts/admin/boss-admin-http.md) | active | Boss direct Account creation and admin HTTP boundary | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/farm/plant-management-http.md](contracts/farm/plant-management-http.md) | active | Farm/Plant lifecycle and PlantAccessGrant HTTP boundary | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/plant-operations-http.md](contracts/plant-operations-http.md) | active | Daily check-in and manual measurement HTTP boundary | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/task-approval-http.md](contracts/task-approval-http.md) | active | Protected Task/Approval/Outcome HTTP plus canonical internal ordinary-task source union | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/companion-governance-http.md](contracts/companion-governance-http.md) | active | Protected Companion IssueStack reads, explicit run, proposal decision, and close boundary | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/photo-intake-http.md](contracts/photo-intake-http.md) | active | Photo upload and catalog HTTP boundary | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/plant-history-http.md](contracts/plant-history-http.md) | active | Plant history card/list HTTP boundary and archived retained-history reads | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/plant-feed-http.md](contracts/plant-feed-http.md) | active | Protected Plant UI Feed pagination and retained-history read boundary | `/feature-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/plant-state-http.md](contracts/plant-state-http.md) | active | Protected Plant trust-record list and human review boundary | `/feature-to-tasks` or `/spec-design` |
| state_spec | [.memory-bank/states/plant-state-trust.md](states/plant-state-trust.md) | active | Plant evidence trust promotion | `/spec-design` |
| state_spec | [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md) | active | Safety/action lifecycle plus evidence-only classification consumer routing | `/spec-design` |
| state_spec | [.memory-bank/states/task-follow-up-lifecycle.md](states/task-follow-up-lifecycle.md) | active | Human Approval, Task completion, automatic follow-up, and Outcome transitions | `/feature-to-tasks` or `/spec-design` |
| state_spec | [.memory-bank/states/companion-governance.md](states/companion-governance.md) | active | Companion governance lifecycle | `/spec-design` |
| state_spec | [.memory-bank/states/dataset-governance.md](states/dataset-governance.md) | active | Dataset trainability lifecycle | `/spec-design` |
| state_spec | [.memory-bank/states/auth/session-lifecycle.md](states/auth/session-lifecycle.md) | active | Password session expiry/revocation | `/feature-to-tasks` or `/spec-design` |
| state_spec | [.memory-bank/states/plants/plant-and-access-lifecycle.md](states/plants/plant-and-access-lifecycle.md) | active | Plant/grant lifecycle and global archived-Plant operational guard | `/feature-to-tasks` or `/spec-design` |
| testing | [.memory-bank/testing/index.md](testing/index.md) | active | Testing document router | `/spec-design` |
| testing_strategy | [.memory-bank/testing/strategy.md](testing/strategy.md) | active | Global risk-based testing strategy | `/spec-design` |
| testing_spec | [.memory-bank/testing/foundation-test-harness.md](testing/foundation-test-harness.md) | active | Foundation executable harness | `/foundation-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/auth/session-and-access.md](testing/auth/session-and-access.md) | active | Identity/session/access verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/admin/boss-admin-and-audit.md](testing/admin/boss-admin-and-audit.md) | active | Boss admin/audit verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/farm/plant-lifecycle-and-access.md](testing/farm/plant-lifecycle-and-access.md) | active | Farm bootstrap, Plant lifecycle/access, audit, migration, and HTTP verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/plant-operations.md](testing/plant-operations.md) | active | Check-in, manual measurement, and freshness verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/photo-intake.md](testing/photo-intake.md) | active | Photo artifact, manifest, catalog, upload, and timeline-ref verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/plant-history.md](testing/plant-history.md) | active | Plant card/history projection, retained-history, timeline-ref, and redaction verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/agent-runtime.md](testing/agent-runtime.md) | active | Agent runtime, MessageEnvelope, deterministic executor anti-cheat, audit, archive-race, and future integration milestone verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/agent-chat-ui-feed.md](testing/agent-chat-ui-feed.md) | active | Bus/UI persistence, lazy introduction materialization, context hygiene, and Plant Feed verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/vision-observation-plant-state.md](testing/vision-observation-plant-state.md) | active | Photo-byte integrity, provider-neutral vision, trust persistence, conflict, promotion, and API verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/hydroponics-advisor.md](testing/hydroponics-advisor.md) | active | Advisor freshness, missing-data, provider-neutral executor, authorization, and pending-handoff verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/safety-gate.md](testing/safety-gate.md) | active | Provider-neutral classification, durable Safety routing, 2-hour evidence, projection, and concurrency verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/task-follow-up.md](testing/task-follow-up.md) | active | Approval/task/outcome transactions, HTTP, archive/concurrency, and provider-neutral Task and Follow-Up verification | `/feature-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/companion-governance.md](testing/companion-governance.md) | active | Companion governance authority, atomic effects, projections, HTTP, runtime triggers, and provider-neutral verification | `/feature-to-tasks` or `/spec-design` |
| runbook | [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md) | active | Local Foundation setup/start/smoke | `/foundation-to-tasks` or `/spec-design` |
| runbook | [.memory-bank/runbooks/first-boss-local-bootstrap.md](runbooks/first-boss-local-bootstrap.md) | active | First Boss one-shot local bootstrap command | `/feature-to-tasks` or `/spec-design` |
| runbook | [.memory-bank/runbooks/agent-runtime-providers.md](runbooks/agent-runtime-providers.md) | active | Provider-neutral fail-closed operation and deferred selected-endpoint integration milestone | `/feature-to-tasks` or `/spec-design` |

## Planned Specs

| Type | Expected path | Needed by | Notes |
|---|---|---|---|
| subject_spec | `.memory-bank/<family>/<subject>.md` | `/feature-to-tasks` | Create only after registry/folder discovery proves the concern is missing. |
| generated_openapi | generated from backend schemas | implementation/CI | Generated after schemas exist; not global source of truth. |

## Broken / Missing Links

- None detected during the 2026-06-30 subject-based migration.

## Update Rules

- One concrete concern has one active canonical path.
- Registry rows contain only type, path, status, scope, and change route.
- Do not store reverse usage, feature status/readiness, decision bodies,
  schemas, transitions, or file-owner metadata here.
- Features/tasks link the exact applicable canonical specs directly.
