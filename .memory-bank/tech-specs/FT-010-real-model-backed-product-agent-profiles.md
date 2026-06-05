---
description: Feature-local SDD tech spec for FT-010 real model-backed product-agent profiles, provider adapters, runtime failure behavior, and first-demo evidence.
status: active
feature_id: FT-010
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-010-real-model-backed-product-agent-profiles.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
  - .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - agents-best-practices
---
# FT-010 Real Model-Backed Product Agent Profiles Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for real
runtime/demo product-agent profiles, provider/model adapter configuration, vision over
actual uploaded photos, test-only mock boundaries, provider failure behavior, and
first-demo evidence requirements.

This spec applies `agents-best-practices`: the harness owns model calls, tool/action
validation, permissions, observations, traces, evals, budgets, and false-success
prevention. A fake, mock, hardcoded, or stubbed product-agent output is not an MVP
runtime/demo success.

## Scope

In scope:

- real provider/model-backed runtime mode for MVP product-agent demo flows;
- provider-neutral text and vision model adapter requirements;
- runtime profile activation/config fields that refine FT-007 `AgentProfile`;
- minimal product-agent profile list and competence boundaries for first demo;
- allowed deterministic policy-backed profiles where the profile is honestly policy
  enforcement rather than a simulated model;
- missing provider/config and provider/model failure handling;
- test-only mock boundaries and anti-cheat launch gates.

Out of scope:

- canonical harness loop, tool registry, permission decisions, observations, traces,
  and budgets owned by FT-007;
- context builder and AgentMemoryRecord retrieval owned by FT-008;
- MessageEnvelope/Bus/UI Feed adaptation owned by FT-009;
- Plant State/advisor trust and missing-data behavior owned by FT-011;
- Safety Gate detailed physical-action taxonomy and approval unlock owned by FT-012
  and FT-013;
- real fine-tuning, hosted SaaS model gateway, broad connector marketplace, or sensor
  runtime dependency before later PRD/spec promotion.

## Runtime Mode Rules

Every active `AgentProfile` must declare one runtime mode:

```yaml
runtime_mode: model_backed | vision_model_backed | deterministic_policy
```

Rules:

- `model_backed` and `vision_model_backed` require real provider/model configuration in
  runtime/demo flows;
- `deterministic_policy` is allowed only for backend policy/gate/validation behavior
  that does not claim to be an LLM/vision agent result;
- automated tests may use mocks only through explicit test configuration and must mark
  traces/results as `test_mock`;
- runtime/demo configuration must reject `test_mock`, `fake`, `stub`, `hardcoded`, or
  missing provider modes as successful product-agent execution;
- provider/model memory is disabled or ignored for project authority; project memory is
  only FT-008 AgentMemoryRecord through the context builder.

## Provider Adapter Boundary

Model adapters are harness components, not model-visible tools and not domain
authority.

Minimum adapter semantics:

```yaml
adapter_id: string
adapter_kind: text_llm | vision_model | deterministic_policy
provider_name: string | null
model_name_or_ref: string | null
capabilities: [text, vision, structured_output, tool_calling]
config_ref: redacted string
status: configured | missing_config | disabled | provider_unavailable | failed
timeout_seconds: number
max_input_tokens: number
max_output_tokens: number
trace_policy: standard | privacy_sensitive | safety_sensitive
redaction_status: redacted | no_sensitive_fields
```

Rules:

- provider credentials and `.env` values stay outside model context, MessageEnvelope,
  Bus, UI Feed, logs, screenshots, exports, and agent-visible traces;
- adapter inputs are context-builder packages and authorized artifact refs, not broad
  filesystem/database access;
- adapter outputs remain raw provider output until parsed, validated, permissioned, and
  adapted through FT-007 and FT-009 contracts;
- provider errors, timeouts, rate limits, malformed outputs, and missing config return
  structured observations with safe next actions;
- no silent fallback to fake success is allowed.

## Profile Runtime Configuration

FT-010 refines FT-007 `AgentProfile` with runtime/demo activation fields:

```yaml
agent_id: string
profile_version: string
runtime_mode: model_backed | vision_model_backed | deterministic_policy
provider_adapter_ref: string
instruction_bundle_ref: string
output_schema_ref: string
required_context_sources: []
required_artifact_capabilities: []
real_runtime_required: boolean
test_mock_allowed: automated_tests_only
first_demo_required: boolean
failure_policy: fail_clear | clarify | escalate | silent_with_trace
launch_gate_refs: []
```

Activation rules:

- active runtime/demo profiles require valid adapter config, instruction bundle refs,
  output schema refs, eval suite refs, and trace policy;
- disabled or missing-config profiles cannot pretend to run;
- a profile may be registered but not first-demo-active if task decomposition defers it;
- competence boundary, allowed context, allowed tools, risk class, memory scope, and
  output contracts remain allowlists from FT-007.

## Initial Profile Activation Map

