---
description: Pre-PRD spec framing, global SDD backbone state, and foundation routing.
status: active
last_updated: 2026-07-29
---
# SDD Spec Backbone

## Pre-PRD Spec Status
- Status: ready_for_prd
- Last updated: 2026-07-28
- Notes: Active PRD contains enough actor, scenario, domain, constraint, non-goal, boundary, lifecycle, and risk evidence for `/prd-to-features` decomposition. The accepted Finding 4 change preserves the canonical eight-agent roster and only moves missing presentation-row materialization to authorized active-Plant Feed access; it creates no new actor, domain entity, product scenario, or durable lifecycle and requires no new L2/L3 cut. No pre-PRD blocker remains.

## Decomposition Inputs
- User scenarios: [.memory-bank/user-scenarios.md](user-scenarios.md) captures Boss setup, Engineer Plant operations, Safety Gate/action task flow, and Companion governance scenarios.
- Domain model: [.memory-bank/domains/core-domain.md](domains/core-domain.md) captures Account, Farm, FarmMembership, ActorContext, Plant, PlantAccessGrant, admin audit, photo/runtime/audit, agent, safety, governance, and dataset entities.
- Constraints: [.memory-bank/prd.md](prd.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/domains/core-domain.md](domains/core-domain.md) capture local-first, loopback default, one local Farm, PostgreSQL/read-model authority, UI Feed isolation, Safety Gate, provider-neutral agent-runtime boundaries, and no automated actuation. The PRD additionally fixes lazy idempotent materialization of missing canonical roster introductions only on authorized active-Plant Feed open while preserving Plant-create and public Feed schemas and forbidding batch/sink/startup/restore/archived-read reconciliation writes.
- Non-goals: [.memory-bank/prd.md](prd.md) and [.memory-bank/user-scenarios.md](user-scenarios.md) capture no production SaaS, hosted/cloud sync as MVP requirement, billing, enterprise identity, multi-Farm tenancy, broad farm management, microservices, automated actuation, full dataset registry, or real fine-tuning.
- Risks: PRD/Product Brief risks are decomposition-relevant: authz enforced only in UI, governance approval confused with Safety Gate approval, Companion proposals leaking into agent context, agent fake/stub runtime paths, scope growth from Accounts/Farm/Admin. Finding 4 adds only the bounded risk that an active Feed read may fail while materializing presentation rows; the accepted `FEED_PERSISTENCE_FAILED` plus idempotent client retry is sufficient recovery.
- Boundary hints: [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) captures preliminary boundaries for ActorContext, admin, Plant operations, photo artifacts, timeline, Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, and dataset governance. The PRD owns the Finding 4 refinement that authorized active-Plant Feed access is the sole missing-introduction materialization trigger and remains isolated from Agent Chat Bus and agent context.
- Lifecycle hints: [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) captures Account/FarmMembership/Plant/PlantAccessGrant, daily check-in, photo artifact, agent output, physical-action proposal, CompanionProposal, DecisionRecord, and dataset candidate lifecycles. Finding 4 adds no introduction lifecycle: archived reads and restore write nothing, and a later authorized active Feed retry may fill only missing rows.

## Current Design Decisions And Deferred Inputs
- FT-013 provider-input decision is closed: the blanket approval-status
  prohibition for model input is removed. Registered agent-specific requests
  may carry authorized typed governance context as untrusted,
  non-authoritative input; FT-013 includes persisted open-Issue `summary_text`.
- `candidate_output` requires no Markdown/HTML/prompt recognizer: it is opaque
  untrusted normalized text, and syntax-looking content has no executable or
  authority semantics. Future Unicode presentation hardening, if needed, is a
  non-blocking UI concern rather than a candidate-output rejection policy.
- No provider, model, or base URL is selected for the current code phase.
  Credentials, egress, network calls, and live smoke are not current
  deterministic acceptance inputs. A later owner selection activates one
  shared manual integration milestone in the provider runbook.
