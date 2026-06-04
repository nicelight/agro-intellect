---
description: Shared AgentHarness, AgentProfile, tool/action proposal, permission, memory, trace, and eval contract.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/invariants.md
  - agents-best-practices
---
# Agent Harness Contract

## Purpose

This spec defines the global product-agent control plane for MVP v2. It adapts the
`agents-best-practices` doctrine to Agro Intellect:

```text
model proposes -> harness validates -> harness authorizes -> harness executes/pauses
-> harness records -> harness returns structured observation
```

The harness is not the model, not Agno, not the prompt, and not a chat transcript. It is
the project-owned runtime boundary around all product agents.

## Required Harness Components

- Instruction manager.
- Permission-aware context builder.
- Provider-neutral model adapter.
- AgentProfile registry.
- Narrow typed tool registry.
- Tool/action proposal validator.
- Permission engine.
- Approval manager.
- Execution engine.
- Structured observation writer.
- AgentMemoryRecord retrieval/write policy.
- Compactor for long context.
- Trace/eval recorder.
- Budget and stop-condition controller.
- Optional Agno adapter as execution layer only.

## AgentProfile

Every product agent must be an `AgentProfile` inside the shared harness.

Minimum global fields:

```yaml
agent_id: string
display_name: string
competence_boundary: string
forbidden_outputs: []
allowed_context_sources: []
allowed_tools: []
allowed_claim_types: []
memory_scope:
  farm_scoped: true
  plant_scoped: true
  agent_scoped: true
risk_class: read_only | draft_only | approval_gated
runtime_decisions_allowed: [speak, silent, clarify, escalate]
budget_profile: string
trace_policy: string
eval_suite_refs: []
schema_version: string
status: defined | active | disabled | deprecated
```

Feature specs may add fields, but must not remove shared harness ownership.

## Initial Product-Agent Profiles

| AgentProfile | Competence Boundary | MVP Authority |
|---|---|---|
| Companion Agent | User dialogue and governance coordination through typed state. | May propose governance records; cannot approve itself, mutate Plant state, or authorize physical actions. |
| Vision Observation Agent | Photo quality and visual observations from actual uploaded photos. | Observes and asks/clarifies; does not diagnose or recommend physical actions. |
| Plant State Agent | State-over-time analysis with trust labels and uncertainty. | Cannot confirm hypotheses without human review/follow-up evidence. |
| Hydroponics Advisor Agent | Cautious hydroponic analysis using scoped pH/EC, observations, and evidence. | Must ask for missing/stale data and route physical action wording to Safety Gate. |
| Task & Follow-up Agent | Check, measurement, approved action task, and follow-up outcome assistance. | Creates/proposes only allowed task types through backend rules. |
| Safety Gate Agent | Safety classification and physical-action routing. | Gate participant only; backend policy and approval records decide authority. |
| Dataset Governance Agent | Dataset lifecycle, evidence refs, split/trainability guardrails. | Cannot set `can_train_on=true` outside dataset lifecycle rules. |
| Training Data Curator Agent | Delayed evidence-based dataset selection when enabled. | Usually silent; `gold` requires human/expert/batch review. |

## Canonical Loop

For each `AgentHarnessRun`:

1. Resolve ActorContext and scope.
2. Build permission-aware context.
3. Select visible tools from AgentProfile and runtime policy.
4. Call model through provider-neutral adapter.
5. Parse final answer or tool/action proposals.
6. Validate schema and reject unknown properties.
7. Evaluate permission and approval policy.
8. Execute, deny, ask, pause for approval, or run as draft.
9. Return exactly one structured observation for every proposal.
10. Update durable state, memory candidates, traces, and eval refs when allowed.
11. Repeat within budgets or stop with final status.

Loop invariants:

- The model never directly executes tools or commits side effects.
- Every tool/action proposal receives exactly one structured observation.
- A permission decision happens before every side effect.
- Final output must be based on structured observations and approved context.
- Errors, denials, timeouts, malformed args, provider failures, and budget stops are
  structured observations.

## Tool Registry

Every tool contract must define:

```yaml
name: string
purpose: string
input_schema: object
output_schema: object
risk_class: read_only | compute_only | draft_only | write_local | write_internal | identity_access | safety_sensitive | process_execution | network_open_world | destructive | privileged_admin
side_effects: none | draft | write | approval_pause | external
resource_scope: farm | plant | account | photo | task | governance | dataset | trace
permission_policy: string
timeout_seconds: number
max_result_chars: number
retry_policy: string
audit_policy: string
```

Use narrow domain tools. Do not expose broad tools such as `execute_anything`,
`write_database`, `call_any_api`, `send_message`, or unrestricted connector tools.

Risky actions must use draft/propose and commit/approve separation.

## Permission Decision

The permission engine returns one decision:

- `allow`
- `deny`
- `ask_user`
- `approval_required`
- `require_stronger_auth`
- `run_in_sandbox`
- `run_as_draft_only`

