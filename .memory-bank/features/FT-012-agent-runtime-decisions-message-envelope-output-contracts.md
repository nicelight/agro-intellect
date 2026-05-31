---
description: FT-012 - Agent runtime decisions and MessageEnvelope output contracts.
status: draft
lifecycle: planned
parent_epic: EP-002
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md
---
# FT-012 Agent Runtime Decisions and MessageEnvelope Output Contracts

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Define how an invoked agent turns execution output into an explicit runtime decision and, when appropriate, a structured `MessageEnvelope` for downstream domain publication or safety routing.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-007, FR-008, FR-009, FR-010, Agent Chat Bus/output acceptance criteria, edge cases, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 4, 9.3, 9.4, 9.7 through 9.13, 10, 20, 23, and 26 for runtime decisions and `MessageEnvelope` context.
- [.memory-bank/requirements.md](../requirements.md): REQ-006 runtime decision/output contract coverage and concise-output coverage from REQ-007.
- [.memory-bank/constitution.md](../constitution.md): bounded agent autonomy, source-of-truth discipline, no speculation, and KISS.
- [.memory-bank/spec-index.md](../spec-index.md): route map for MessageEnvelope, Agent output/runtime decision, companion output, and Agno boundary design areas.
- [.memory-bank/testing/index.md](../testing/index.md): message envelope, silent audit, and concise-output verification.

## Use Cases

- An invoked agent returns exactly one runtime decision: `speak`, `silent`, `clarify`, or `escalate`.
- `speak` produces a concise consumable conclusion through `MessageEnvelope`.
- `clarify` produces a short missing-data request through `MessageEnvelope`.
- `escalate` produces a Team Signal or Safety Block route through `MessageEnvelope`.
- `silent` leaves audit evidence without creating a `MessageEnvelope` or publishing to Agent Chat Bus.
- `ui_spoiler_note_ref` points from `MessageEnvelope` only to a UI Feed event.

## Acceptance Criteria

- Each invoked agent returns one runtime decision: `speak`, `silent`, `clarify`, or `escalate`.
- `silent` creates no `MessageEnvelope` and no Agent Chat Bus publication.
- `silent` still leaves an audit record.
- `speak` publishes a concise consumable conclusion through `MessageEnvelope`.
- `clarify` publishes a short missing-data request.
- `escalate` publishes a Team Signal or Safety Block.
- Agent work outputs published to the Bus pass through `MessageEnvelope`.
- Ordinary agent conclusions are 1-3 lines by default.
- Clarification requests are short and targeted.
- Quoted detail replies are 3-7 lines and remain shorter than UI Spoiler Notes.
- Large team messages are reserved for Team Signals or Safety Blocks.
- `ui_spoiler_note_ref` may be included in `MessageEnvelope`, but it refers only to a UI Feed event.

## Edge Cases / Failure Modes

- Agent returns no runtime decision or more than one runtime decision: reject or require adapter correction.
- Agent returns `silent` but attempts to create a `MessageEnvelope` or Bus publication: reject publication and keep audit only.
- Agent output is long, unstructured, or mixes raw reasoning with conclusion: reject or adapt to concise `MessageEnvelope`.
- `escalate` output is not a Team Signal or Safety Block: reject or reroute.
- `ui_spoiler_note_ref` points outside UI Feed or to an agent-consumable artifact: reject.
- Safety Block or Team Signal tries to bypass the Bus publication boundary: route through FT-004 and relevant Safety Gate semantics.

## Test Strategy Pointers

- `schema:message-envelope` for output fields, source refs, approval flags, concise output, and `ui_spoiler_note_ref`.
- `policy:runtime-decision-required` for exactly one decision per invoked agent.
- `policy:silent-audit` for no Bus publication plus audit record on `silent`.
- `policy:concise-output` for default 1-3 line conclusions, targeted clarification requests, quoted detail bounds, and large-message routing.
- `policy:ui-spoiler-note-ref` for the pointer rule to UI Feed only.
- `policy:team-signal-safety-block-routing` for `escalate` outputs.

## Constraints / Invariants

- Raw reasoning is not published as domain output.
- Runtime decisions are adapter/domain outcomes, not implicit Agno side effects.
- `silent` never creates agent-consumable Bus content.
- Team Signals and Safety Blocks are the only large working-message routes.
- UI Feed remains presentation only; `ui_spoiler_note_ref` is a pointer, not agent context.
- Agent hypotheses are not trainable labels by default.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. `/spec-improve FT-012` completed the feature-local SDD gate.

- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): runtime decisions, envelope fields, output size, and invalid-output rules.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): Bus publication boundary and influence levels.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): execution adapter rules and `silent` boundary.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): `ui_spoiler_note_ref` target rules.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): schema, adapter, and concise-output gates.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](../tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): feature-local decisions for runtime decision state machine, adapter boundary, `MessageEnvelope` schema, decision-to-event mapping, output-size rules, `silent` audit, safety/escalation boundary, and verification targets.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](../tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md): Bus publication service used after FT-012 validates publishable agent output.

No FT-012 design blocker remains for `/prd-to-tasks FT-012`.
