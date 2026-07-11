---
description: Local configuration and credentialed smoke runbook for Agent Runtime provider profiles.
status: active
type: runbook
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/testing/agent-runtime.md
  - .memory-bank/contracts/evidence-redaction.md
---
# Agent Runtime Providers Runbook

## Purpose

Configure one explicit canonical-agent provider/model binding, run the
credentialed FT-007 adapter smoke, and collect safe evidence without
overclaiming its later competence-specific product flow.

## Preconditions

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

## FT-007 contract smoke

The FT-007 smoke uses the production assembler/provider factory and the
isolated test-only `runtime_contract_smoke` definition/binding through the
explicit test seam. The definition is absent from production resolution. This
proves transport, typed egress, validation, and anti-fallback behavior, not a
detailed product competence or trigger.

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
