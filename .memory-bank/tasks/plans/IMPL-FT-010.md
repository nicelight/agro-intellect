---
description: Implementation plan for FT-010 Real Model-Backed Product Agent Profiles.
status: active
---
# IMPL-FT-010 Real Model-Backed Product Agent Profiles

## Goals

- Activate MVP runtime/demo product-agent profiles through real configured model
  providers or honestly labeled deterministic policy profiles.
- Ensure fake, mock, hardcoded, stubbed, and missing-provider paths cannot satisfy
  runtime/demo acceptance.
- Prove first-demo behavior over actual scoped Plant data and actual accepted uploaded
  photo refs with redacted traces and provider-failure evidence.

## Constitution Check

- Aligns with Spec Before Code, no speculation, bounded agent autonomy, local privacy,
  secret redaction, and risk-based Definition of Done.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because provider configuration, credential redaction,
  runtime acceptance, false-success prevention, and model-backed safety boundaries are
  critical runtime/security concerns.
- KISS boundary: one provider-neutral adapter interface and first-demo active subset;
  no hosted SaaS model gateway, broad connector marketplace, real fine-tuning, or
  provider memory authority.

## Source Artifacts

- .memory-bank/features/FT-010-real-model-backed-product-agent-profiles.md
- .memory-bank/tech-specs/FT-010-real-model-backed-product-agent-profiles.md
- .memory-bank/epics/EP-003-shared-agent-harness-and-context-boundaries.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

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
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- agents-best-practices: provider adapters normalize model calls while the harness owns
  tools, permissions, traces, budgets, structured observations, provider failure,
  prompt-cache/cost telemetry, and no fake runtime success.

## Constraints

- Runtime/demo `model_backed` and `vision_model_backed` profiles require real provider
  and model configuration.
- Test-only mocks are allowed only in automated tests and must be trace-labeled
  `test_mock`.
- Provider credentials and `.env` values stay outside model context, MessageEnvelope,
  Bus, UI Feed, logs, screenshots, exports, and agent-visible traces.
- Adapter outputs remain raw provider output until parsed, validated, permissioned, and
  adapted through harness and publication contracts.
- Provider/model memory is disabled or ignored for project authority.

## Invariants

- Fake, mock, hardcoded, stubbed, or missing-provider product-agent output cannot pass
  MVP runtime/demo acceptance.
- Vision Observation processes actual accepted uploaded photo binary or a real
  derivative from that photo, not a placeholder text description.
- Vision Observation cannot diagnose, recommend physical action, or mutate Plant state.
- Provider failures produce structured observations and safe next actions, not silent
  success.

## Steps

1. Implement provider adapter configuration validation and secret-safe runtime status
   summaries.
2. Add AgentProfile runtime activation fields and anti-fake/mock/stub success gates.
3. Implement real text model-backed Plant State and Hydroponics Advisor run entrypoint
   over authorized FT-008 context packages.
4. Implement real Vision Observation over accepted FT-005 photo refs and actual local
   photo data.
5. Add real-runtime smoke/evals, provider failure fixtures, missing-config proof, and
   first-demo launch gates.

## Expected Touched Files

- backend/app/agent_harness/*
- backend/app/model_adapters/*
- backend/app/context/*
- backend/app/photo_artifacts/*
- backend/app/runtime_state/*
- backend/app/publication/*
- backend/app/privacy/*
- backend/app/config/*
- backend/app/api/*
- backend/tests/agent_harness/*
- backend/tests/model_adapters/*
- backend/tests/photo_artifacts/*
- backend/tests/integration/*
- backend/tests/security/*
- .memory-bank/changelog.md

## Tests

- Unit: provider adapter config status, runtime mode validation, test-mock mode guards,
  malformed provider output repair/downgrade, timeout/rate-limit status, and budget
  stops.
- Integration: missing provider config fails clearly; real text-model run consumes
  scoped context package; real vision run consumes accepted photo binary; raw provider
  output cannot bypass validation/publication.
- Harness evals: provider unavailable, malformed output, fake/mock/stub acceptance
  attempt, model suggests forbidden action, provider memory bypass attempt, budget
  exhaustion, and first-demo trace completeness.
- Security: credentials and secret-like provider content are redacted/rejected before
  traces/context/output/publication.

## Quality Gates

- pytest backend/tests/model_adapters backend/tests/agent_harness backend/tests/photo_artifacts backend/tests/integration backend/tests/security
- Real-runtime smoke/eval evidence through the task-specific pytest/eval suite and /red-verify semantic-pass
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Missing provider config returns a clear provider-unavailable status with no fake
  agent success.
- Plant State or Hydroponics Advisor run uses actual scoped Plant context through a
  real configured text model.
- Vision Observation run processes an accepted uploaded photo ref through a real
  vision-capable model or real vision integration.
- First-demo trace shows provider/model/settings, context ref, tool visibility,
  token/cost/latency, final status, redaction proof, and no hidden reasoning.

## Task Slice

- TASK-059: Provider adapter configuration validation and secret-safe runtime status.
- TASK-060: Runtime profile activation fields and anti-fake/mock/stub success gates.
- TASK-061: Real text model-backed Plant State and Hydroponics Advisor run entrypoint.
- TASK-062: Real Vision Observation over accepted uploaded photo refs.
- TASK-063: Real-runtime smoke/evals, provider failure, and launch-gate coverage.
