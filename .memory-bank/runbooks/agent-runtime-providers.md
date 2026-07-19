---
description: Provider-neutral fail-closed operation and deferred OpenAI-compatible endpoint integration milestone.
status: active
type: runbook
last_updated: 2026-07-19
source_of_truth:
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/testing/agent-runtime.md
  - .memory-bank/contracts/evidence-redaction.md
---
# Agent Runtime Provider Runbook

## Purpose

Operate the current provider-neutral code phase truthfully and define one
future manual integration milestone after an OpenAI-compatible endpoint is
explicitly selected. No provider, model, base URL, credential, egress, or live
smoke is required for current code-phase closure.

## Current code phase

Current production composition is intentionally unbound and MUST return the
stable not-configured result before network I/O. Do not add placeholder
credentials, choose an endpoint implicitly, or treat installed SDKs as a
binding.

Current closure evidence is deterministic:

- strict competence request/result schemas and unknown-field rejection;
- actual PostgreSQL record selection and accepted-photo byte/hash integrity;
- explicit test-only fake/spy executor call snapshots;
- pre-I/O and post-I/O authorization plus write-boundary rechecks;
- timeout, transport failure, malformed output, audit failure, and redaction;
- no default, retry-to-another-endpoint, fake/canned production fallback, or
  failure-as-silence;
- no direct Plant-state, Safety, Task, DecisionRecord, publication, or
  actuation authority from model output.

Missing credentials, endpoint access, egress, network connectivity, or a
non-skipped live smoke is `not_applicable_for_current_code_phase`, not a
blocker. Agno 2.7.4 being installed in `.venv` is dependency availability only
and is not provider-integration evidence.

## Deterministic commands

Use the applicable feature commands from the registered testing specs. The
shared baseline is:

```bash
.venv/bin/python -m pytest tests/backend/agent_runtime -m "not real_model" -q
.venv/bin/python -m pytest tests -m "not real_model" -q
node scripts/mb-lint.mjs
git diff --check
```

Fake/spy executors must be injected explicitly by tests. Production code must
not import or select them.

## Future integration milestone

Status: `deferred/manual/not_applicable_for_current_code_phase`.

Trigger: the owner explicitly selects one OpenAI-compatible endpoint and
records provider, model, base URL, authentication mode, egress approval,
timeout policy, and cost budget. Until all are selected, do not invent config
names or attempt a provider call.

The milestone is one integrated manual campaign, not a current queue task. It
must cover all of the following:

1. Real text response: invoke one canonical text competence over authorized
   persisted Plant data and validate its strict result.
2. Real image: upload/accept an image through production photo intake, verify
   path containment, size and sha256, send the exact in-memory bytes, and
   validate the strict Vision result.
3. Errors: exercise safe authentication/configuration and provider/transport
   failures without fallback or raw payload leakage.
4. Timeouts: enforce the selected timeout and prove the stable provider-failed
   result with no downstream effect.
5. Redaction: inspect stdout/stderr, logs, Timeline, HTTP errors, and evidence
   for credentials, secret-bearing URLs, request/response bodies, media bytes,
   prompts, raw exceptions, and hidden reasoning.
6. Cost: record only safe usage/cost totals needed to compare with the approved
   budget; never record credentials or raw content.
7. Authority: repeat post-I/O authorization/archive races and prove model
   output still has no direct Safety, Task, governance, Plant-state,
   publication, or actuation authority.

## Milestone acceptance

The future milestone passes only when every selected real call is non-skipped,
uses the explicitly selected endpoint, and produces safe evidence for the
expected strict outcome. Fake/spy executors, canned output, fallback, missing
call, silent substitution, unconfigured/failed/invalid/unaudited results, or
direct downstream authority cannot satisfy it.

Provider request/response content is never durable evidence. Retain only the
selected safe endpoint/model identifier defined by the milestone, call count,
strict outcome kind, safe ids/refs, timeout/error code, redaction result, and
approved cost summary.

## Troubleshooting

- `*_NOT_CONFIGURED` in the current code phase is the expected fail-closed
  production result, not a reason to choose a provider ad hoc.
- `*_PROVIDER_FAILED` after future selection retains only the stable safe code;
  never copy provider bodies or credentials into evidence.
- `*_OUTPUT_INVALID` is investigated through local schema diagnostics without
  persisting raw model content.
- Audit failure blocks handoff; no result may be claimed from unaudited
  provider I/O.

No real integration is currently claimed.
