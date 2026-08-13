---
description: Pre-PRD spec framing, global SDD backbone state, and foundation routing.
status: active
last_updated: 2026-08-14
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
- `AD-011` closes the FT-014 shared runtime branch: canonical roster agents
  `dataset_governance` and `training_data_curator` use the only registered
  advisory-only Agent Runtime route. Their strict requests are registered in
  typed egress, their competence-local outcome creates no MessageEnvelope,
  Safety, Bus, or UI effect, and Dataset Governance retains every mutable
  advisory/lifecycle/trainability write.
- The Timeline registry now defines exact Dataset Candidate create/evidence-
  link/review events plus the dedicated Dataset Agent attempt event, including
  no-I/O outcomes, cardinality, redaction, append failure, and
  append-success/commit-failure noise semantics.
- The canonical Boundary Map now contains the required detailed Modules,
  Dependency Graph, and Inline Contracts structure. It records Dataset
  evidence creation, follow-up evidence association, and the advisory-only
  runtime edge without promoting code roots to task write boundaries.
- `AD-012` closes the shared Product Surface Redaction branch. Runtime
  Substrate owns one sanitization primitive, while each product capability
  retains its strict payload, safe-error, and fail-closed output authority
  before persistence, append, publication, serialization, export, provider
  egress, or browser capture.
- Brownfield current-state evidence is narrower than the accepted target:
  `backend/app/core/redaction.py` plus existing auth, Timeline, and Plant
  History usage prove the reusable substrate and some owner coverage. The
  remaining product surfaces are downstream implementation/planning deltas;
  they neither redefine the target nor require new Foundation work.

## FT-013 Shared Design Decisions

| Concern | Canonical sources | Durable decision |
|---|---|---|
| Ordinary Task creation from classified output or approved governance decision | [Task And Approval HTTP](contracts/task-approval-http.md), [Task lifecycle](states/task-follow-up-lifecycle.md), [Task data](domains/task-approval-outcomes.md) | One `create_ordinary_task` seam owns the closed source union, source refs, fingerprints, results, current guards, and branch-specific UoW ownership. |
| Companion classification without premature ordinary dispatch | [Safety Action Lifecycle](states/safety-action-lifecycle.md), [Safety Gate Runtime](contracts/safety-gate-runtime.md), [MessageEnvelope](contracts/message-envelope.md), [Bus](contracts/agent-chat-bus.md), [UI Feed](contracts/ui-feed.md) | The server derives `ordinary_dispatch|companion_governance_hold`; the route adds no persisted schema and Companion-held output cannot dispatch an ordinary Task. |
| FT-013 HTTP views, errors, evidence selection, concurrency, and ref/read grammar | FT-013 registered feature-local contracts, data specs, and testing specs | Exact schemas and error mapping, one-row evidence selection, distinct-run serialization, canonical refs/derived reads, and deterministic classifier composition are authoritative. |
| FT-013 post-review Task, conclusion, and context behavior | [Task And Approval HTTP](contracts/task-approval-http.md), [Companion Governance Data](domains/companion-governance.md), [Companion Governance HTTP](contracts/companion-governance-http.md), [Agent Chat Bus](contracts/agent-chat-bus.md), [Provider Profiles](contracts/agent-model-provider-profiles.md) | Approved Task creation stays in the caller-owned UoW; conclusions support open/unfocused state; approved summaries are derived; nested Task errors remain reachable; governance input is typed and non-authoritative. |
| FT-013 aggregate authority | [Companion Governance Data](domains/companion-governance.md), [Companion Governance State](states/companion-governance.md), [Companion Governance HTTP](contracts/companion-governance-http.md), [Companion Verification](testing/companion-governance.md) | Current proposal derives from unique pending-proposal authority; there is no reverse attention pointer; read integrity covers supported paths; proposal projection repair derives from authority state. |

## FT-014 Shared Design Decisions

