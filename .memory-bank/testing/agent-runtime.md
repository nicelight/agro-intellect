---
description: Verification contract for FT-007 agent runtime, MessageEnvelope, real-model anti-cheat, and archive-race behavior.
status: active
type: testing_spec
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/features/FT-007-agent-runtime-decisions-message-envelope.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/auth/session-storage.md
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Agent Runtime Verification

## Scope

Defines executable verification for the FT-007 project-owned runtime adapter,
runtime decisions, MessageEnvelope validation, canonical roster/bootstrap,
multi-provider production binding, sanitized audit, and post-invocation
archive/authorization guard.

## Out of scope

- Bus storage/context queries and UI Feed projection tests owned by FT-008.
- Vision input/trust promotion owned by FT-009.
- Advisor missing-data behavior owned by FT-010.
- Safety Gate model classification and routing through immutable
  `pending_human_approval` are owned by FT-011. FT-012 owns the human
  decision, tasks/outcomes, and `task_follow_up` competence verification.
- Frontend/PWA flows owned by FT-016.

## Unit matrix

| Area | Required assertions |
|---|---|
| Provider request | Exact closed `ProviderRequestV1`; ordered records/refs; no authorization, session, role/grant, provider selection, or arbitrary metadata. |
| Typed input | Exact record union and payloads; PostgreSQL sources; Plant/check-in/pH/EC order; pH+EC row dedup; canonical UUID/time/decimal values; maximum four records. |
| Observation bound | Lengths 1/2000 accepted; 2001 rejected before provider I/O; no truncation, chunking, or implicit summary. |
| Model/envelope | Exact decision/candidate matrix; unknown/malformed/type/normalization/length-invalid content rejected; representative Markdown/HTML/prompt-/instruction-/URL-looking strings accepted unchanged as opaque candidate data when schema-valid; silence has no envelope; non-silent envelope is pending and non-consumable; model supplies no safety authority. |
| Outcome/event | Every `AgentRuntimeOutcomeV1` and Timeline matrix row; exact nullability/ref/provider/audit states; no-event branches; no failure becomes silence. |
| Security/errors | Message scope and audit attribution expose only canonical safe fields; provider/parser failures expose stable codes without secrets or raw payloads. |
| Roster/batch | Exact roster/order/metadata, UUIDv5 namespace and names, one eight-item batch, and the 8-or-0 sink result matrix. |
| Provider profiles | Strict bindings, nonblank model ids, no caller override/default/fallback, approved egress, and safe model refs. |

## Integration matrix

| Flow | Required assertions |
|---|---|
| Production assembly | ActorContext plus `plant_id` loads real PostgreSQL rows; callers cannot inject records/refs; request order matches the canonical contract. A persisted oversized observation returns `context_denied/input_contract_violation` with no provider or audit call. |
| Post-model guard | Expired/revoked session, disabled Account/Membership, role/grant change, wrong Farm, revoked grant, or archived Plant returns exact `publication_guard_denied` semantics. Identity never enters provider input; Timeline attribution is exactly `account_id`, `membership_id`, and request-time `role_preset`. |
| Envelope/classifier boundary | FT-007 returns only immutable pending/non-consumable envelopes. Producer tests reject model safety fields and claim no Bus/UI/task effect; classifier/effect implementation remains FT-011/FT-008/FT-012 scope. |
| Opaque candidate handoff | Schema-valid markup-/prompt-looking text reaches the pending envelope unchanged but has no instruction, routing, publication, task, Safety, or action authority. Downstream literal UI rendering and typed Bus quotation remain FT-008/FT-016 tests. |
| Audit/storage | One sanitized event for each provider-I/O branch; append failure blocks handoff; no agent-run/provider-history table and no timeline-as-runtime read. |
| Plant compatibility | Bootstrap starts after the existing Plant/grant/audit commit, makes no provider call, and leaves `POST /api/plants` authorization, `201 PlantSummary`, no-store, and error behavior unchanged for every sink result. |
| Batch sink | One call with eight deterministic items; identical duplicate succeeds; conflict rejects; rejected/failed accepts zero; introductions are non-consumable and not MessageEnvelope. No FT-008 storage/projection is implemented or claimed. |
| Provider composition | DeepSeek/Gemini construct only the selected native adapter; no cross-provider fallback; unconfigured `chatgpt_oauth` fails before credential/network access and never reads Codex/browser credentials. |

