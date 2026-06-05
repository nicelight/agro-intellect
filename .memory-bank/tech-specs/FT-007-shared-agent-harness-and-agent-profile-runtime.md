---
description: Feature-local SDD tech spec for FT-007 shared AgentHarness, AgentProfile runtime, tools, permissions, observations, traces, evals, and budgets.
status: active
feature_id: FT-007
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-007-shared-agent-harness-and-agent-profile-runtime.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/safety-gate.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - agents-best-practices
---
# FT-007 Shared AgentHarness And AgentProfile Runtime Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for one
project-owned provider-neutral `AgentHarness`, explicit `AgentProfile` records, the
model/tool loop, schema validation, runtime permission decisions, approval pauses,
structured observations, traces, evals, and budgets.

This spec applies `agents-best-practices`: the model proposes; the harness validates,
authorizes, executes or pauses, records, and returns structured observations.

## Scope

In scope:

- shared `AgentHarness` runtime boundary for all product agents;
- `AgentProfile` schema refinements and initial profile registry;
- canonical harness run loop and state transitions;
- narrow typed tool registry policy;
- permission matrix and approval record handoff;
- structured observation requirements for success, denial, approval pause, timeout,
  provider failure, validation error, and abort;
- trace/eval evidence and budget profiles;
- Agno boundary as optional execution layer only.

Out of scope:

- exact product-agent prompt bodies and provider/model choices owned by FT-010;
- AgentMemoryRecord schema/retrieval/compaction details owned by FT-008;
- MessageEnvelope/Bus/UI Feed payload variants owned by FT-009;
- Safety Gate action taxonomy/approval unlock owned by FT-012 and FT-013;
- broad multi-agent workflow orchestration before a single shared loop proves
  insufficient.

## AgentProfile Shape

Every product agent is a profile inside the shared harness. Minimum feature-local
profile semantics:

```yaml
agent_id: companion | vision_observation | plant_state | hydroponics_advisor | task_follow_up | safety_gate | dataset_governance | training_data_curator
display_name: string
profile_version: string
status: defined | active | disabled | deprecated
competence_boundary: string
forbidden_outputs: []
allowed_context_sources: []
allowed_bus_event_families: []
allowed_tools: []
allowed_claim_types: []
runtime_decisions_allowed: []
memory_scope:
  farm_scoped: true
  plant_scoped: true
  agent_scoped: true
risk_class: read_only | draft_only | approval_gated
budget_profile: interactive_light | model_vision | safety_strict | background_low
trace_policy: standard | safety_sensitive | privacy_sensitive
eval_suite_refs: []
schema_version: string
```

Rules:

- disabled or deprecated profiles cannot start new product-agent runs;
- profile changes are versioned enough for trace/eval attribution;
- profile tools, context sources, and output contracts are allowlists, not suggestions;
- no profile receives UI Feed replay, raw chat as fact, hidden provider memory, raw
  model reasoning, unapproved governance content, secrets, or auth material;
- Agno configuration cannot grant authority beyond the project profile and harness
  policy.

## Initial Runtime Profiles

Initial profiles are registered with minimum authority. `risk_class` uses only the
AgentProfile enum `read_only | draft_only | approval_gated`; safety, privacy, and
background-execution nuance is expressed through `trace_policy`, `budget_profile`, and
notes.

| AgentProfile | Profile Risk Class | Runtime Policy Notes | Initial Allowed Output |
|---|---|---|---|
| `companion` | draft_only | `trace_policy=standard`, `budget_profile=interactive_light`. | Governance coordination proposals through typed state only. |
| `vision_observation` | read_only | `trace_policy=privacy_sensitive`, `budget_profile=model_vision`. | Photo quality and visual observations from authorized accepted photo refs. |
| `plant_state` | read_only | `trace_policy=standard`, `budget_profile=interactive_light`. | Trust-labeled state analysis, unknown/probable/conflict, no confirmation alone. |
| `hydroponics_advisor` | approval_gated | `trace_policy=safety_sensitive`, `budget_profile=interactive_light`; Safety Gate required for physical-action wording. | Cautious analysis and Safety Gate-routed physical-action wording. |
| `task_follow_up` | draft_only | `trace_policy=standard`, `budget_profile=interactive_light`. | Check, measurement, follow-up, and approved-action task proposals through backend rules. |
| `safety_gate` | approval_gated | `trace_policy=safety_sensitive`, `budget_profile=safety_strict`; backend policy remains authority. | Gate classification/route evidence only. |
| `dataset_governance` | draft_only | `trace_policy=privacy_sensitive`, `budget_profile=background_low`; may propose FT-016 dataset transitions, backend commits them. | Dataset lifecycle refs, transition proposals, and non-trainable default checks. |
| `training_data_curator` | draft_only | `trace_policy=privacy_sensitive`, `budget_profile=background_low`; enabled only for delayed curation. | Delayed evidence selection proposals only when enabled; usually silent. |

Task decomposition may activate profiles incrementally, but must not create separate
ungoverned harnesses.

## Canonical Run Loop

Each `AgentHarnessRun` follows the global lifecycle:

1. resolve ActorContext and Plant/Farm scope;
2. build permission-aware context through the shared context builder;
3. select visible tools from AgentProfile plus runtime policy;
4. call the model/provider through a provider-neutral adapter;
5. parse a final output or `ToolActionProposal`;
6. validate schema and reject unknown properties;
7. evaluate permission and approval policy outside the model;
8. execute, deny, ask, pause for approval, run as draft, or abort;
9. return exactly one `StructuredObservation` for every proposal;
10. record trace/eval evidence, budget use, and refs;
11. repeat within budget or stop with final status.