| Concern | Canonical sources | Durable decision |
|---|---|---|
| Dataset Agents outcome route | [AD-011](architecture/system-architecture.md#ad-011---dataset-agents-use-a-registered-advisory-only-runtime-route), [Agent Runtime](contracts/agent-runtime-adapter.md#registered-advisory-only-exception), [Provider Boundary](contracts/agent-model-provider-profiles.md#registered-advisory-only-result-route), [Dataset Agents](contracts/dataset-agents-runtime.md#registered-advisory-only-exception) | Only the two canonical Dataset Agents use `dataset_advisory_v1`; they reuse shared fail-closed provider/current-guard infrastructure but return a strict advisory outcome and never create MessageEnvelope/Safety/Bus/UI effects. |
| Dataset Timeline matrix | [Timeline Event](contracts/timeline-event.md#dataset-candidate-payload-summaries), [Dataset Agent event](contracts/timeline-event.md#dataset_agent_runtime_decided-payload-summary) | Candidate create/evidence-link/review events and every accepted Dataset Agent attempt have exact registered identities, redacted summaries, cardinality, failure behavior, and non-authoritative audit-noise semantics. |
| Detailed module topology | [Boundary Map](contracts/boundary-map.md#modules), [Dependency Graph](contracts/boundary-map.md#dependency-graph) | Dataset source owners call the Dataset Governance creation/association seams; Dataset Governance consumes Agent Runtime Core only through the registered advisory exception and owns all mutable Dataset state. |

## FT-015 Shared Design Decisions

| Concern | Canonical sources | Durable decision |
|---|---|---|
| Product output redaction ownership | [AD-012](architecture/system-architecture.md#ad-012---product-output-redaction-is-owner-enforced-through-one-shared-substrate), [Product Surface Redaction](contracts/product-surface-redaction.md#surface-rules), [Boundary Map](contracts/boundary-map.md#product-surface-redaction) | Runtime Substrate owns the shared primitive only. Every semantic owner keeps its strict schema/allowlist and sanitizes or rejects the output copy before crossing its boundary; source credentials and domain authority never move into the helper. |
| FT-015 backend and FT-016 presentation handoff | [Photo Intake HTTP](contracts/photo-intake-http.md#storage-status-behavior), [Product Surface Redaction](contracts/product-surface-redaction.md#surface-rules), [FT-015](features/FT-015-local-security-privacy-storage-prompt.md), [FT-016](features/FT-016-web-app-pwa-operator-surface-first-demo.md) | FT-015 owns photo-pressure accounting and the protected stateless status contract. FT-016 owns transient Svelte presentation and future browser capture, consumes both canonical contracts directly, and gains no storage, upload, or sync authority. |

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/constitution.md](constitution.md) | Local modular monolith with Svelte 5/SvelteKit Operator PWA under strict shared-boundary architecture guardrails; FT-000 runtime substrate defined. |
| source_of_truth | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/foundation.md](foundation.md) | Design precedence, runtime authority layers, verified FT-000 brownfield executable baseline gate, and substrate data boundaries defined. |
| module_boundaries | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/contracts/product-surface-redaction.md](contracts/product-surface-redaction.md) | Bounded modules remain inside one deployable monolith. Runtime Substrate owns shared settings/redaction primitives only; product consumers retain payload, safe-error, persistence, publication, export, provider-request, and capture authority through explicit Product Surface Redaction edges. |
| user_scenarios | authoritative | [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/requirements.md](requirements.md) | Boss setup, Engineer operations, Safety Gate flow, and Companion governance covered. |
| constraints | authoritative | [.memory-bank/constitution.md](constitution.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Local-first, low-maintenance, safety, data authority, context hygiene, and no automated actuation. |
| non_goals | authoritative | [.memory-bank/prd.md](prd.md), [.memory-bank/requirements.md](requirements.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | SaaS, hosted sync, enterprise identity, multi-Farm, microservices, full dataset registry, and actuation excluded. |
| domain_model | authoritative | [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/domains/index.md](domains/index.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/domains/plant-history.md](domains/plant-history.md), [.memory-bank/states/index.md](states/index.md) | Global entities, shared native-UUID/non-cascading relation compatibility, foundation substrate, photo authority, Plant history projections, archived-Plant operational guard, and dataset lifecycle/trainability ownership are defined; exact feature fields live in registered subject specs. |
| data_flow | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/contracts/product-surface-redaction.md](contracts/product-surface-redaction.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/contracts/plant-feed-http.md](contracts/plant-feed-http.md), [.memory-bank/contracts/dataset-agents-runtime.md](contracts/dataset-agents-runtime.md), [.memory-bank/foundation.md](foundation.md) | Existing agent/Safety/task/governance, active-Feed introduction, and Dataset advisory flows remain. AD-012 additionally requires each semantic owner to sanitize or reject the output copy before persistence, append, publication, serialization, export, provider egress, or capture. |
| storage | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/agent-chat-ui-feed-storage.md](domains/agent-chat-ui-feed-storage.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/foundation.md](foundation.md) | PostgreSQL, local artifacts, Timeline, and UI storage ownership are unchanged. FT-015 photo-pressure accounting reads authoritative accepted-photo metadata and creates no sync, upload, acknowledgment, or replacement lifecycle state. |
| api_contracts | authoritative | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md), [.memory-bank/contracts/product-surface-redaction.md](contracts/product-surface-redaction.md), [.memory-bank/contracts/photo-intake-http.md](contracts/photo-intake-http.md), [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md), [.memory-bank/contracts/farm/plant-management-http.md](contracts/farm/plant-management-http.md), [.memory-bank/contracts/plant-feed-http.md](contracts/plant-feed-http.md), [.memory-bank/contracts/plant-operations-http.md](contracts/plant-operations-http.md), [.memory-bank/contracts/plant-history-http.md](contracts/plant-history-http.md), [.memory-bank/contracts/task-approval-http.md](contracts/task-approval-http.md) | Existing API authority remains. Safe errors redact before emission, and FT-015 adds one protected read-only storage-status contract consumed by FT-016 without a prompt-mutation endpoint. |
| event_message_contracts | authoritative | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md) | Generic MessageEnvelope/Bus/Safety/UI rules remain; introductions are presentation-only, and the Dataset advisory exception uses only its dedicated Timeline attempt event plus candidate audit events. |
| agent_io_contracts | authoritative | [.memory-bank/contracts/agent-runtime-adapter.md](contracts/agent-runtime-adapter.md), [.memory-bank/contracts/agent-model-provider-profiles.md](contracts/agent-model-provider-profiles.md), [.memory-bank/contracts/product-surface-redaction.md](contracts/product-surface-redaction.md), [.memory-bank/contracts/dataset-agents-runtime.md](contracts/dataset-agents-runtime.md), [.memory-bank/contracts/companion-runtime.md](contracts/companion-runtime.md), [.memory-bank/contracts/agent-roster-bootstrap.md](contracts/agent-roster-bootstrap.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | Existing runtime/provider composition remains. Every competence request keeps its exact typed allowlist and excludes credentials, raw ActorContext, cookies, headers, UI text, and provider history before provider I/O. |
| security_safety | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/contracts/evidence-redaction.md](contracts/evidence-redaction.md), [.memory-bank/contracts/product-surface-redaction.md](contracts/product-surface-redaction.md), [.memory-bank/contracts/auth/session-security.md](contracts/auth/session-security.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md), [.memory-bank/states/plants/plant-and-access-lifecycle.md](states/plants/plant-and-access-lifecycle.md) | AD-012 extends the verified Foundation redaction baseline across product outputs while preserving every owner schema and source credential. Existing Safety, authorization, archive, and no-authority rules remain unchanged. |
| testing_strategy | authoritative | [.memory-bank/testing/strategy.md](testing/strategy.md), [.memory-bank/testing/local-privacy-storage.md](testing/local-privacy-storage.md), [.memory-bank/testing/agent-runtime.md](testing/agent-runtime.md), [.memory-bank/testing/agent-chat-ui-feed.md](testing/agent-chat-ui-feed.md), [.memory-bank/testing/dataset-governance.md](testing/dataset-governance.md), [.memory-bank/runbooks/agent-runtime-providers.md](runbooks/agent-runtime-providers.md) | Risk-based deterministic acceptance remains. One configured corpus proves actual owner outputs, unchanged source credentials, stable safe failures, exact photo-pressure boundaries, and future FT-016 capture compliance. |
| deployment | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md), [.memory-bank/foundation.md](foundation.md) | Supported deployment remains loopback with `local_only`; optional LAN is not introduced by FT-015. Startup performs no introduction or prompt-state reconciliation. |
| risks | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/contracts/product-surface-redaction.md](contracts/product-surface-redaction.md), [.memory-bank/prd.md](prd.md) | Cross-surface auth leakage and accidental sanitizer authority are addressed by strict owner allowlists, one shared primitive, pre-output enforcement, source immutability, and fail-closed safe errors. Existing Feed-race recovery remains unchanged. |
| open_questions | authoritative | [.memory-bank/spec-backbone.md](spec-backbone.md), [.memory-bank/contracts/product-surface-redaction.md](contracts/product-surface-redaction.md), [.memory-bank/contracts/agent-model-provider-profiles.md](contracts/agent-model-provider-profiles.md), [.memory-bank/contracts/dataset-agents-runtime.md](contracts/dataset-agents-runtime.md) | No unresolved global/shared blocker remains. AD-012 and the FT-015/FT-016 consumer boundary are authoritative; provider/model selection remains intentionally deferred to its existing future milestone. |