- Finding 4 is closed by `AD-010`: the static ordered roster and deterministic
  per-introduction identities remain, while only an authorized active-Plant
  Feed transaction may insert missing presentation rows. Plant create,
  startup, restore, archived reads, Agent Chat Bus, and agent context write
  none; no batch/digest/pending/reconciliation lifecycle remains.
- Current-state evidence now matches the accepted design:
  `TASK-046-T3-FT-008-W3` removed the superseded post-create sink, batch table,
  startup scan, and reconciliation path and passed every required T3 closure
  gate.

## FT-013 Shared Design Decisions

| Concern | Canonical sources | Durable decision |
|---|---|---|
| Ordinary Task creation from classified output or approved governance decision | [Task And Approval HTTP](contracts/task-approval-http.md), [Task lifecycle](states/task-follow-up-lifecycle.md), [Task data](domains/task-approval-outcomes.md) | One `create_ordinary_task` seam owns the closed source union, source refs, fingerprints, results, current guards, and branch-specific UoW ownership. |
| Companion classification without premature ordinary dispatch | [Safety Action Lifecycle](states/safety-action-lifecycle.md), [Safety Gate Runtime](contracts/safety-gate-runtime.md), [MessageEnvelope](contracts/message-envelope.md), [Bus](contracts/agent-chat-bus.md), [UI Feed](contracts/ui-feed.md) | The server derives `ordinary_dispatch|companion_governance_hold`; the route adds no persisted schema and Companion-held output cannot dispatch an ordinary Task. |
| FT-013 HTTP views, errors, evidence selection, concurrency, and ref/read grammar | FT-013 registered feature-local contracts, data specs, and testing specs | Exact schemas and error mapping, one-row evidence selection, distinct-run serialization, canonical refs/derived reads, and deterministic classifier composition are authoritative. |
| FT-013 post-review Task, conclusion, and context behavior | [Task And Approval HTTP](contracts/task-approval-http.md), [Companion Governance Data](domains/companion-governance.md), [Companion Governance HTTP](contracts/companion-governance-http.md), [Agent Chat Bus](contracts/agent-chat-bus.md), [Provider Profiles](contracts/agent-model-provider-profiles.md) | Approved Task creation stays in the caller-owned UoW; conclusions support open/unfocused state; approved summaries are derived; nested Task errors remain reachable; governance input is typed and non-authoritative. |
| FT-013 aggregate authority | [Companion Governance Data](domains/companion-governance.md), [Companion Governance State](states/companion-governance.md), [Companion Governance HTTP](contracts/companion-governance-http.md), [Companion Verification](testing/companion-governance.md) | Current proposal derives from unique pending-proposal authority; there is no reverse attention pointer; read integrity covers supported paths; proposal projection repair derives from authority state. |

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/constitution.md](constitution.md) | Local modular monolith with Svelte 5/SvelteKit Operator PWA under strict shared-boundary architecture guardrails; FT-000 runtime substrate defined. |
| source_of_truth | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/foundation.md](foundation.md) | Design precedence, runtime authority layers, verified FT-000 brownfield executable baseline gate, and substrate data boundaries defined. |
| module_boundaries | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) | Bounded modules defined inside one deployable monolith; Agent Runtime owns roster metadata, Plant create owns no introduction work, and Agent Chat Bus & UI Feed owns missing-row materialization only at the protected active Feed boundary. |
| user_scenarios | authoritative | [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/requirements.md](requirements.md) | Boss setup, Engineer operations, Safety Gate flow, and Companion governance covered. |
| constraints | authoritative | [.memory-bank/constitution.md](constitution.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Local-first, low-maintenance, safety, data authority, context hygiene, and no automated actuation. |
| non_goals | authoritative | [.memory-bank/prd.md](prd.md), [.memory-bank/requirements.md](requirements.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | SaaS, hosted sync, enterprise identity, multi-Farm, microservices, full dataset registry, and actuation excluded. |
| domain_model | authoritative | [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/domains/index.md](domains/index.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/domains/plant-history.md](domains/plant-history.md), [.memory-bank/states/index.md](states/index.md) | Global entities, shared native-UUID/non-cascading relation compatibility, foundation substrate, photo authority, Plant history projections, archived-Plant operational guard, and dataset lifecycle/trainability ownership are defined; exact feature fields live in registered subject specs. |
| data_flow | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/contracts/plant-feed-http.md](contracts/plant-feed-http.md), [.memory-bank/foundation.md](foundation.md) | Existing agent/Safety/task/governance flow remains; roster introductions use the separate authorized active Feed GET -> same-transaction guard -> missing UI rows -> unchanged page flow and never enter Bus/context. |
| storage | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/agent-chat-ui-feed-storage.md](domains/agent-chat-ui-feed-storage.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/foundation.md](foundation.md) | Existing UI rows and uniqueness remain; forward migration removes only presentation batch metadata/table and adds no replacement lifecycle state. Other PostgreSQL/artifact/audit boundaries are unchanged. |
| api_contracts | authoritative | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md), [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md), [.memory-bank/contracts/farm/plant-management-http.md](contracts/farm/plant-management-http.md), [.memory-bank/contracts/plant-feed-http.md](contracts/plant-feed-http.md), [.memory-bank/contracts/plant-operations-http.md](contracts/plant-operations-http.md), [.memory-bank/contracts/plant-history-http.md](contracts/plant-history-http.md), [.memory-bank/contracts/task-approval-http.md](contracts/task-approval-http.md) | Plant create/201 remains free of introduction work; protected active Feed GET owns missing-row materialization without changing response/order/cursor/error grammar. |
| event_message_contracts | authoritative | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md) | Existing MessageEnvelope/Bus/Safety/UI rules remain; introductions are presentation-only rows with both agent flags false and no Bus/context path. |
| agent_io_contracts | authoritative | [.memory-bank/contracts/agent-runtime-adapter.md](contracts/agent-runtime-adapter.md), [.memory-bank/contracts/agent-model-provider-profiles.md](contracts/agent-model-provider-profiles.md), [.memory-bank/contracts/companion-runtime.md](contracts/companion-runtime.md), [.memory-bank/contracts/agent-roster-bootstrap.md](contracts/agent-roster-bootstrap.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | Agent Runtime owns the canonical roster and deterministic metadata but no introduction persistence; registered typed provider boundaries and fail-closed unbound production behavior remain unchanged. |
| security_safety | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/contracts/plant-feed-http.md](contracts/plant-feed-http.md), [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md), [.memory-bank/states/plants/plant-and-access-lifecycle.md](states/plants/plant-and-access-lifecycle.md) | AD-008 remains; AD-010 additionally requires current identity/grant/active-Plant locks in the same transaction as lazy introduction writes and keeps archived reads/restore write-free. |
| testing_strategy | authoritative | [.memory-bank/testing/strategy.md](testing/strategy.md), [.memory-bank/testing/agent-runtime.md](testing/agent-runtime.md), [.memory-bank/testing/agent-chat-ui-feed.md](testing/agent-chat-ui-feed.md), [.memory-bank/testing/plant-operations.md](testing/plant-operations.md), [.memory-bank/runbooks/agent-runtime-providers.md](runbooks/agent-runtime-providers.md) | Existing deterministic runtime acceptance remains; Feed/migration verification proves sole trigger, same-UoW guard, missing-only idempotency, retained rows, no forbidden-trigger writes, unchanged public grammar, and retry. |
| deployment | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md), [.memory-bank/foundation.md](foundation.md) | Local loopback path remains; application startup performs no introduction reconciliation and recovery is an authorized active Feed retry. |
| risks | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/prd.md](prd.md) | Lazy Feed persistence may fail or race archive/revocation; same-transaction current guards plus `FEED_PERSISTENCE_FAILED` and retry are the accepted bounded recovery. |
| open_questions | authoritative | [.memory-bank/spec-backbone.md](spec-backbone.md), [.memory-bank/contracts/agent-model-provider-profiles.md](contracts/agent-model-provider-profiles.md), [.memory-bank/contracts/companion-runtime.md](contracts/companion-runtime.md) | No unresolved global/shared blocker remains; Finding 4 and the FT-013 provider-input policy are authoritative. |

