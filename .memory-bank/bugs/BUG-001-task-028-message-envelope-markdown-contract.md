---
description: Open TASK-028 follow-up: runtime code/tests still enforce the superseded candidate-output syntax rule.
status: active
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tasks/TASK-028-T3-FT-007-W1.task.json
  - .memory-bank/tasks/TASK-030-T3-FT-007-W1.task.json
---
# BUG-001 — TASK-028 MessageEnvelope Markdown Contract Breach

## Scope

- Origin task: `TASK-028-T3-FT-007-W1`.
- State: open; scheduler terminal state is `HALT_FAILURE_BUDGET`.
- Follow-up task: `TASK-030-T3-FT-007-W1` (`planned`).

## Historical reproduction

Under the contract then in force, `candidate_output` was required to be
normalized plain UTF-8 text and not Markdown, HTML, or a prompt. In a fresh
PostgreSQL-backed service invocation,
`AgentModelResultV1.from_untrusted` accepts standard single-emphasis Markdown;
the invocation returns `envelope_ready` and places that value unchanged in
`MessageEnvelopeV1.candidate_output`.

## Evidence

- First independent functional failure:
  `.tasks/TASK-028-T3-FT-007-W1/TASK-028-T3-FT-007-W1-S-VERIFY-final-report-docs-01.md`.
- First independent semantic failure:
  `.tasks/TASK-028-T3-FT-007-W1/TASK-028-T3-FT-007-W1-S-RED-VERIFY-final-report-docs-01.md`.
- Retry functional failure:
  `.tasks/TASK-028-T3-FT-007-W1/TASK-028-T3-FT-007-W1-S-VERIFY-final-report-docs-02.md`.
- Retry semantic failure:
  `.tasks/TASK-028-T3-FT-007-W1/TASK-028-T3-FT-007-W1-S-RED-VERIFY-final-report-docs-02.md`.

## Current impact

The historical verification finding remains valid evidence for TASK-028 and is
not rewritten. The current canonical contract now accepts schema-valid
formatting-looking content as opaque untrusted data, so the remaining defect is
the downstream code/test delta: the partial syntax/prompt regex rejects valid
candidate text and must be removed without weakening the strict schema,
authorization, guard, audit, classifier-handoff, or no-authority boundaries.

## Superseded planning blocker

`HALT_FAILURE_BUDGET` remains the terminal state of TASK-028. Its earlier
follow-up planning blocker was the absence of an authoritative recognizer
grammar for Markdown/HTML/prompt-like text.

That recognizer ambiguity is superseded by the owner-approved canonical
decision: no such syntax recognizer is required or permitted at this boundary.
TASK-030 owns the narrow runtime/test alignment and keeps this bug active until
that delta is implemented and independently verified. TASK-028 failure evidence
and TASK-029 blocked lifecycle remain unchanged.