## Deferred optional/manual real-model UAT

This credentialed smoke is retained for later manual UAT and is non-blocking
for TASK-031/code-phase closure. Its absence or lack of credentials/provider
egress is not a deterministic-suite failure. BHV-001 and the live-provider
portion of REQ-011 remain explicitly deferred/unverified until a later smoke
passes; deterministic introduction, constructor, binding, or anti-cheat
evidence cannot satisfy them.

When explicitly invoked, the smoke remains strict and must:

1. Use a production DeepSeek or Gemini `AgnoModelExecutor`; no injected test
   executor or cross-provider substitute is allowed.
2. Use the isolated test-only `runtime_contract_smoke` definition through the
   explicit test seam with production assembler/provider composition. It is
   absent from production definition resolution and proves transport only.
3. Resolve an authorized active Plant and assemble actual persisted Plant
   context through the production assembler.
4. Invoke the configured real `provider_profile:model_id` model.
5. Complete with exactly one accepted result: either
   `outcome_kind=envelope_ready`, `status=envelope_ready`, with a valid pending
   MessageEnvelope; or `outcome_kind=model_silent`, `status=silent`, with
   `final_decision=silent` and
   `reason_code=no_material_output|insufficient_evidence`. Both require the
   configured safe `model_ref` and successful sanitized audit.
6. Record the configured safe `provider_profile:model_id` and prove the test did not
   skip or xfail.
7. Keep credentials, raw provider response, prompt history, and hidden reasoning
   out of stdout, logs, timeline, protocol, and task evidence.

The smoke must fail, not skip or substitute a fake output, when explicit smoke
mode is requested but model configuration, provider dependency, credential, or
network access is unavailable.

`context_denied`, `runtime_not_configured`, `provider_failed`,
`output_invalid`, `publication_guard_denied`, `audit_failed`, an unaudited
result, or runtime-created failure silence never count as a successful smoke.

## Anti-cheat inspection

- Production modules import/construct only the real Agno executor.
- Test executors live only in tests or clearly test-only helpers and are
  injected explicitly.
- Missing configuration/provider errors have no hardcoded response, canned
  MessageEnvelope, heuristic answer, or automatic fake fallback.
- Missing/unavailable model bindings have no default provider/model or
  cross-provider retry.
- Production code never reads Codex or ChatGPT browser credential stores and
  never relabels API-key auth as `chatgpt_oauth`.
- Agno memory/session history, Team coordination, raw provider messages, and
  UI Feed are absent from model context and persistence.
- Candidate text is never parsed or promoted into system/developer/instruction
  channels by FT-007; syntax-looking content remains opaque data.

## Behavior traceability

- `FT-007-BHV-001`: deferred/unverified manual UAT. A later credentialed real
  provider transport must produce either an audited validated non-silent
  envelope or audited strict model-declared silence, without accepting failure
  silence or claiming downstream product-agent completion.
- `FT-007-BHV-002`: committed Plant -> exact post-commit roster introduction
  handoff without model I/O or agent-context visibility.
- `FT-007-BHV-003`: archive during invocation ->
  `publication_guard_denied`, null final decision, blocked audit only, and no
  replay after restore.

## Commands

- Focused deterministic suite:
  `.venv/bin/python -m pytest tests/backend/agent_runtime -m "not real_model" -q`
- Deferred optional/manual UAT after explicit `AGENT_REAL_SMOKE_PROFILE`/model
  id, egress opt-in, installed provider dependency, and matching credential are
  configured (not a TASK-031/code-phase closure command):
  `AGENT_REAL_SMOKE=1 .venv/bin/python -m pytest tests/backend/agent_runtime/test_real_model_smoke.py -m real_model -q`
- Related access/archive regression:
  `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_runtime -q`
- Full regression: `.venv/bin/python -m pytest tests -q`
- Memory Bank lint: `node scripts/mb-lint.mjs`
- Diff check: `git diff --check`

Concrete roster-member prompts, triggers, and product-flow real-model evidence
remain with the RTM-listed owning features. The live-provider portion of
REQ-011 is currently deferred/unverified. Before REQ-011 is claimed complete,
at least one such downstream flow must repeat the production provider path over
actual scoped Plant data; the FT-007 contract smoke alone is insufficient.

Provider setup, redaction-safe triage, and the explicit ChatGPT OAuth support
boundary are defined in
`.memory-bank/runbooks/agent-runtime-providers.md`.