## Handoff To /prd-to-features
- Ready: yes
- Required reads: [.memory-bank/prd.md](prd.md), [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/glossary.md](glossary.md).
- Stop conditions: PRD scope changes; Pre-PRD Spec Status becomes stale/blocked; new ambiguity appears around actors, Farm/Plant boundaries, Safety Gate authority, Companion governance authority, or provider-neutral agent-runtime requirements.

## Handoff To /spec-design
- Global Backbone Status: complete; the FT-013 typed governance-input decision,
  ordinary-task UoW phase, Finding 4 active-Feed materialization boundary, and
  all other current shared routes are authoritative.
- Backbone areas decided: architecture_style, source_of_truth, module_boundaries, ActorContext/authz, Farm/Plant data authority, photo artifact storage, timeline audit/export, Agent Chat Bus, MessageEnvelope, UI Feed, Plant state trust, Safety Gate/action lifecycle, Companion governance, dataset governance, testing, deployment.
- Authoritative specs: see .memory-bank/spec-index.md Spec Registry.
- L1-L3 context: [.memory-bank/requirements.md](requirements.md), [.memory-bank/epics/index.md](epics/index.md), and [.memory-bank/features/index.md](features/index.md).

## Handoff To /foundation-to-tasks
- Decision: required.
- Status: complete and verified; [.memory-bank/foundation.md](foundation.md) owns the current gate state and executable-baseline evidence.
- Downstream rule: product tasking must honor the Foundation gate recorded in the authoritative Foundation document.

