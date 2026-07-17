---
description: Pre-PRD spec framing, global SDD backbone state, and foundation routing.
status: active
last_updated: 2026-07-17
---
# SDD Spec Backbone

## Pre-PRD Spec Status
- Status: ready_for_prd
- Last updated: 2026-06-26
- Notes: Active PRD contains enough actor, scenario, domain, constraint, non-goal, boundary, lifecycle, and risk evidence for `/prd` decomposition. No pre-PRD blocker remains.

## Decomposition Inputs
- User scenarios: [.memory-bank/user-scenarios.md](user-scenarios.md) captures Boss setup, Engineer Plant operations, Safety Gate/action task flow, and Companion governance scenarios.
- Domain model: [.memory-bank/domains/core-domain.md](domains/core-domain.md) captures Account, Farm, FarmMembership, ActorContext, Plant, PlantAccessGrant, admin audit, photo/runtime/audit, agent, safety, governance, and dataset entities.
- Constraints: [.memory-bank/prd.md](prd.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/domains/core-domain.md](domains/core-domain.md) capture local-first, loopback default, one local Farm, PostgreSQL/read-model authority, UI Feed isolation, Safety Gate, real model-backed agent runtime, and no automated actuation.
- Non-goals: [.memory-bank/prd.md](prd.md) and [.memory-bank/user-scenarios.md](user-scenarios.md) capture no production SaaS, hosted/cloud sync as MVP requirement, billing, enterprise identity, multi-Farm tenancy, broad farm management, microservices, automated actuation, full dataset registry, or real fine-tuning.
- Risks: PRD/Product Brief risks are decomposition-relevant: authz enforced only in UI, governance approval confused with Safety Gate approval, Companion proposals leaking into agent context, agent fake/stub runtime paths, scope growth from Accounts/Farm/Admin.
- Boundary hints: [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) captures preliminary boundaries for ActorContext, admin, Plant operations, photo artifacts, timeline, Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, and dataset governance.
- Lifecycle hints: [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) captures Account/FarmMembership/Plant/PlantAccessGrant, daily check-in, photo artifact, agent output, physical-action proposal, CompanionProposal, DecisionRecord, and dataset candidate lifecycles.

## Open Design Questions
- None at the global/shared design level.
- `candidate_output` requires no Markdown/HTML/prompt recognizer: it is opaque
  untrusted normalized text, and syntax-looking content has no executable or
  authority semantics. Future Unicode presentation hardening, if needed, is a
  non-blocking UI concern rather than a candidate-output rejection policy.
- DeepSeek/Gemini model id, credential, and egress opt-in are execution inputs;
  FT-008/FT-011/FT-012 concrete design remains feature-owned.

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/constitution.md](constitution.md) | Local modular monolith with Svelte 5/SvelteKit Operator PWA under strict shared-boundary architecture guardrails; FT-000 runtime substrate defined. |
| source_of_truth | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/foundation.md](foundation.md) | Design precedence, runtime authority layers, verified FT-000 brownfield executable baseline gate, and substrate data boundaries defined. |
| module_boundaries | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md) | Bounded modules defined inside one deployable monolith; substrate dependency direction defined. |
| user_scenarios | authoritative | [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/requirements.md](requirements.md) | Boss setup, Engineer operations, Safety Gate flow, and Companion governance covered. |
| constraints | authoritative | [.memory-bank/constitution.md](constitution.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Local-first, low-maintenance, safety, data authority, context hygiene, and no automated actuation. |
| non_goals | authoritative | [.memory-bank/prd.md](prd.md), [.memory-bank/requirements.md](requirements.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | SaaS, hosted sync, enterprise identity, multi-Farm, microservices, full dataset registry, and actuation excluded. |
| domain_model | authoritative | [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/domains/index.md](domains/index.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/domains/plant-history.md](domains/plant-history.md), [.memory-bank/states/index.md](states/index.md) | Global entities, shared native-UUID/non-cascading relation compatibility, foundation substrate, photo authority, Plant history projections, archived-Plant operational guard, and dataset lifecycle/trainability ownership are defined; exact feature fields live in registered subject specs. |
| data_flow | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/foundation.md](foundation.md) | ActorContext -> state/artifacts/audit -> Bus/agents -> Safety/UI/tasks flow defined; FT-000 runtime smoke flow defined; projection/audit layers cannot become runtime or agent authority. |
| storage | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/foundation.md](foundation.md) | PostgreSQL/read model, shared UUID identity, non-cascading authority relations, DB/session/Alembic substrate, local filesystem artifacts, JSONL audit/export separation, and local bootstrap/runtime-root baseline defined. |
| api_contracts | authoritative | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md), [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md), [.memory-bank/contracts/farm/plant-management-http.md](contracts/farm/plant-management-http.md), [.memory-bank/contracts/plant-operations-http.md](contracts/plant-operations-http.md), [.memory-bank/contracts/plant-history-http.md](contracts/plant-history-http.md) | HTTP/API guardrails, FT-000 smoke, unchanged Plant-create compatibility, authoritative observation-limit rejection, and FT-006 Plant history boundary are defined. |
| event_message_contracts | authoritative | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md) | Pending opaque-text MessageEnvelope, project-owned classification, literal UI rendering, typed Bus quotation, guarded downstream writes, Timeline matrix, and archive no-replay rules are defined. |
| agent_io_contracts | authoritative | [.memory-bank/contracts/agent-runtime-adapter.md](contracts/agent-runtime-adapter.md), [.memory-bank/contracts/agent-model-provider-profiles.md](contracts/agent-model-provider-profiles.md), [.memory-bank/contracts/agent-roster-bootstrap.md](contracts/agent-roster-bootstrap.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | Sole ProviderRequestV1 allowlist, ordered AgentInputRecordV1 records/refs, strict model/outcome unions, opaque candidate-text boundary, UUIDv5 batch identity, atomic sink matrix, and active-Plant reconciliation boundary are defined. |
| security_safety | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md), [.memory-bank/states/plants/plant-and-access-lifecycle.md](states/plants/plant-and-access-lifecycle.md) | AD-008 and the strict classification matrix deny model-selected/content-selected authority, separate ordinary tasks from action_task, and require current guards at every downstream write. |
| testing_strategy | authoritative | [.memory-bank/testing/strategy.md](testing/strategy.md), [.memory-bank/testing/agent-runtime.md](testing/agent-runtime.md), [.memory-bank/testing/plant-operations.md](testing/plant-operations.md), [.memory-bank/runbooks/agent-runtime-providers.md](runbooks/agent-runtime-providers.md) | Exact request/input/outcome/event/batch assertions, opaque candidate acceptance, literal UI/typed Bus separation, adversarial classification compatibility, and the two accepted audited smoke outcomes are defined. |
| deployment | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md), [.memory-bank/foundation.md](foundation.md) | Local loopback first demo; Linux Mint local bootstrap/PostgreSQL path and runbook; optional protected LAN later; no SaaS/server sync. |
| risks | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/prd.md](prd.md) | Key architecture risks recorded. |
| open_questions | authoritative | [.memory-bank/spec-backbone.md](spec-backbone.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/foundation.md](foundation.md) | No global/shared design blocker remains; provider model/credential/egress values are execution inputs, and downstream feature-local details stay routed to their owning `/prd-to-tasks` runs. |