## Handoff To /prd-to-features
- Ready: yes
- Required reads: [.memory-bank/prd.md](prd.md), [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/glossary.md](glossary.md).
- Stop conditions: PRD scope changes; Pre-PRD Spec Status becomes stale/blocked; new ambiguity appears around actors, Farm/Plant boundaries, Safety Gate authority, Companion governance authority, or provider-neutral agent-runtime requirements.

## Handoff To /spec-design
- Global Backbone Status: complete; the FT-013 typed governance-input decision,
  ordinary-task UoW phase, Finding 4 active-Feed materialization boundary,
  AD-011 Dataset advisory route, Dataset Timeline matrix, and current Boundary
  Map topology are authoritative. AD-012 now also governs shared product-output
  redaction and the FT-015/FT-016 consumer boundary.
- Backbone areas decided: architecture_style, source_of_truth, module_boundaries, ActorContext/authz, Farm/Plant data authority, photo artifact storage, timeline audit/export, Agent Chat Bus, MessageEnvelope, UI Feed, Plant state trust, Safety Gate/action lifecycle, Companion governance, dataset governance, testing, deployment.
- Authoritative specs: see .memory-bank/spec-index.md Spec Registry.
- L1-L3 context: [.memory-bank/requirements.md](requirements.md), [.memory-bank/epics/index.md](epics/index.md), and [.memory-bank/features/index.md](features/index.md).

