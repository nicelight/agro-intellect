---
description: MessageEnvelope and agent runtime decision contract.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Message Envelope

## Runtime Decision

Each invoked agent must return exactly one runtime decision:

- `speak`: publish a concise consumable conclusion through `MessageEnvelope`;
- `silent`: publish nothing to Agent Chat Bus and create no `MessageEnvelope`, but leave audit evidence;
- `clarify`: publish a short missing-data request through `MessageEnvelope`;
- `escalate`: publish a Team Signal or Safety Block route through `MessageEnvelope`.

## Envelope Fields

Publishable agent work output uses `MessageEnvelope`:

- `message_id`
- `agent_id`
- `claim_type`
- `confidence`
- `requires_human_approval`
- `can_train_on`
- `source_refs`
- `consumable_output`
- `ui_spoiler_note_ref`

## Stable Identity

- Every validated publishable `MessageEnvelope` MUST have a backend-generated stable `message_id`.
- Recommended `message_id` prefix is `msg_`.
- Canonical reference format is `message:<message_id>`.
- `message_id` identifies the validated agent work output. Bus event IDs, timeline event IDs, UI Feed event IDs, and provider message IDs do not replace it.
- `silent` decisions create no `MessageEnvelope` and no `message_id`.
- Downstream specs reference publishable agent output with `message:<message_id>`. Bus, timeline, UI, and dataset refs may be retained as publication, audit, presentation, or governance refs, but they are not the MessageEnvelope identity.

## Claim Types

MVP claim types:

- `observation`
- `hypothesis`
- `recommendation`
- `safety_block`
- `task_request`
- `clarification_request`
- `quoted_detail_reply`
- `team_signal`

## Output Size Rules

- Ordinary conclusions should be 1-3 lines.
- Clarification requests must be short and targeted.
- Quoted detail replies should be 3-7 lines and remain shorter than UI Spoiler Notes.
- Large working messages are reserved for Team Signals and Safety Blocks.

## Safety and Dataset Rules

- Agent hypotheses default to `can_train_on=false`.
- `can_train_on=true` must satisfy dataset governance rules and cannot be set by an ordinary raw agent hypothesis.
- Physical-action wording requires Safety Gate review before user display or task/action routing.
- `ui_spoiler_note_ref` may point only to a UI Feed event with `visible_to_agents=false` and `consumable_by_agents=false`.

## Invalid Output

Reject or adapt before publication when:

- runtime decision is missing or duplicated;
- `silent` attempts to publish a message;
- a publishable decision lacks a backend-generated `message_id`;
- output is raw reasoning, long unstructured prose, or mixes hidden reasoning with conclusions;
- source refs are missing where the output affects state, safety, tasking, review, or dataset decisions;
- `ui_spoiler_note_ref` points outside UI Feed.