## Handoff To /prd
- Ready: yes
- Required reads: [.memory-bank/prd.md](prd.md), [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/glossary.md](glossary.md).
- Stop conditions: PRD scope changes; Pre-PRD Spec Status becomes stale/blocked; new ambiguity appears around actors, Farm/Plant boundaries, Safety Gate authority, Companion governance authority, or real agent-runtime/demo requirements.

## Handoff To /spec-design
- Global Backbone Status: complete.
- Backbone areas decided: architecture_style, source_of_truth, module_boundaries, ActorContext/authz, Farm/Plant data authority, photo artifact storage, timeline audit/export, Agent Chat Bus, MessageEnvelope, UI Feed, Plant state trust, Safety Gate/action lifecycle, Companion governance, dataset governance, testing, deployment.
- Authoritative specs: see .memory-bank/spec-index.md Spec Registry.
- L1-L3 context: [.memory-bank/requirements.md](requirements.md), [.memory-bank/epics/index.md](epics/index.md), and [.memory-bank/features/index.md](features/index.md).

## Handoff To /foundation-to-tasks
- Decision: required.
- Status: complete and verified; [.memory-bank/foundation.md](foundation.md) owns the current gate state and executable-baseline evidence.
- Downstream rule: product tasking must honor the Foundation gate recorded in the authoritative Foundation document.

## Handoff To /prd-to-tasks
- Ready: yes for feature-local `/prd-to-tasks FT-<NNN>` runs whose own
  clarification/design preflight passes.
- Current FT-008 outcome: feature-local Bus/UI envelopes, PostgreSQL
  persistence/reconciliation, protected Plant feed HTTP, context hygiene, and
  verification are complete; TASK-032 and TASK-033 are `done` with independent
  functional PASS and per-task semantic-pass evidence. FT-008 is `verified`.
- Latest pre-execution `/review-tasks-plan FT-008` is `APPROVE`. The scheduler
  will delegate the final task-plan review separately; this sync does not run
  or pre-claim that review.
- FT-007 note: TASK-030/TASK-031 are done under the explicit owner deferral of
  credentialed real-provider smoke; that residual UAT remains unclaimed and
  does not block FT-008 deterministic sink/context work.
- Current FT-009 planning outcome: feature-local real-photo Vision Observation,
  Plant State PostgreSQL authority, protected trust reads/review, conflicts,
  promotion, and verification contracts are complete. TASK-034 and TASK-035
  are indexed `planned`; product-agent real-model acceptance remains an
  execution/UAT target and is not pre-claimed by planning.
- Current FT-011 planning outcome: feature-local real model-backed Safety
  classification, immutable PostgreSQL classification/action decisions,
  `approval_input=2h`, exact manual/unsupported action taxonomy, safe pending
  UI projection, and verification contracts are complete. TASK-037 and
  TASK-038 are indexed `planned`; FT-012 remains the owner of human decisions
  and every later task/follow-up state.
- Stop conditions: PRD scope changes, a new shared/global gap appears, or a
  feature design conflicts with the authoritative global backbone; route the
  shared decision back through `/spec-design`.

## Global Backbone Status
- Status: complete
- Mode: strict_architecture_scaffold
- Architecture artifact strategy: single-file
- Not applicable areas:
  - separate_handwritten_openapi_yaml: not_applicable - generated OpenAPI should come from backend FastAPI/Pydantic-style schemas after implementation exists.
  - microservices_or_distributed_deployment: not_applicable - MVP uses a local modular monolith.
  - automated_device_actuation: not_applicable - physical actions create only human-performed tasks in MVP.
  - production_saas_sync: not_applicable - MVP remains local-first with `local_only` sync status.
- Notes: Foundation remains verified. FT-008 feature-local design and both
  execution waves are complete and independently verified. FT-009 feature-local
  design is complete and its two T3 tasks await review/execution; no real-model
  product-agent acceptance is claimed yet. FT-011 feature-local design is
  complete and its two T3 tasks await review/execution; no Safety Gate
  real-model acceptance is claimed yet. Dataset Governance now has one
  lifecycle and one derived trainability authority; FT-014 exact persistence
  and evidence policy remain feature-local.