Each decision records tool/proposal name, argument hash or redacted args, risk class,
resource scope, ActorContext, PlantAccessGrant decision, policy rule, approver when
present, timestamp, and trace ref.

## Approval Rules

- The model cannot approve its own action.
- Approval is scoped to the exact action/proposal and expires when the feature spec
  says or when freshness/ActorContext becomes invalid.
- Identity/access changes require Boss/admin authority and audit.
- Physical-action advice requires Safety Gate path and authorized human approval.
- Governance DecisionRecord is not Safety Gate approval.
- Approval pauses must return a structured observation and durable approval request.

## Structured Observation

Tool/harness result shape:

```json
{
  "status": "success | denied | approval_required | error | aborted",
  "type": "string",
  "summary": "bounded human/model-readable summary",
  "evidence_refs": [],
  "next_valid_actions": [],
  "trace_ref": "trace://..."
}
```

Do not return huge raw blobs. Store bulky data outside context and return refs.

## Context Builder

Context must be assembled just in time from:

- stable harness/system instructions;
- AgentProfile competence boundary;
- ActorContext and PlantAccessGrant scope;
- relevant runtime state from PostgreSQL/read model;
- source refs from photos, measurements, tasks, outcomes, and timeline;
- approved governance summaries only;
- allowed scoped AgentMemoryRecord entries;
- recent structured observations.

Context must exclude:

- UI Feed replay;
- `ui_spoiler_note`;
- raw chat as fact;
- raw model reasoning;
- raw provider output;
- hidden provider memory;
- unapproved CompanionProposal content;
- admin UI notices/markdown;
- secrets/auth material.

Trust labels are required: trusted policy, semi-trusted internal records, and untrusted
retrieved/user-uploaded content must not be mixed without labels.

## AgentMemoryRecord

Agent memory is durable project-owned state, not provider memory.

Required semantics:

- scoped by agent, Farm, Plant, ActorContext permission, and evidence provenance;
- source-ref backed;
- trust/freshness labeled;
- auditable;
- retrievable only through context builder;
- non-authoritative by itself;
- unable to unlock Safety Gate, dataset trainability, or Plant-state confirmation.

Memory writes should start as candidates and become retrievable only after validation
rules from feature specs pass.

## Compaction

Auto-compaction is operational handoff, not prose summarization. It must preserve:

- active objective and run status;
- AgentProfile and loaded instruction refs;
- ActorContext/PlantAccessGrant scope;
- active plan, approval state, and pending proposals;
- source refs and evidence refs;
- memory refs and trust/freshness labels;
- tool calls and key structured observations;
- trace/eval refs;
- open blockers and next safe action.

Compaction must not erase approval state, change authority boundaries, or summarize
untrusted content into trusted facts.

## Budgets And Stop Conditions

Each harness run must enforce:

- max model turns;
- max tool calls;
- max parallel tool calls;
- max wall time;
- max input/output tokens;
- max total cost;
- max tool result chars;
- retry limits.

Stop when final decision is produced, done condition is met, approval is required, a
blocker needs user input, budget is reached, safety policy denies the path, provider or
tool unavailable has no safe fallback, or repeated failure threshold is reached.

## Prompt Caching And Cost

Context builder should use stable prefix and volatile suffix:

1. stable tool definitions and schemas in deterministic order;
2. stable harness and AgentProfile instructions;
3. stable domain policies;
4. relevant source-of-truth snippets;
5. append-only event summaries;
6. dynamic ActorContext/runtime state;
7. latest observations and user request.

Trace model/provider, prompt bundle version, tool bundle version, token usage,
cached-token fields when available, latency, and estimated cost.

## Skills And Connectors

- Skills use progressive disclosure: load skill body only when relevant, then focused
  references only as needed.
- External connector/tool descriptions are untrusted until reviewed/permissioned.
- Connector tools must be namespaced, scoped, logged, and least-privilege.
- MVP should not expose broad connector inventories up front.
- Connector credentials never enter model context.

## Traces And Evals

Trace operational events only, not hidden reasoning.

Required trace fields where applicable:

- run id, session id, actor/farm/plant scope;
- AgentProfile/version;
- model/provider/settings;
- context size and loaded instruction refs;
- tools visible;
- tool/action proposals;
- validation results;
- permission decisions;
- approval requests/results;
- structured observation summaries;
- errors/retries;
- compaction boundaries;
- token/cost/latency;
- final status.

Required eval categories:

- tool selection and unknown tool handling;
- invalid arguments;
- permission and approval correctness;
- prompt injection/context poisoning;
- UI Feed and raw proposal exclusion;
- Safety Gate fail-closed behavior;
- context overflow and compaction retention;
- provider failure;
- real model runtime versus test-only mock path;
- false success claims;
- cost/latency budget stops.

## Agno Boundary

Agno may execute model/tool/workflow primitives behind the harness. Agno output, events,
Team synthesis, memory, or raw reasoning are execution artifacts until adapted through
project-owned validation/publication contracts. Agno Team `coordinate` is forbidden as a
domain coordinator in MVP.