Loop rules:

- the model never executes tools directly;
- every tool/action proposal receives one observation, including denial, timeout,
  approval pause, validation error, provider failure, budget stop, or abort;
- risky side effects split draft/propose from commit/approve;
- final output is grounded in structured observations and allowed context;
- missing provider configuration fails clearly and cannot silently fall back to fake
  product-agent output.

## Tool Registry Policy

Tools are narrow domain contracts. Minimum tool metadata:

```yaml
name: string
purpose: string
input_schema_ref: string
output_schema_ref: string
risk_class: read_only | compute_only | draft_only | write_local | write_internal | identity_access | safety_sensitive | process_execution | network_open_world | destructive | privileged_admin
side_effects: none | draft | write | approval_pause | external
resource_scope: farm | plant | account | photo | task | governance | dataset | trace
permission_policy: string
timeout_seconds: number
max_result_chars: number
retry_policy: none | safe_idempotent_only
audit_policy: trace_only | audit_record | safety_audit
```

Forbidden tools:

- `execute_anything`;
- unrestricted SQL/database writes;
- arbitrary HTTP/API caller;
- unrestricted filesystem or process execution;
- direct external send;
- direct physical actuation;
- broad connector inventory exposed to the model;
- hidden provider memory read/write as product memory.

Tool arguments are strict, typed, locally validated, and reject unknown properties.
Tool results are bounded structured observations with refs for large artifacts.

## Permission Matrix

Default FT-007 permission behavior:

| Risk Class | Default Decision |
|---|---|
| `read_only`, `compute_only` | Allow only inside ActorContext, PlantAccessGrant, profile, and result-size limits. |
| `draft_only` | Allow proposal/draft creation; no commit without backend rule. |
| `write_local`, `write_internal` | Allow only when profile and backend policy explicitly permit; otherwise deny or ask. |
| `identity_access`, `privileged_admin` | Boss/admin authority and durable audit required; no model self-approval. |
| `safety_sensitive` | Route through Safety Gate and human approval where physical action is involved. |
| `process_execution`, `network_open_world`, `destructive` | Deny in MVP unless a later active spec creates a sandboxed allowlist. |

Each decision records redacted args or argument hash, ActorContext ref, resource scope,
PlantAccessGrant result, policy rule, approver when present, timestamp, and trace ref.

## Structured Observation

Minimum observation semantics:

```yaml
observation_id: string
run_id: string
proposal_id: string | null
status: success | denied | approval_required | error | aborted
type: string
summary: string
evidence_refs: []
next_valid_actions: []
trace_ref: string
redaction_status: redacted | no_sensitive_fields
```

Observation rules:

- no hidden reasoning, raw provider output, secrets, auth material, or oversized blobs;
- errors include safe next actions;
- approval pauses are durable and scoped to the exact proposal;
- observations visible to the model are bounded and trust-labeled where relevant.

## Trace, Evals, And Budgets

Every run records operational trace refs without hidden reasoning:

- run id, session id, actor/farm/plant scope;
- AgentProfile id/version and prompt/tool bundle refs;
- model/provider/settings and missing-config/provider failure status;
- tools visible and proposals received;
- validation results, permission decisions, approvals, observations;
- context size, token/cost/latency, budget use, retry counts;
- final status and safe next action.

Minimum budget profiles:

| Budget Profile | Intended Use | Constraints |
|---|---|---|
| `interactive_light` | Companion, Plant State, Advisor text flows | Low model turns, low tool calls, bounded latency and result size. |
| `model_vision` | Vision over accepted photo refs | Allows larger input/result budget for authorized photo data only. |
| `safety_strict` | Safety Gate participant and physical-action routing | No unsafe retries, exact approval pause, fail closed. |
| `background_low` | Dataset/training-data curation when enabled | Low priority, explicit stop condition, no user-visible action by itself. |

Required eval families for FT-007:

- unknown tool;
- invalid args;
- permission denial;
- approval bypass attempt;
- prompt-injection-like text in user/uploaded data;
- UI Feed/unapproved proposal leakage attempt;
- provider unavailable and missing provider config;
- budget stop and false success claim;
- no fake runtime/demo fallback.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- AgentProfile registry/list/detail;
- start AgentHarnessRun for an authorized profile and Plant scope;
- submit/handle tool proposal inside the loop;
- record permission decision and structured observation;
- pause/resume from approval result;
- read redacted trace summary for authorized diagnostics;
- run harness eval fixture set.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-007 can be considered implemented:

- every product agent is registered as an AgentProfile in one shared AgentHarness;
- separate ungoverned product-agent harness entry points are absent;
- unknown tools and invalid arguments produce structured observations;
- every proposal receives exactly one observation;
- permission decision happens before every side effect;
- risky actions pause for exact scoped approval and cannot be self-approved by model;
- budget exhaustion stops with clear status and next safe action;
- traces record operational events without hidden reasoning or secrets;
- missing provider configuration does not produce fake successful agent behavior;
- Agno output/events/memory cannot bypass project-owned validation, permission, or
  publication contracts.

## Open Questions

No blocker for `/prd-to-tasks FT-007`. Exact provider adapter class names, initial
numeric budgets, profile storage table names, and eval fixture file layout can be
decided during task decomposition as long as the shared-harness, narrow-tool,
permission, observation, trace, and no-fake-runtime constraints hold.