| AgentProfile | Runtime Mode | First-Demo Requirement |
|---|---|---|
| `vision_observation` | `vision_model_backed` | Must process an accepted photo ref backed by actual uploaded photo data. |
| `plant_state` | `model_backed` | Must analyze actual scoped Plant runtime state/evidence and produce trust-labeled output. |
| `hydroponics_advisor` | `model_backed` | Must use actual scoped pH/EC/observation evidence and ask/route safely when data is missing or stale. |
| `companion` | `model_backed` | May be active only through typed governance boundaries; raw chat/proposal content remains non-authority. |
| `task_follow_up` | `model_backed` or `deterministic_policy` | If deterministic, it only proposes/checks backend task policy and must not simulate an LLM result. |
| `safety_gate` | `deterministic_policy` or `model_backed` | Backend policy remains authority; model output can only assist classification and must fail closed. |
| `dataset_governance` | `deterministic_policy` or `model_backed` | Cannot grant trainability outside dataset rules; deterministic guardrails must be labeled honestly. |
| `training_data_curator` | `model_backed` or disabled | Usually deferred/silent in MVP; no trainability change without evidence/review rules. |

Task decomposition may activate the first-demo subset incrementally, but the demo cannot
claim coverage for a profile that is disabled, missing config, fake, or test-mocked.

## Vision Observation Requirements

Vision Observation Agent must:

- receive authorized accepted photo refs from FT-005, including catalog identity,
  `sha256`, photo type, captured/accepted metadata, and local file access through a
  backend-controlled adapter;
- process the actual uploaded photo binary or a real derivative produced from that
  photo, not a placeholder text description;
- output photo quality and visual observations only;
- avoid diagnosis, treatment, dosing, pH/EC changes, or other physical-action advice;
- return structured failures for missing file, unauthorized photo, unsupported format,
  model/provider failure, or unclear image;
- preserve source refs, trace refs, and redaction status.

Raw vision output is not Plant fact until adapted through the harness and owning state
rules.

## Runtime Failure Behavior

Required failure outcomes:

| Failure | Required Behavior |
|---|---|
| Missing provider/model config | Return `provider_unavailable`/`missing_config` structured observation and no fake success. |
| Provider timeout/rate limit | Return bounded error observation with retry/ask/try-later next action according to budget policy. |
| Malformed model output | Reject, ask model to repair when budget allows, downgrade to clarify/escalate, or fail with trace. |
| Vision file missing/unauthorized | Deny or error before provider call; do not leak file existence beyond ActorContext. |
| Model suggests forbidden action | Harness rejects/routes through permission and Safety Gate contracts. |
| Provider returns secret-like content | Redact/reject before observation, MessageEnvelope, Bus, UI Feed, trace, or context. |
| Budget exhausted | Stop with clear status and safe next action; no claimed success. |

`silent` may record a non-public trace, but it cannot hide missing config or provider
failure as a successful agent result.

## Test-Only Mock Boundary

Mocks are allowed only when:

- execution mode is an automated test/eval fixture;
- traces and assertions mark the dependency as `test_mock`;
- runtime/demo config rejects the same mock provider;
- tests include at least one anti-cheat path proving fake/mock/stub output cannot pass
  MVP runtime/demo acceptance.

Test fixtures may mock provider latency, failures, malformed outputs, and tool-call
syntax. They may not redefine product acceptance.

## First-Demo Evidence Requirements

First-demo evidence must include:

- one AgentHarnessRun trace for an authorized Plant scope using a real configured text
  model for Plant State or Hydroponics Advisor;
- one Vision Observation run over an accepted actual uploaded photo ref;
- trace fields for provider/model/settings, context package ref, tools visible,
  structured observations, runtime decision, MessageEnvelope/Bus/UI handling where
  applicable, token/cost/latency, and final status;
- redaction proof that provider credentials, `.env` values, tokens, and auth material
  are absent from traces/context/output;
- failure evidence showing missing provider config fails clearly rather than returning
  fake success.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- provider/model adapter configuration validation;
- profile activation/deactivation for runtime/demo;
- start a model-backed AgentHarnessRun for an authorized profile and Plant/photo scope;
- execute a real vision observation over an accepted photo ref;
- read redacted run/provider status summaries;
- run real-runtime smoke/eval gates and test-only mock fixtures.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-010 can be considered implemented:

- runtime/demo rejects fake, mock, hardcoded, stubbed, or missing-provider agent outputs
  as success;
- test-only mocks are accepted only in automated test configuration and are trace-labeled
  as mocks;
- missing provider/model config fails clearly with no fake fallback;
- provider timeout, malformed output, and rate-limit paths produce structured
  observations and safe next actions;
- Vision Observation processes an actual accepted uploaded photo ref through a real
  vision-capable model or real vision integration;
- Vision Observation cannot diagnose, recommend physical action, or mutate Plant state;
- Plant State and Hydroponics Advisor first-demo runs use actual scoped Plant data from
  the context builder;
- raw provider output cannot bypass harness validation, permission policy, runtime
  decision, MessageEnvelope, Bus, UI Feed, or Plant-state rules;
- provider/model memory cannot bypass FT-008 project-owned memory;
- traces/evals record provider/model, context, budgets, token/cost/latency, final
  status, and no hidden reasoning or secrets.

## Open Questions

No blocker for `/prd-to-tasks FT-010`. Exact provider names, environment variable names,
model IDs, numeric budgets, instruction bundle file layout, and first-demo active
subset can be chosen during task decomposition as long as real model-backed acceptance,
vision-over-actual-photo behavior, test-only mock isolation, clear provider failure,
redaction, and harness/publication boundaries hold.
