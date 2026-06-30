---
description: FT-005 - UI Feed and context hygiene.
status: draft
lifecycle: planned
parent_epic: EP-002
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md
---
# FT-005 UI Feed and Context Hygiene

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Keep user-facing display events separate from agent working context so UI Feed, controlled spoiler notes, and educational explanations can support the operator without becoming facts, labels, raw reasoning, or agent-consumable context.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-009, FR-010, UI Feed acceptance criteria, context hygiene non-functional requirements, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-007 and UI/context parts of REQ-013.
- [.memory-bank/constitution.md](../constitution.md): bounded agent autonomy, source-of-truth discipline, no speculation, and KISS.
- [.memory-bank/spec-index.md](../spec-index.md): route map for UI Feed, companion output, context hygiene, and UI/PWA design areas.
- [.memory-bank/testing/index.md](../testing/index.md): context filtering and UI Feed risk-surface gates.

## Use Cases

- The UI displays agent status or controlled spoiler notes to the user.
- A `ui_spoiler_note_ref` links a `MessageEnvelope` to a UI Feed event for presentation.
- Silent agent activity can optionally appear in UI Feed without entering Agent Chat Bus.
- Agents receive only domain-approved Bus events and structured outputs as working context.
- UI-only explanation text is kept out of dataset labels and confirmed facts.

## Acceptance Criteria

- UI Feed is a presentation layer separate from Agent Chat Bus.
- UI Feed events are not passed to agents as working context.
- `ui_spoiler_note` has `consumable_by_agents=false` and `visible_to_agents=false`.
- UI-only explanations are controlled summaries for the user, not raw chain-of-thought.
- `ui_spoiler_note_ref` may be included in `MessageEnvelope`, but only refers to a UI Feed event.
- Ordinary agent conclusions stay 1-3 lines by default.
- Clarification requests are short and targeted.
- Quoted detail replies are 3-7 lines and stay shorter than UI Spoiler Notes.
- UI Feed content does not become confirmed facts or trainable labels.

## Edge Cases / Failure Modes

- UI Feed or spoiler note is included in an agent input context: fail context filtering.
- UI-only explanation is treated as domain fact, plant state, or dataset label: reject.
- Raw chain-of-thought is displayed or persisted as UI Feed content: reject.
- `ui_spoiler_note` has `visible_to_agents=true` or `consumable_by_agents=true`: reject.
- `ui_spoiler_note_ref` points to a Bus event or non-UI artifact: reject.
- Long agent output bypasses concise output rules by being placed directly in UI: reject or summarize through controlled UI policy.

## Test Strategy Pointers

- `schema:ui-feed-event` for UI-only event fields, `visible_to_agents=false`, and `consumable_by_agents=false`.
- `policy:context-filtering` for UI Feed and spoiler notes never entering agent working context.
- `policy:concise-output` for default conclusion, clarification, quoted detail, and spoiler-note length boundaries.
- `integration:ui-feed-presentation` for display-only rendering with no agent context leakage.
- `policy:raw-reasoning-not-source-of-truth` for preventing UI notes from becoming facts or trainable labels.

## Constraints / Invariants

- UI Feed is presentation only.
- Agent Chat Bus is the agent working context.
- Raw chain-of-thought is not exposed, stored as source of truth, or passed to agents.
- UI-only explanations are not confirmed facts and are not trainable data.
- Keep display affordances simple and controlled for MVP.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. `/spec-improve FT-005` completed the feature-local SDD gate.

- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): `UIFeedEvent`, spoiler-note boundary, and display safety rules.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): `ui_spoiler_note_ref` pointer rule.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): UI Feed is presentation only.
- [.memory-bank/invariants.md](../invariants.md): cross-cutting context hygiene rules.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): UI Feed filtering and anti-cheat gates.
- [.memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md](../tech-specs/FT-005-ui-feed-context-hygiene.md): feature-local decisions for UI Feed presentation storage, event payloads, controlled spoiler notes, context filtering, timeline/export snapshots, display safety, API surface, and verification targets.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](../tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): `ui_spoiler_note_ref` pointer validation and concise-output relationship.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](../tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md): agent context allowlist and Bus/UI separation.

No FT-005 design blocker remains for `/prd-to-tasks FT-005`.
