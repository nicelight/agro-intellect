---
description: Verification contract for FT-007 agent runtime, MessageEnvelope, real-model anti-cheat, and archive-race behavior.
status: active
type: testing_spec
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/features/FT-007-agent-runtime-decisions-message-envelope.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/plant-operations.md
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
- Safety Gate classification and approval owned by FT-011.
- Frontend/PWA flows owned by FT-016.

## Unit matrix

- Validate all four runtime decisions and the exact decision/claim/safety
  compatibility matrix.
- Validate the exact `plant`, `daily_checkin`, and `manual_measurement`
  `AgentInputRecordV1` union; reject unknown record/payload fields, mismatched
  ids, non-PostgreSQL source values, non-deterministic latest selection, and
  more than four records.
- Reject unknown fields, malformed UUIDs/timestamps, unsafe refs, out-of-range
  confidence, empty/oversized output, and forbidden content.
- Prove `silent` has no MessageEnvelope and requires a safe reason code.
- Prove message ids are generated only after validation/current permission and
  are never reused by blocked candidates.
- Prove authorization scope serialization excludes sessions, tokens, headers,
  cookies, credentials, raw ActorContext objects, and provider keys.
- Prove provider errors and parser failures expose stable safe codes only.
- Validate the exact eight-member roster, fixed order, unique ids, immutable
  competence/introduction metadata, and deterministic UUIDv5 introduction ids.
- Validate strict provider binding configuration, partial maps, nonblank
  deployment model ids, no caller override/default/fallback, and redacted safe
  model refs.

## Integration matrix

- Feed an authenticated ActorContext plus `plant_id` into the production
  assembler; prove it builds the existing `AuthorizedPlantContext` seam from
  actual persisted Plant data, callers cannot inject candidate mappings/refs,
  only canonical typed records reach the executor, and executor refs exactly
  equal the typed-record refs.
- Revalidate the original service-side session/account/membership/Plant/grant
  after model execution; prove that identity/provenance is sufficient for
  current authorization but never enters model input or timeline actor refs.
- Revoke access or archive the Plant while the executor is in flight; the fresh
  publication guard must return audit-only, no MessageEnvelope, no Bus/UI
  publication, and no replay after restore.
- Simulate archive/revoke after FT-007 returns `envelope_ready`; the FT-008
  publication contract must deny the handoff in the same transactional/locking
  boundary as its write. FT-007 must not claim this later window is atomic.
- Append one `agent_runtime_decided` event with the correct run/source identity,
  safe metadata, and no output text/provider payload/reasoning.
- Inject timeline append failure and prove no envelope handoff is returned.
- Prove FT-007 does not write PostgreSQL agent-run/provider-history tables and
  does not read timeline as runtime or context authority.
- Create a Plant through the production transaction seam and prove bootstrap
  starts only after commit, builds exactly eight idempotent introduction
  handoffs, and makes no provider call.
- Repeat/fail the post-commit handoff and prove duplicate keys/content remain
  deterministic, a committed Plant is not reported as rolled back, and tests
  do not claim visible chat publication without a downstream sink.
- Prove introductions have `visible_to_agents=false`,
  `consumable_by_agents=false`, are not MessageEnvelope, and never enter model
  input.
- Prove native DeepSeek and Gemini factories construct only the configured
  Agno adapter and a failure never selects the other provider/model.
- Prove `chatgpt_oauth` is recognized but fails before credential discovery or
  network I/O when no approved broker is injected; scan production code for
  Codex/browser credential-store reads.

## Real-model smoke

The credentialed smoke must:

1. Use a production DeepSeek or Gemini `AgnoModelExecutor`; no injected test
   executor or cross-provider substitute is allowed.
2. Use the isolated test-only `runtime_contract_smoke` definition through the
   explicit test seam with production assembler/provider composition. It is
   absent from production definition resolution and proves transport only.
3. Resolve an authorized active Plant and assemble actual persisted Plant
   context through the production assembler.
4. Invoke the configured real `provider_profile:model_id` model.
5. Produce either a valid MessageEnvelope or a truthful audited `silent`,
   `blocked`, or `failed` outcome.
6. Record the configured safe `provider_profile:model_id` and prove the test did not
   skip or xfail.
7. Keep credentials, raw provider response, prompt history, and hidden reasoning
   out of stdout, logs, timeline, protocol, and task evidence.

The smoke must fail, not skip or substitute a fake output, when explicit smoke
mode is requested but model configuration, provider dependency, credential, or
network access is unavailable.

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

## Behavior traceability

- `FT-007-BHV-001`: credentialed real provider transport -> validated speak
  envelope without claiming downstream product-agent completion.
- `FT-007-BHV-002`: committed Plant -> exact post-commit roster introduction
  handoff without model I/O or agent-context visibility.
- `FT-007-BHV-003`: archive during invocation -> blocked audit only and no
  replay after restore.

## Commands

- Focused deterministic suite:
  `.venv/bin/python -m pytest tests/backend/agent_runtime -m "not real_model" -q`
- Credentialed smoke after explicit `AGENT_REAL_SMOKE_PROFILE`/model id,
  egress opt-in, and matching credential are configured:
  `AGENT_REAL_SMOKE=1 .venv/bin/python -m pytest tests/backend/agent_runtime/test_real_model_smoke.py -m real_model -q`
- Related access/archive regression:
  `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_runtime -q`
- Full regression: `.venv/bin/python -m pytest tests -q`
- Memory Bank lint: `node scripts/mb-lint.mjs`
- Diff check: `git diff --check`

The real-model command is not considered passing if it reports only skipped or
xfailed tests.

Concrete roster-member prompts, triggers, and product-flow real-model evidence
remain with the RTM-listed owning features. Before REQ-011 is claimed complete,
at least one such downstream flow must repeat the production provider path over
actual scoped Plant data; the FT-007 contract smoke alone is insufficient.

Provider setup, redaction-safe triage, and the explicit ChatGPT OAuth support
boundary are defined in
`.memory-bank/runbooks/agent-runtime-providers.md`.
