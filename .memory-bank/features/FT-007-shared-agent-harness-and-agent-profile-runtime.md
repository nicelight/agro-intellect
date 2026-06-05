---
description: Feature FT-007 for shared AgentHarness, AgentProfile definitions, model loop, tools, permissions, observations, traces, evals, and budgets.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
epic: EP-003
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
---
# FT-007 Shared AgentHarness And AgentProfile Runtime

## Use Cases

- Product agent runs as an AgentProfile inside the shared harness.
- Model proposes a tool/action/output; harness validates schema and permission policy.
- Harness executes, denies, pauses for approval, or records structured observation.
- Harness records trace/eval evidence and stops on budget or completion.

## Acceptance Criteria

- All product agents share one project-owned AgentHarness/control plane.
- Agent-specific behavior is explicit in AgentProfile definitions: competence boundary,
  allowed context, tools, output contracts, risk boundaries, and memory scope.
- Model calls, tool/action proposals, schema validation, permission decisions,
  approval pauses, structured observations, context updates, traces, evals, and budgets
  are harness concerns, not prompt-only conventions.
- Every tool/action proposal receives a structured observation, including denial,
  timeout, validation error, approval pause, or abort.
- Agno remains execution layer only and cannot become source of truth or domain coordinator.

## Edge Cases & Failure Modes

- Unknown tool request returns structured error instead of silent failure.
- Invalid tool arguments are rejected before execution.
- Risky side effects pause for exact scoped approval.
- Budget exhaustion stops with clear status and next safe action.
- Separate ungoverned product-agent harnesses are forbidden.

## Test Strategy Pointers

- `test:harness.shared-profile-control-plane`
- `test:harness.loop-permission-observation-trace`
- `test:harness.approval-bypass-attempt`
- `test:harness.step-token-cost-budget`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): shared harness requirements.
- [.memory-bank/invariants.md](../invariants.md): AgentHarness MUST/NEVER rules.
- `agents-best-practices`: doctrine for provider-neutral loop, permissions, traces, evals, and budgets.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-007` are complete. Use
[.memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md](../tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md)
as the feature-local design hub before `/prd-to-tasks FT-007`.
