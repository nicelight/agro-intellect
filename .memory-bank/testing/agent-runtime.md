---
description: Verification contract for provider-neutral Agent Runtime, MessageEnvelope, executor anti-cheat, and archive-race behavior.
status: active
type: testing_spec
last_updated: 2026-07-29
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
runtime decisions, MessageEnvelope validation, canonical roster metadata,
provider-neutral fail-closed production binding, sanitized audit, and
post-invocation archive/authorization guard.

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
| Provider request | Exact closed `ProviderRequestV1`; ordered records with read-only refs derived from them and no independent refs constructor input; no authorization, session, role/grant, provider selection, or arbitrary metadata. |
| Typed input | Exact record union and payloads; PostgreSQL sources; Plant/check-in/pH/EC order; pH+EC row dedup; canonical UUID/time/decimal values; maximum four records. |
| Observation bound | Lengths 1/2000 accepted; 2001 rejected before provider I/O; no truncation, chunking, or implicit summary. |
| Model/envelope | Exact decision/candidate matrix; unknown/malformed/type/normalization/length-invalid content rejected; representative Markdown/HTML/prompt-/instruction-/URL-looking strings accepted unchanged as opaque candidate data when schema-valid; silence has no envelope; non-silent envelope is pending and non-consumable; model supplies no safety authority. |
| Outcome/event | Every `AgentRuntimeOutcomeV1` and Timeline matrix row; exact nullability/ref/provider/audit states; no-event branches; no failure becomes silence. |
| Security/errors | Message scope and audit attribution expose only canonical safe fields; provider/parser failures expose stable codes without secrets or raw payloads. |
| Roster metadata | Exact roster/order/competence/introduction metadata and deterministic per-introduction UUIDv5 namespace/name; no batch, sink, pending state, or persistence behavior in Agent Runtime. |
| Provider boundary | Unbound production fails before I/O; explicit test-only fake/spy injection; no caller override/default/fallback; safe synthetic refs and no real-integration claim. |

## Integration matrix

| Flow | Required assertions |
|---|---|
| Production assembly | ActorContext plus `plant_id` loads real PostgreSQL rows; callers cannot inject records/refs; request order matches the canonical contract. A persisted oversized observation returns `context_denied/input_contract_violation` with no provider or audit call. |
| Post-model guard | Expired/revoked session, disabled Account/Membership, role/grant change, wrong Farm, revoked grant, or archived Plant returns exact `publication_guard_denied` semantics. Identity never enters provider input; Timeline attribution is exactly `account_id`, `membership_id`, and request-time `role_preset`. |
| Envelope/classifier boundary | FT-007 returns only immutable pending/non-consumable envelopes. Producer tests reject model safety fields and claim no Bus/UI/task effect; classifier/effect implementation remains FT-011/FT-008/FT-012 scope. |
| Opaque candidate handoff | Schema-valid markup-/prompt-looking text reaches the pending envelope unchanged but has no instruction, routing, publication, task, Safety, or action authority. Downstream literal UI rendering and typed Bus quotation remain FT-008/FT-016 tests. |
| Audit/storage | One sanitized event for each provider-I/O branch; append failure blocks handoff; no agent-run/provider-history table and no timeline-as-runtime read. |
| Plant compatibility | `POST /api/plants` leaves the Plant/grant/audit transaction, authorization, `201 PlantSummary`, no-store, and error behavior unchanged and performs no introduction persistence, sink, provider, Bus, or Feed work. |
| Introduction ownership | Agent Runtime exposes static roster metadata only. FT-008 owns any missing-row materialization inside an authorized active-Plant Feed request; introductions remain non-consumable and are not MessageEnvelope. |
| Provider composition | No current endpoint is selected; production fails before network I/O, test fake/spy executors are explicit, and code never reads browser/Codex credential stores or retries a fallback. |

## Deferred future selected-endpoint milestone

The single manual integration campaign in
`.memory-bank/runbooks/agent-runtime-providers.md` is
`deferred/manual/not_applicable_for_current_code_phase`. Credentials, egress,
network access, endpoint selection, and a non-skipped live smoke are not
current closure gates. Deterministic evidence MUST NOT claim a real image,
response, provider, model, or network call.

After an OpenAI-compatible endpoint is explicitly selected, that milestone
must cover real text response, real image, provider errors, enforced timeouts,
redaction, cost, and unchanged no-fallback/no-direct-authority behavior.

## Anti-cheat inspection

- Production modules cannot select a fake/spy executor and fail closed while
  no endpoint is selected.
- Test executors live only in tests or clearly test-only helpers and are
  injected explicitly.
- Missing configuration/provider errors have no hardcoded response, canned
  MessageEnvelope, heuristic answer, or automatic fake fallback.
- Missing/unavailable model bindings have no default endpoint/model or retry.
- Production code never reads Codex, ChatGPT, browser, CLI, or IDE credential
  stores.
- Agno memory/session history, Team coordination, raw provider messages, and
  UI Feed are absent from model context and persistence.
- Candidate text is never parsed or promoted into system/developer/instruction
  channels by FT-007; syntax-looking content remains opaque data.

## Behavior traceability

- `FT-007-BHV-001`: historical real-provider behavior is superseded for current
  closure by the provider-neutral deterministic contract. Any future real
  transport claim belongs only to the selected-endpoint milestone.
- `FT-007-BHV-002`: static canonical roster metadata remains deterministic
  while Plant create/startup perform no introduction work; any missing
  presentation rows belong only to a later authorized active-Plant Feed open.
- `FT-007-BHV-003`: archive during invocation ->
  `publication_guard_denied`, null final decision, blocked audit only, and no
  replay after restore.

## Commands

- Focused deterministic suite:
  `.venv/bin/python -m pytest tests/backend/agent_runtime -m "not real_model" -q`
- Future live integration command: intentionally undefined until provider,
  model, base URL, authentication, egress, timeout, and cost decisions exist.
- Related access/archive regression:
  `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_runtime -q`
- Full regression: `.venv/bin/python -m pytest tests -q`
- Memory Bank lint: `node scripts/mb-lint.mjs`
- Diff check: `git diff --check`

Concrete roster-member prompts and triggers remain with the RTM-listed owning
features. Their current code-phase evidence is deterministic and provider-
neutral. The future real-integration claim is centralized in the provider
runbook milestone.

Provider-neutral operation, redaction-safe triage, and the future selected-
endpoint milestone are defined in
`.memory-bank/runbooks/agent-runtime-providers.md`.