## Handoff To /foundation-to-tasks
- Decision: required.
- Status: complete and verified; [.memory-bank/foundation.md](foundation.md) owns the current gate state and executable-baseline evidence.
- Post-revision audit: complete on 2026-08-13. `/foundation-to-tasks` found no
  executable substrate gap, preserved TASK-004 and existing FT-000 history,
  and created no Foundation task.
- Downstream rule: product tasking must honor the Foundation gate recorded in the authoritative Foundation document.

## Handoff To /feature-to-tasks
- Ready: yes; the required post-revision `/foundation-to-tasks` audit completed
  without a substrate gap. This handoff does not authorize execution or
  lifecycle transitions.
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
- FT-014 shared and feature-local design is complete. Its reconciled
  TASK-047..055 plus TASK-057 queue received fresh task-plan APPROVE for
  Planning Revision 3 and passed the strict readiness gate, and has since been
  fully executed to terminal `done`; the W6 remediation cards
  (TASK-058/059/060) are likewise terminal `done` and the feature-level T2
  completion gate recorded `SEMANTIC_VERDICT: semantic-pass`.
- FT-016 feature-local design is complete for Planning Revision 4. The
  registered Operator PWA presentation contract, read-only Dataset Governance
  HTTP contract, two leaf presentation edges, FT-015 status/prompt/capture
  consumer handoffs, and deterministic first-demo testing matrix ground the
  rebuilt planned TASK-080..110 queue without moving backend authority into
  the PWA. Provider commands/reads and the two final gates have atomic claim
  ownership; fresh task-plan review remains required before execution.
- Planning Revision 4 makes every indexed product task-plan review through
  Revision 3 stale while preserving every task status and historical evidence.
  Run `/feature-to-tasks --all` to reconcile all product planning against
  AD-012, including FT-015 execution cohesion/direct handoffs and the FT-016
  canonical consumer links, then run `/review-tasks-plan --all`.
- Stop conditions: PRD scope changes, a new shared/global gap appears, or a
  feature design conflicts with the authoritative global backbone; route the
  shared decision back through `/spec-design`.

## Global Backbone Status
- Status: complete
- Planning Revision: 4
- Mode: strict_architecture_scaffold
- Architecture artifact strategy: single-file
- Not applicable areas:
  - separate_handwritten_openapi_yaml: not_applicable - generated OpenAPI should come from backend FastAPI/Pydantic-style schemas after implementation exists.
  - microservices_or_distributed_deployment: not_applicable - MVP uses a local modular monolith.
  - automated_device_actuation: not_applicable - physical actions create only human-performed tasks in MVP.
  - production_saas_sync: not_applicable - MVP remains local-first with `local_only` sync status.
- Notes: Foundation remains verified and its gate/status are unchanged.
  Planning Revision advanced exactly once from 3 to 4 on 2026-08-13 because
  AD-012 promotes Product Surface Redaction and its cross-module Runtime
  Substrate dependency topology into the durable global target used by task
  planning. Historical task lifecycle/evidence remains unchanged; every
  product task-plan review through Revision 3 is stale until all-feature
  reconciliation and fresh review complete.
  No unresolved global/shared ambiguity remains.
