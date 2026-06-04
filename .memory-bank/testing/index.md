---
description: Testing and verification router for MVP v2 requirements, epics, and features.
status: active
owner: quality
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/spec-index.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-harness.md
---
# Testing Index

## Current State

The active MVP v2 PRD has been decomposed into requirements, epics, and features.
Global `/spec-design` now defines backbone test categories and verifiable contract
boundaries. Feature-level `/spec-improve FT-<NNN>` must turn these categories into exact
test cases, fixtures, API schemas, eval prompts, and launch gates before task
decomposition.

MVP v1 testing docs are archived under
[.memory-bank/archive/mvp-v1/testing/](../archive/mvp-v1/testing/).

## Migration Gates

After Memory Bank routing or spec-layer changes, run:

```bash
node scripts/mb-lint.mjs
node scripts/mb-doctor.mjs
git diff --check
```

After `/prd` and `/spec-design`, run fresh-context Memory Bank review before task
decomposition.

## Quality Gates

- Requirements traceability: each T1/T2/T3 task must link concrete `REQ-*` and `FT-*`
  IDs once tasks exist.
- Spec gate: global `/spec-design` must be `complete` or valid `minimal` before
  `/prd-to-tasks`.
- Feature gate: each feature needs `/spec-improve FT-<NNN>` or explicit `not_required`
  rationale before task decomposition.
- Unit tests: deterministic domain rules, schema validation, permission policy,
  state transitions, redaction helpers, and trainability rules.
- Integration tests: API/service boundaries for ActorContext, PlantAccessGrant,
  photo intake, runtime/timeline separation, harness tool/action proposals,
  MessageEnvelope/Bus/UI Feed, Safety Gate, Companion governance, and dataset refs.
- E2E/UI smoke: Boss setup, Engineer authorized Plant workflow, Plant selector,
  daily check-in, photo upload, pH/EC, agent output display, Safety Gate prompt,
  task/follow-up, Companion proposal/decision, storage prompt.
- Harness evals: prompt injection, tool misuse, approval bypass, model/provider
  failure, unknown tool, invalid args, context overflow/compaction, cost/latency
  budget, false success claim, real-vs-test-mock runtime distinction.

## Global Test Contract Map

| Area | Required Verification |
|---|---|
| Access and ActorContext | Unit tests for role/preset policy; integration tests proving backend rejects missing session, disabled membership, missing/revoked PlantAccessGrant, non-Boss admin mutation, and unauthorized context-builder retrieval. |
| Plant lifecycle and runtime authority | Integration tests proving archive removes normal operations but retains authorized history; timeline/photo/manifests cannot overwrite runtime state. |
| Photo intake | File/catalog/sha256/manifest/timeline tests, invalid upload rejection, failure ordering, unauthorized photo access denial, and manifest redaction. |
| API boundary | Generated OpenAPI validation once backend exists; error envelope tests; CORS/LAN fail-closed tests if LAN mode exists. |
| AgentHarness | Unit/contract tests for unknown tool, invalid args, permission decision, approval pause, structured observation, budgets, provider failure, trace recording, and no fake runtime/demo fallback. |
| Context and memory | Tests for ActorContext/PlantAccessGrant filtering, UI Feed exclusion, unapproved proposal exclusion, stale memory non-authority, compaction preservation, and prompt-injection labeling. |
| Event/message boundaries | Contract tests for MessageEnvelope validation, BusEventEnvelope filtering, `silent` trace/no Bus behavior, UI Feed projection isolation, and malformed output rejection. |
| Safety Gate | Fail-closed tests for stale/missing evidence, fresh-data-not-sufficient, Boss/Engineer/Consultant approval differences, governance-vs-safety separation, stale approval replay, and no automated actuation. |
| Tasks/follow-up | Tests for check/measurement/action_task separation, rejected approval no action_task, follow-up outcome evidence, and no-data outcome semantics. |
| Companion governance | Tests for typed Plant-scoped IssueStack/proposal/decision state, supersede behavior, superseded proposal non-approval, DecisionRecord authority limits, and approved summary filtering. |
| Dataset/privacy/deployment | Tests for non-trainable default, `can_train_on` guardrails, 200 MB prompt no upload implication, `local_only` sync, LAN controls, and secret redaction across forbidden surfaces. |

## MVP v2 Risk Surfaces

- local account/session/authentication behavior;
- Farm/Plant authorization and per-Plant access;
- Boss Admin Surface and durable admin audit;
- ActorContext propagation through APIs, workflows, context builders, tasks, approvals, and audit;
- Plant archive/restore retention and normal-flow filtering;
- photo file/catalog/manifest/timeline refs and local artifact integrity;
- PostgreSQL/read-model runtime authority versus timeline/photo/export artifacts;
- shared AgentHarness loop, AgentProfile definitions, tool/action validation,
  permission decisions, approval pauses, structured observations, traces, evals, and budgets;
- AgentMemoryRecord lifecycle, scoping, retrieval, freshness/trust semantics, and non-authority;
- Agent Chat Bus, MessageEnvelope, and UI Feed permission/context hygiene;
- real model-backed runtime/demo agents and real vision processing over actual uploaded photos;
- Plant State trust statuses and Hydroponics Advisor missing-data behavior;
- Safety Gate approval roles, physical-action fail-closed behavior, and no automated actuation;
- task/approval/action/follow-up evidence and audit refs;
- Companion governance state, proposal supersede behavior, `DecisionRecord` semantics, and approved governance summaries;
- dataset/export isolation by Farm/Plant context and trainability guardrails;
- local privacy, loopback/LAN controls, `local_only` sync, 200 MB storage prompt, and secret redaction.

## Anti-Cheat Rules

- Do not satisfy MVP runtime/demo agent acceptance with fake, mock, hardcoded, or
  stubbed product-agent outputs. Test-only mocks are allowed only in automated tests.
- Do not treat UI Feed, spoiler notes, admin UI text, raw chat, raw model reasoning,
  unapproved proposals, or provider memory as agent working context or source of truth.
- Do not let `timeline.jsonl`, photo manifests, export snapshots, or dataset files
  replace PostgreSQL/read-model runtime authority.
- Do not promote agent hypotheses or AgentMemoryRecord content to confirmed Plant state
  without owning runtime/state rules, evidence, and required human review/follow-up.
- Do not display or imply immediate physical-action instructions without Safety Gate
  clearance and authorized human approval.
- Do not let governance DecisionRecord substitute for Safety Gate approval.
- Do not imply upload/server availability from local storage or sync UI.
- Do not allow secrets/auth material into logs, timeline, manifests, Bus, UI Feed,
  screenshots, exports, or agent context.

## Harness Eval Requirements

Agent harness evals must evaluate the harness, not only model answer quality.

Required eval families:

- happy path over actual scoped Plant data;
- real vision processing over an uploaded photo;
- missing/stale pH/EC behavior;
- unknown tool and invalid argument recovery;
- approval bypass attempts;
- prompt injection in user/uploaded/retrieved content;
- raw UI Feed or unapproved proposal leakage attempts;
- context overflow and compaction retention;
- provider/model failure and missing configuration;
- budget stop and false success claim;
- safety-sensitive wording before and after Safety Gate route.

Test-only mocks may be used in automated tests, but runtime/demo acceptance must prove
real model-backed behavior where PRD acceptance requires it.
