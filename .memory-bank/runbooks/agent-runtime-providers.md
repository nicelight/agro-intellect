---
description: Local configuration and credentialed smoke runbook for Agent Runtime provider profiles.
status: active
type: runbook
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/testing/agent-runtime.md
  - .memory-bank/contracts/companion-runtime.md
  - .memory-bank/testing/companion-governance.md
  - .memory-bank/contracts/evidence-redaction.md
---
# Agent Runtime Providers Runbook

## Purpose

Configure one explicit canonical-agent provider/model binding, optionally run
the deferred credentialed FT-007 adapter manual UAT, and collect safe evidence
without overclaiming its later competence-specific product flow. This UAT is
not a TASK-031/code-phase closure prerequisite.

## Manual-UAT preconditions

These preconditions apply only when the optional credentialed UAT is explicitly
invoked. Missing credentials, egress, model selection, or dependencies leave
that UAT deferred; they do not fail TASK-031/code-phase closure.

- Local Foundation bootstrap and PostgreSQL migration path are working.
- An active authorized Plant has at least one real completed check-in or manual
  pH/EC row.
- Runtime dependencies from `pyproject.toml` are installed.
- The chosen DeepSeek or Gemini credential is available in the current shell.
- No credential value is written to `.env.example`, committed files, command
  history examples, logs, timeline, screenshots, or task evidence.

## Production binding

Production supplies one strict non-secret JSON mapping plus explicit egress:

```text
AGENT_MODEL_BINDINGS_JSON={"<canonical-agent-id>":{"provider_profile":"deepseek|gemini|chatgpt_oauth","model_id":"<explicit-provider-model-id>"}}
AGENT_EXTERNAL_EGRESS_ENABLED=true
```

There is no default model id or fallback. Invalid JSON, an unknown roster id or
profile, a blank model id, a missing binding, or
`AGENT_EXTERNAL_EGRESS_ENABLED=false` must fail before provider I/O.

Credential sources:

- `deepseek`: `DEEPSEEK_API_KEY`.
- `gemini`: `GOOGLE_API_KEY`.
- `chatgpt_oauth`: a future project-approved deployment-supplied
  `ChatGptOAuthCredentialAdapter`/broker; FT-007 ships none.

Do not add `OPENAI_API_KEY` as an implicit replacement for
`chatgpt_oauth` and do not read ChatGPT/Codex CLI credential caches.

## Deferred optional/manual FT-007 contract smoke

The FT-007 smoke uses the production assembler/provider factory and the
isolated test-only `runtime_contract_smoke` definition/binding through the
explicit test seam. The definition is absent from production resolution. This
proves transport, typed egress, validation, and anti-fallback behavior, not a
detailed product competence or trigger. BHV-001 and the live-provider portion
of REQ-011 remain deferred/unverified until a later accepted run; deterministic
evidence must not claim them.

1. Set `AGENT_REAL_SMOKE_PROFILE=deepseek|gemini` and a nonblank
   `AGENT_REAL_SMOKE_MODEL_ID`.
2. Enable `AGENT_EXTERNAL_EGRESS_ENABLED=true` and `AGENT_REAL_SMOKE=1`.
3. Provide the matching credential without printing it.
4. Run:

   ```bash
   AGENT_REAL_SMOKE=1 .venv/bin/python -m pytest tests/backend/agent_runtime/test_real_model_smoke.py -m real_model -q
   ```

5. Accept exactly one of two audited results:
   `outcome_kind=envelope_ready`, `status=envelope_ready`, with a valid pending
   MessageEnvelope; or `outcome_kind=model_silent`, `status=silent`, with
   `final_decision=silent`, `no_material_output|insufficient_evidence`, and no
   MessageEnvelope.
6. Treat skip, xfail, missing provider call, injected fake executor, canned
   output, fallback, `context_denied`, `runtime_not_configured`,
   `provider_failed`, `output_invalid`, `publication_guard_denied`,
   `audit_failed`, or any unaudited/runtime-created failure silence as failure.
7. Record only profile/model ref, accepted outcome kind, pass/fail, safe
   run/event refs, and redacted error code.

## Deterministic and regression checks