## Handoff To /feature-to-tasks
- Ready: yes for feature tasking when the selected feature satisfies its
  current review and workflow gates; this handoff does not authorize execution
  or lifecycle transitions.
- FT-013 shared and feature-local design is complete. The single ordinary-task
  source union, caller-owned UoW phase, classification-only Companion
  governance hold, derived approved summary, and typed non-authoritative
  governance input are authoritative through the registered subject specs.
- FT-007 and FT-008 were reconciled through `/feature-to-tasks` and fresh
  task-plan review for Planning Revision 2. The resulting
  `TASK-046-T3-FT-008-W3` is terminal `done`; future FT-007 selected-endpoint
  work remains a separate deferred planning route.
- FT-002 Plant create and FT-016 Feed rendering are compatibility consumers:
  their public outcomes remain unchanged and do not require an independent
  design branch.
- Stop conditions: PRD scope changes, a new shared/global gap appears, or a
  feature design conflicts with the authoritative global backbone; route the
  shared decision back through `/spec-design`.

## Global Backbone Status
- Status: complete
- Planning Revision: 2
- Mode: strict_architecture_scaffold
- Architecture artifact strategy: single-file
- Not applicable areas:
  - separate_handwritten_openapi_yaml: not_applicable - generated OpenAPI should come from backend FastAPI/Pydantic-style schemas after implementation exists.
  - microservices_or_distributed_deployment: not_applicable - MVP uses a local modular monolith.
  - automated_device_actuation: not_applicable - physical actions create only human-performed tasks in MVP.
  - production_saas_sync: not_applicable - MVP remains local-first with `local_only` sync status.
- Notes: Foundation remains verified and its gate/status are unchanged.
  Planning Revision advanced exactly once from 1 to 2 for the durable Finding 4
  Plant-create/Agent Runtime/Feed/storage ownership change. Historical
  `done|failed` task records and their approvals remain unchanged;
  Planning Revision 2 review and TASK-046 closure completed the Finding 4
  implementation delta. FT-008 is `verified`; FT-007 remains `planned` for its
  deferred selected-endpoint milestone. No unresolved global/shared ambiguity
  remains.
