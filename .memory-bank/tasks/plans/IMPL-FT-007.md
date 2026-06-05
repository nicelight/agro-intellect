---
description: Implementation plan for FT-007 Shared AgentHarness And AgentProfile Runtime.
status: active
---
# IMPL-FT-007 Shared AgentHarness And AgentProfile Runtime

## Goals

- Implement one project-owned provider-neutral AgentHarness/control plane for product
  agents.
- Define AgentProfile records as allowlists for competence, tools, context, output
  contracts, risk, trace policy, eval refs, and budgets.
- Make model calls, tool/action proposals, schema validation, permission decisions,
  approval pauses, structured observations, traces, evals, and budgets harness-owned
  runtime behavior, not prompt-only conventions.

## Constitution Check

- Aligns with Spec Before Code, Bounded Agent Autonomy, low-maintenance MVP scope, and
  stability-first treatment for agent-contract boundaries.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because the shared harness is a permission, approval,
  redaction, trace/eval, provider failure, and no-fake-runtime boundary.
- KISS boundary: one shared loop first; no multi-agent workflow orchestration, broad
  connector inventory, unrestricted tools, or hidden provider memory authority.

## Source Artifacts

- .memory-bank/features/FT-007-shared-agent-harness-and-agent-profile-runtime.md
- .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
- .memory-bank/epics/EP-003-shared-agent-harness-and-context-boundaries.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/message-envelope.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/safety-gate.md
- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- agents-best-practices: model proposes and harness disposes; typed tools are narrow,
  schema-validated, permissioned, observed, traced, budgeted, and never prompt-only
  safety.

## Constraints

- Every product agent is an AgentProfile inside one shared AgentHarness.
- Disabled/deprecated profiles cannot start new product-agent runs.
- Tool arguments reject unknown properties and are locally validated before execution.
- Every tool/action proposal gets exactly one structured observation.
- Permission decisions happen before side effects and are recorded outside the model.
- Missing provider configuration fails clearly and cannot produce fake successful
  product-agent output.

## Invariants

- No separate ungoverned product-agent harness entrypoints.
- No broad `execute_anything`, unrestricted SQL/write, arbitrary HTTP, direct external
  send, direct physical actuation, or hidden provider-memory product tools.
- Secrets, auth material, hidden reasoning, raw provider output, UI Feed replay, and
  unapproved governance content cannot enter agent context or trace summaries visible
  to agents.
- Agno may execute behind the harness only and cannot bypass project-owned validation,
  permission, trace, memory, or publication contracts.

## Steps

1. Build AgentProfile registry, schemas, initial profiles, and profile validation.
2. Implement AgentHarnessRun lifecycle, provider-neutral model adapter boundary, and
   budget/stop handling.
3. Build typed tool registry, proposal validator, and structured observation writer.
4. Implement permission engine decisions and exact-scoped approval-pause handoff.
5. Add trace/eval recorder and harness eval fixture runner.
6. Add Agno boundary/no-fake-runtime diagnostics and contract coverage.

## Expected Touched Files

- backend/app/agent_harness/*
- backend/app/access/*
- backend/app/publication/*
- backend/app/safety/*
- backend/app/db/migrations/*
- backend/app/api/*
- backend/tests/agent_harness/*
- backend/tests/integration/*
- backend/tests/security/*
- .memory-bank/changelog.md

## Tests

- Unit: AgentProfile validation, profile status, tool schema validation, observation
  shaping, budget stop, and provider failure statuses.
- Integration: ActorContext and PlantAccessGrant filtering at harness start, one
  observation per proposal, permission before side effect, approval pause persistence,
  and redacted trace summaries.
- Harness evals: unknown tool, invalid args, permission denial, approval bypass,
  prompt-injection-like content, UI Feed/unapproved proposal leakage, provider
  unavailable, missing provider config, budget stop, and false success claim.
- Security: no secrets/auth material or hidden reasoning in traces, observations, Bus,
  UI Feed, exports, or agent context.

## Quality Gates

- pytest backend/tests/agent_harness backend/tests/integration backend/tests/security
- Harness eval fixture evidence through the task-specific pytest/eval suite and /red-verify semantic-pass
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Start an authorized AgentProfile run and see clear budget/trace status.
- Unknown tool, invalid args, and denied permission each return one structured
  observation.
- Risky side effect pauses for exact scoped approval instead of committing.
- Missing provider configuration fails clearly without fake output.

## Task Slice

- TASK-041: AgentProfile registry, schemas, and initial profile validation.
- TASK-042: AgentHarnessRun lifecycle, provider-neutral adapter boundary, and budgets.
- TASK-043: Typed tool registry, proposal validation, and structured observations.
- TASK-044: Permission engine and approval-pause handoff.
- TASK-045: Trace/eval recorder and harness eval fixture runner.
- TASK-046: Agno boundary, no-fake-runtime, diagnostics, and contract coverage.