```bash
.venv/bin/python -m pytest tests/backend/agent_runtime -m "not real_model" -q
.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_runtime -q
.venv/bin/python -m pytest tests -q
node scripts/mb-lint.mjs
git diff --check
```

## FT-009 product-agent smokes

FT-009 uses canonical production definitions rather than the isolated FT-007
transport definition. Configure `AGENT_MODEL_BINDINGS_JSON` with:

- `vision_observation`: `provider_profile=gemini` and an explicit
  image-capable model id;
- `plant_state`: an explicit `deepseek` or `gemini` model id.

Enable egress and supply only the matching credential. Then run:

```bash
AGENT_REAL_VISION_SMOKE=1 .venv/bin/python -m pytest tests/backend/vision_observation/test_real_vision_smoke.py -m real_model -q
AGENT_REAL_PLANT_STATE_SMOKE=1 .venv/bin/python -m pytest tests/backend/plant_state/test_real_plant_state_smoke.py -m real_model -q
```

The vision smoke must accept the committed fixture through production photo
intake and send the freshly verified bytes, not a URL/path/canned description.
Both smokes fail when explicitly requested but skipped, faked, unconfigured,
unaudited, blocked, provider-failed, `clarify`, or model-silent for the
committed fixtures. The vision fixture must return `runtime_decision=speak`
with one pending envelope and one matching state candidate.
Record only safe model/outcome/event refs; never record photo bytes, prompts,
raw responses, or credentials.

## FT-010 product-agent smoke

Configure the canonical `hydroponics_advisor` binding with one explicit
DeepSeek or Gemini model id, enable egress, and supply only the matching
credential. Seed the smoke Plant through production PostgreSQL paths with the
specified missing/stale pH/EC fixture and run:

```bash
AGENT_REAL_HYDROPONICS_SMOKE=1 .venv/bin/python -m pytest tests/backend/hydroponics_advisor/test_real_hydroponics_smoke.py -m real_model -q
```

The smoke must make exactly one real provider call and return audited
`envelope_ready` with the exact project-validated measurement set and pending
`task_request` MessageEnvelope. Recommendation, hypothesis, clarification,
silence, skip/xfail, fake executor, fallback, unconfigured/blocked/failed/
audit-failed result, or any direct task/Safety/Bus/UI/state effect fails the
fixture. Record only safe model/outcome/event refs and the expected project-
owned request phrase; never record prompts, raw responses, credentials, auth
state, or hidden reasoning.

## FT-011 Safety Gate product-agent smoke

Configure the canonical `safety_gate` binding with one explicit DeepSeek or
Gemini model id, enable egress, and supply only the matching credential. Seed a
validated pending MessageEnvelope containing one unambiguous manual
solution-related action and run:

```bash
AGENT_REAL_SAFETY_GATE_SMOKE=1 .venv/bin/python -m pytest tests/backend/safety_gate/test_real_safety_gate_smoke.py -m real_model -q
```

The smoke must make exactly one real provider call over the strict
`SafetyGateProviderRequestV1`, return the expected closed model candidate, and
persist the matching project-owned classification. It must not send
Farm/Plant/auth/evidence data to the provider or create approval, task, Bus,
Timeline, or action effects. Skip/xfail, fake executor, fallback,
unconfigured/provider-failed/output-invalid/guard-denied/persistence-failed
outcome, unexpected class/kind, or direct action effect fails the fixture.
Record only the safe model ref and classification record/result refs.

## FT-012 Task and Follow-Up product-agent smoke

Configure canonical `task_follow_up` and `safety_gate` bindings with explicit
DeepSeek or Gemini model ids, enable egress, and supply only the matching
credentials. Seed an authorized active Plant through production PostgreSQL
paths with the committed Task/Outcome/evidence fixture from the FT-012 testing
contract. Run:

```bash
AGENT_REAL_TASK_FOLLOW_UP_SMOKE=1 .venv/bin/python -m pytest tests/backend/task_follow_up/test_real_task_follow_up_smoke.py -m real_model -q
```

The smoke must make exactly one real `task_follow_up` provider call over
`TaskFollowUpProviderRequestV1`, return a strict non-silent
`check|measurement|follow_up` proposal, pass one real existing Safety
classifier call with the same task kind, and persist exactly one ordinary Task
through the production authority path. It must not send Farm/Plant/auth/UI/
Bus/Timeline replay data to the Task and Follow-Up provider and must create no
action Task, Approval decision, completion, Outcome, Plant-state mutation, or
device effect.

