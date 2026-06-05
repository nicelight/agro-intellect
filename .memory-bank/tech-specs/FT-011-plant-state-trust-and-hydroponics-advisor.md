---
description: Feature-local SDD tech spec for FT-011 Plant State trust statuses, freshness handoff, missing-data behavior, advisor output, and Safety Gate routing.
status: active
feature_id: FT-011
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-011-plant-state-trust-and-hydroponics-advisor.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/safety-gate.md
  - .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
  - .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-010-real-model-backed-product-agent-profiles.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - agents-best-practices
---
# FT-011 Plant State Trust And Hydroponics Advisor Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for Plant
State trust status mapping, freshness handoff, missing/stale-data behavior,
Hydroponics Advisor output contracts, first-demo visibility, and Safety Gate routing
for physical-action wording.

This spec applies `agents-best-practices`: the Plant State and Hydroponics Advisor
profiles propose analysis/output; the harness validates, permission-checks, routes,
records observations/traces, and never lets model hypotheses become authority by
prompt convention.

## Scope

In scope:

- Plant State trust status mapping for first-demo state values;
- freshness handoff for pH/EC and other evidence used by advisor behavior;
- missing, stale, conflicting, and unauthorized evidence behavior;
- Hydroponics Advisor output contract and safe wording rules;
- MessageEnvelope/Bus/UI handoff for clarifications, hypotheses, recommendations, and
  safety routes;
- no-promotion rules for agent hypotheses and memory;
- verification targets for cautious advisor behavior.

Out of scope:

- core runtime state authority and timeline/history mechanics owned by FT-006;
- context builder and AgentMemoryRecord retrieval owned by FT-008;
- real provider/model activation owned by FT-010;
- detailed Safety Gate taxonomy, approval decision states, approver UX, action-task
  unlock, and follow-up outcomes owned by FT-012 and FT-013;
- automated actuation, device commands, sensor runtime dependency, crop-specific dosing
  engine, or expert agronomy knowledge base beyond the bounded first-demo advisory
  behavior.

## Inputs

Plant State and Hydroponics Advisor runs may consume only context-builder-provided,
permission-scoped inputs:

- current `PlantStateSnapshot` and history refs from FT-006;
- CheckIn, Observation, and ManualMeasurement refs from FT-004;
- accepted photo/catalog/manifest refs and valid Vision Observation outputs from FT-005
  and FT-010 where available;
- validated MessageEnvelope/Bus refs from FT-009;
- allowed AgentMemoryRecord refs from FT-008;
- approved governance summaries only when later features create them;
- Safety Gate policy refs for routing, not approval substitution.

Forbidden inputs remain UI Feed replay, raw chat as fact, raw provider output, hidden
reasoning, provider memory, unapproved proposals, admin UI text, timeline replay as
authority, and secrets/auth material.

## Plant State Trust Mapping

FT-011 uses the global `PlantStateValue` statuses:

| Status | Meaning | Promotion Rule |
|---|---|---|
| `confirmed_updated` | Current value was explicitly updated by validated human input, measurement, review, or follow-up evidence. | Requires backend validation and human/follow-up evidence; agent output alone cannot create it. |
| `confirmed_unchanged` | Human/review/follow-up evidence explicitly confirms no relevant change. | Requires evidence and review/follow-up path; agent output alone cannot create it. |
| `assumed_unchanged` | Prior confirmed value is carried forward without fresh confirmation. | Allowed only with source ref and stale/unknown freshness label where relevant. |
| `probable` | Agent or incomplete evidence suggests a state but confirmation is missing. | May be proposed by Plant State Agent; remains non-confirmed. |
| `unknown` | Required evidence is missing, unauthorized, stale beyond use, or unavailable. | Must be explicit; do not silently reuse absent data. |
| `conflict` | Evidence contradicts other evidence or memory/history disagrees with current runtime state. | Must preserve conflicting refs and avoid model-only resolution. |

Rules:

- raw model output, AgentMemoryRecord, photo manifest, UI text, or timeline replay cannot
  create confirmed state;
- valid Vision Observation may support `probable`, `unknown`, or `conflict` but cannot
  diagnose or confirm by itself;
- human-entered pH/EC values can become evidence after backend validation, but
  freshness and Safety Gate rules still apply;
- conflict resolution requires human review, follow-up evidence, or later owning rules.

## Freshness Handoff

Freshness labels are handoff metadata. They do not authorize physical action by
themselves.

Minimum FT-011 behavior:

- pH/EC analysis freshness follows the Safety Gate default of up to 24 hours unless a
  later active spec narrows it;
- pH/EC physical-action approval freshness follows the Safety Gate default of up to 2
  hours, but FT-011 only routes to Safety Gate and does not approve;
- missing pH or EC creates `unknown` state for the missing value and a clarification or
  measurement-task request;
- stale pH/EC may be used for historical analysis only when labeled stale and must not
  support action wording;
- conflicting pH/EC or observation evidence creates `conflict` and asks for a new
  measurement/check rather than resolving silently.

Future sensor data may add other freshness windows only through later specs.

## Missing And Stale Data Behavior

Advisor behavior must choose the lowest-risk useful output:

| Condition | Required Behavior |
|---|---|
| Missing pH or EC needed for analysis | `clarify` or measurement-task request; no physical-action recommendation. |
| Stale pH/EC for analysis | Explain stale context, ask for new measurement, allow cautious non-action observation only. |
| Fresh pH/EC but no supporting observation/photo where needed | Ask for the missing evidence or provide bounded uncertainty. |
| Conflicting evidence | Mark `conflict`, cite refs, ask for re-check/follow-up. |
| Unauthorized Plant/evidence | Deny or omit through context builder; do not mention hidden records. |
| Archived Plant in normal operation | Do not produce normal operational advice; allow authorized history analysis only if routed as such. |
| Provider/model failure | Return structured observation and safe next action; no fake advisor output. |

Measurement/check task requests may be proposed as `task_request` or clarification
handoffs. Actual task creation and follow-up outcome semantics are owned by FT-013.

## Hydroponics Advisor Output Contract

Minimum advisor output after harness validation:

```yaml
advisor_output_id: string
agent_id: hydroponics_advisor
farm_id: string
plant_id: string
runtime_decision: speak | clarify | escalate
claim_type: hypothesis | recommendation | clarification | safety_block | task_request
trust_status_refs: []
freshness_summary:
  ph: fresh | stale | missing | conflict | unknown | not_applicable
  ec: fresh | stale | missing | conflict | unknown | not_applicable
physical_action_implied: boolean
safety_gate_required: boolean
safety_gate_status: not_required | required | blocked | pending_approval | cleared_for_approval
consumable_output: string
source_refs: []
evidence_refs: []
trace_ref: string
redaction_status: redacted | no_sensitive_fields
```

Rules:

- `silent` is trace/eval-only. It creates no `advisor_output`, MessageEnvelope, Bus
  event, or UI Feed projection.
- `cleared_for_approval` is a Safety Gate handoff state, not human approval and not an
  `action_task` unlock.
- ordinary advice is concise and scoped to the current Plant;
- output must distinguish observation, hypothesis, recommendation, clarification, and
  safety route;
- recommendations implying physical action set `physical_action_implied=true` and
  `safety_gate_required=true`;
- before Safety Gate clearance and authorized approval, user-visible wording must not
  imply immediate physical action;
- Consultant context may receive advisory/read output but cannot create domain
  task/recommendation/action records by default;
- raw provider output is not displayed or published until adapted through FT-009.

## Safety Gate Routing Boundary

FT-011 detects and routes action-implying wording. It does not own final Safety Gate
decision internals.

Physical-action wording includes at least pH/EC change, solution change, nutrient
dosing, pump/light/dosing/watering/circulation change, pruning, transplanting, root
trimming, or other material Plant-system interventions.

Routing rules:

- action-implying advisor output is blocked from direct UI action wording and routed to
  Safety Gate with source/evidence refs;
- fresh data is required for the route but never sufficient to approve action;
- Safety Gate clearance is distinct from human approval;
- Companion governance DecisionRecord cannot substitute for Safety Gate approval;
- no `action_task` is created by FT-011 directly.

## First-Demo Visibility

First demo must show trust status and missing-data behavior clearly enough for the user
workflow:

- Plant card/history can show confirmed/probable/unknown/conflict labels or equivalent
  bounded UI projection from runtime state;
- missing/stale pH/EC produces a visible clarify or measurement prompt;
- a non-action cautious advisor message may be displayed when evidence is adequate for
  analysis but not for action;
- action-implying output appears only as Safety Gate route/block/pending path, not as
  immediate instruction.

Exact UI component layout belongs to task decomposition.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- compute/update trust-labeled Plant state proposals from validated evidence;
- start Plant State Agent run over authorized Plant context;
- start Hydroponics Advisor run over authorized Plant context;
- create clarification or measurement-task request handoff for missing/stale data;
- route action-implying advisor output to Safety Gate;
- read Plant state/advisor trace summaries for authorized diagnostics.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-011 can be considered implemented:

- agent hypotheses, AgentMemoryRecord, raw provider output, photo manifests, UI Feed,
  raw chat, and timeline replay cannot create confirmed Plant state;
- human/follow-up evidence is required for `confirmed_updated` and
  `confirmed_unchanged`;
- missing pH/EC creates explicit missing/unknown behavior and a clarify or measurement
  request, not unsafe recommendation;
- stale pH/EC can support historical/cautious analysis only when labeled stale and
  cannot support physical-action wording;
- conflicting evidence creates `conflict` with refs and asks for re-check/follow-up;
- Advisor output is ActorContext and PlantAccessGrant scoped;
- Consultant context cannot create domain task/recommendation/action records by
  default;
- physical-action wording routes to Safety Gate before user-visible action wording or
  action-task creation;
- governance DecisionRecord cannot substitute for Safety Gate approval;
- provider/model failure produces structured observation and no fake advisor success;
- first-demo UI/API flow exposes trust status and missing-data prompt enough to verify
  behavior.

## Open Questions

No blocker for `/prd-to-tasks FT-011`. Exact field names, nutrient/pH/EC display
thresholds, UI label wording, task endpoint names, and first-demo component layout can
be chosen during task decomposition as long as trust-status authority, missing/stale
data behavior, real-runtime failure handling, Safety Gate routing, and no-automated
actuation constraints hold.