Skip/xfail, fake executor or classifier, canned output, fallback, model
silence, unconfigured/provider-failed/output-invalid/guard-denied/audit-failed
result, classification mismatch, or direct action effect fails an explicitly
requested smoke. Record only safe model, run/event, classification, and Task
refs; never record Task text, prompts, raw responses, credentials, auth state,
or hidden reasoning. Without this accepted smoke, do not claim FT-012's
product-agent portion of REQ-011.

## FT-013 Companion product-agent smoke

Configure both canonical production bindings in the same strict deployment
map: `companion` for the proposal and `safety_gate` for the mandatory project
classification. Each binding has one explicit DeepSeek or Gemini model id;
they may use the same profile or different profiles, but neither may fall back
to the other. For example, with non-secret placeholders:

```text
AGENT_MODEL_BINDINGS_JSON={"companion":{"provider_profile":"deepseek","model_id":"<companion-model-id>"},"safety_gate":{"provider_profile":"deepseek","model_id":"<safety-model-id>"}}
AGENT_EXTERNAL_EGRESS_ENABLED=true
AGENT_REAL_COMPANION_SMOKE=1
```

Provide `DEEPSEEK_API_KEY` and/or `GOOGLE_API_KEY` for every distinct selected
profile without printing them. Use the normal Foundation/PostgreSQL
`DATABASE_URL`, apply the current migration head, and seed one active Plant
authorized for the smoke actor with:

- two completed check-ins that prove selection by
  `(recorded_at DESC,check_in_id DESC)`;
- competing pH-only and EC-only manual rows plus an equal-`measured_at` tie
  that prove exactly one row is selected by
  `(measured_at DESC,measurement_id DESC)` and no synthetic pH/EC merge occurs.

This real smoke intentionally uses `new_issue` and therefore sends no issue
summary. The deterministic FT-013 outbound-spy suite separately proves that an
authorized `existing_issue` request sends exactly its persisted matching
`companion_issue.summary_text` and no field outside the registered Companion
request allowlist.

Then use the new-issue explicit-run request from the FT-013 testing contract.
Run:

```bash
AGENT_REAL_COMPANION_SMOKE=1 .venv/bin/python -m pytest tests/backend/companion_governance/test_real_companion_smoke.py -m real_model -q
```

The smoke must invoke the protected explicit-run command, make exactly one real
`companion` provider call over `CompanionProviderRequestV1`, make exactly one
real `safety_gate` provider call over `SafetyGateProviderRequestV1`, return the
committed strict non-silent proposal plus matching classification, and persist
exactly one classification and one current proposal plus its active
HumanAttentionNeeded projection. It must create no Safety decision,
DecisionRecord, ordinary Task, approval, action Task, Plant mutation, or device
effect.

Skip/xfail, fake executor or classifier, canned output, fallback, model
silence, either missing binding/credential/provider call,
unconfigured/provider-failed/output-invalid/guard-denied/audit-failed result,
blocked or mismatched classification, any implicit domain-event/task/feed/
startup trigger, or direct decision/effect fails an explicitly requested
smoke. Record only both safe model refs, run/event, issue/proposal/attention,
and classification refs; never record proposal text, prompts, raw responses,
credentials, auth state, or hidden reasoning. Without this accepted smoke, do
not claim FT-013's product-agent portion of REQ-011.

## Troubleshooting

- `AGENT_RUNTIME_NOT_CONFIGURED`: verify the exact profile/model pair, egress
  flag, declared dependency, matching credential, and OAuth adapter when
  applicable. Do not try another provider automatically.
- `AGENT_PROVIDER_FAILED`: retain only the safe code and redacted provider
  class; never copy response bodies or credentials into evidence.
- `AGENT_OUTPUT_INVALID`: inspect local schema/test diagnostics without
  persisting raw model content.
- `AGENT_AUDIT_FAILED`: fix the timeline append path; no MessageEnvelope
  handoff may be claimed.

Concrete downstream product-agent UAT is owned by the feature that adds its
detailed policy and trigger. That UAT must repeat the real-provider path before
its portion of REQ-011 is claimed complete.
