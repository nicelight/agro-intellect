---
description: Global UI Feed projection contract for MVP v2.
status: active
type: contract
last_updated: 2026-07-28
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
---
# UI Feed

## Scope

UI Feed is the human-facing presentation stream for cards, prompts, messages,
history snippets, task/approval cards, storage warnings, and admin notices. It
is not Agent Chat Bus, not MessageEnvelope, not timeline authority, and not
agent working context.

The verified FT-000 executable baseline does not implement UI Feed runtime
code. This contract is a global guardrail; concrete projection payloads,
frontend routes, and component behavior belong to feature-level SDD design
inside `/feature-to-tasks FT-008`, `/feature-to-tasks FT-016`, or another owning
feature when a projection is feature-specific.

## Contract Scope

- Defines: global presentation-only rules, projection boundary, consumability
  flags, redaction expectations, and verification requirements for keeping UI
  content out of agent context.
- Out of scope: concrete frontend component layout, route/view map, exact card
  payload fields, endpoint schemas, or task execution state machines.
- Related specs:
  - [.memory-bank/contracts/agent-chat-bus.md](agent-chat-bus.md): defines
    agent-consumable working events.
  - [.memory-bank/contracts/message-envelope.md](message-envelope.md): defines
    validated pending agent-output boundary before classification and UI
    projection.
  - [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
    defines the canonical ordered roster and deterministic introduction
    metadata.
  - [.memory-bank/contracts/timeline-event.md](timeline-event.md): defines
    append-only audit/export events.
  - [.memory-bank/domains/safety-action-routing.md](../domains/safety-action-routing.md):
    owns authoritative Safety decisions, exact project summaries, evidence
    snapshots, and expiry projected by the Safety variant.

## UIFeedEvent version 1

FT-008 establishes one strict Plant-scoped object with unknown fields rejected;
later owning features may add only the registered additive variants below:

- `schema_version=1`;
- `ui_event_id`: UUID; introductions reuse their deterministic
  `introduction_id`, other projections use application-generated UUIDv4;
- `created_at`: timezone-aware UTC timestamp;
- `farm_id`, `plant_id`: native UUID identities;
- `source_type`: `system | agent_message | safety | companion_governance`;
- `source_id`: stable primary introduction/message/Safety-decision/governance-record identity;
- `source_refs`: zero through four unique safe `kind:identifier` refs;
- `display_kind`: `agent_introduction | agent_message | block_notice |
  safety_status | companion_governance`;
- `display_payload`: exactly one variant below;
- `visible_to_roles`: non-empty unique subset of
  `boss|engineer|consultant`;
- `visible_to_agents=false`;
- `consumable_by_agents=false`.

Payload variants:

- `agent_introduction`: exactly
  `{payload_kind:"agent_introduction",agent_id,display_name,competence_summary,introduction_text,roster_version}`
  copied from the strict canonical introduction item.
- `agent_message`: exactly
  `{payload_kind:"agent_message",agent_id,candidate_claim_type,quoted_text}`;
  `quoted_text` equals the authorized/classified candidate and remains literal
  presentation data.
- `block_notice`: exactly
  `{payload_kind:"block_notice",notice_code:"classification_uncertain",text:"Сообщение заблокировано до уточнения безопасности."}`;
  it never copies candidate text.

For `agent_introduction`, the unchanged outer mapping is exact:

- `ui_event_id=introduction_id`, `source_type=system`,
  `source_id=<introduction_id>`;
- `source_refs=["agent_roster:<roster_version>",
  "agent_introduction:<introduction_id>"]`;
- `display_kind=agent_introduction`;
- `visible_to_roles=["boss","engineer","consultant"]`;
- both agent flags are false.

`created_at` is assigned only on the first insert. Lazy materialization never
rewrites this mapping or any existing introduction row.

For `display_kind=safety_status`, `display_payload` is exactly:

```text
{
  payload_kind:"safety_status",
  decision_ref:"safety_decision:uuid",
  classification_ref:"safety_classification:uuid",
  action_kind:"ph_adjustment|ec_adjustment|solution_change|pump_command|light_command|dosing_command|pruning|transplanting|root_trimming|other_physical_action",
  safety_status:"safety_blocked|needs_fresh_evidence|pending_human_approval",
  reason_code:"unsupported_action|approval_authority_missing|approval_input_missing_or_stale|ready_for_human_approval",
  summary_text:"exact project-owned literal text",
  evidence_refs:["manual_measurement:uuid"],
  approval_input_freshness:null|{
    purpose:"approval_input",window_hours:2,computed_at:"UTC timestamp",
    ph:{status:"fresh|stale|missing",source_ref:null|"manual_measurement:uuid",measured_at:null|"UTC timestamp"},
    ec:{status:"fresh|stale|missing",source_ref:null|"manual_measurement:uuid",measured_at:null|"UTC timestamp"}
  },
  expires_at:null|"UTC timestamp"
}
```

`decision_ref` supplies `source_id`. `evidence_refs` contains the unique present
pH/EC refs in pH-then-EC order and has zero through two items. Unsupported and
approval-authority blocks have null freshness/expiry. Missing/stale evidence
has the exact computed snapshot and null expiry. Pending approval requires a
supported kind, both statuses `fresh`, non-empty evidence refs, and the exact
expiry from the Safety Action Routing data spec. All variants use only the
project-owned summary; candidate text is forbidden.

For `display_kind=companion_governance`, `display_payload` is exactly one of:

  - `{payload_kind:"companion_attention",attention_ref:"companion_attention:uuid",issue_ref:"companion_issue:uuid",summary_text:"compact literal text"}`;
  - `{payload_kind:"companion_proposal",proposal_ref:"companion_proposal:uuid",issue_ref:"companion_issue:uuid",proposal_state:"pending|approved|rejected|superseded",summary_text:"compact literal text"}`;
  - `{payload_kind:"companion_decision",decision_record_ref:"decision_record:uuid",issue_ref:"companion_issue:uuid",proposal_ref:"companion_proposal:uuid",decision_summary:"compact literal text",safety_gate_authority:"not_granted"}`.

For these variants, `source_id` is the UUID contained in the primary record
ref for the selected payload. Exact compact-text normalization and bounds are
owned by the FT-013 canonical governance payload contract; raw proposal text,
raw rationale, raw chat, and UI markup are never copied into these projections.
Alias kinds such as `issue:` and `human_attention_needed:` are invalid; all
Companion projections use the same FT-013 ref grammar as HTTP, provider input,
Bus resolution, and PostgreSQL-derived views.

`display_payload` must not be reused as agent input, runtime truth, timeline
authority, task/action authority, URL/action input, or HTML/Markdown source.

## Rules

- UI Feed may project candidate text only for non-Companion
  `safe_information` with the matching `SafetyClassificationResultV1`, derived
  `ClassificationConsumerRouteV1=ordinary_dispatch`, and current guard. Other
  ordinary-dispatch classes use an authoritative task/Safety record or a
  generic block notice; the notice never copies candidate text. UI Feed may
  also project authorized domain, timeline, admin, storage, and Companion
  records under their owning contracts.
- Candidate text on that authorized/classified route is rendered literally
  through escaped/text-node semantics (for example, framework text
  interpolation or `textContent`). UI Feed never sends it through an HTML or
  Markdown renderer, raw-HTML insertion, URL/link activation, or action parser.
  Markup-, prompt-, instruction-, command-, and URL-looking sequences remain
  inert visible text.
- UI Feed is the visible projection owner for deterministic roster
  introductions. Only an authorized `GET` Feed access for a currently active
  Plant may materialize missing canonical rows. The current authorization and
  active Plant state are locked/rechecked in the same transaction as those
  inserts. Existing rows remain unchanged; deterministic ids and
  `(plant_id, agent_id, roster_version)` uniqueness make repeat, concurrent,
  and retried opens idempotent. The Plant chat/feed UI renders those same rows;
  no introduction is copied to Agent Chat Bus. Introductions remain
  `visible_to_agents=false` and `consumable_by_agents=false`.
- Plant creation/`201`, process startup, restore, and archived
  retained-history Feed reads create no introduction rows. There is no
  introduction batch, sink, pending state, background scan, or reconciliation
  lifecycle.
- UI Feed must never publish directly to Agent Chat Bus.
- UI Feed, UI markdown, cards, spoiler notes, raw chat, and admin notices must
  never enter agent working context. An agent-specific provider assembler may
  load typed governance content from PostgreSQL authority, never from UI Feed.
- Candidate text displayed by UI Feed must not be copied into agent context,
  runtime instructions, command handlers, routing inputs, or authority fields.
- UI Feed may show a Safety block or pending approval prompt, but it cannot
  authorize a physical action.
- A `safety_status` event is derived only from the immutable authoritative
  Safety decision. It is visible to `boss|engineer`, remains non-consumable,
  and its summary, freshness snapshot, or expiry cannot approve, execute, or
  refresh the decision.
- UI Feed may show a DecisionRecord summary, but it cannot make raw proposal
  text, raw rationale, or raw chat agent-consumable.
- Companion projections are human presentation of authoritative governance
  records, not copies of their mutable state. `companion_attention` and
  `companion_proposal` never publish to Bus. Only the separate guarded
  DecisionRecord reference defined by Agent Chat Bus may become
  agent-consumable.
- Canonical Companion classification uses
  `companion_governance_hold`. Its `safe_information` result creates no FT-008
  `agent_message`, and its `safe_task_request` creates neither an FT-008 row nor
  an FT-012 Task. Held `physical_action|blocked_uncertain|mismatch|failure`
  creates no generic block, Safety-status, or candidate row. Only the later
  governance command may write the compact dedicated attention/proposal/
  decision summaries above; raw candidate/proposal/rationale/provider text is
  never copied into UI Feed.
- UI Feed must apply the same ActorContext and PlantAccessGrant visibility
  constraints as backend reads.
- Secrets, tokens, auth headers, `.env` values, provider payloads, hidden
  reasoning, and credentials must not appear in UI Feed.

Persisted Plant feed reads use the protected
`.memory-bank/contracts/plant-feed-http.md` boundary. Actual Svelte/PWA DOM
rendering remains FT-016 ownership because no frontend scaffold exists in the
current brownfield tree; that consumer must render these text fields through
text-node/framework interpolation semantics.

## Edge Cases And Errors

- If projection source authorization cannot be proven, do not emit the UI Feed
  event.
- A classification result or stale MessageEnvelope authorization snapshot is
  not proof of current visibility. The projection writer applies the canonical
  current authorization and active-Plant guard in the same write boundary.
- If a source record is valid but unsafe for agents, UI Feed may still show a
  redacted human notice with `consumable_by_agents=false` only when its owning
  contract permits that projection. A Companion governance hold permits no
  ordinary candidate/block/Safety notice.
- If a projection references archived Plant history, it must use an explicit
  retained-history authorization path.
- Existing introduction rows remain retained while their Plant is archived.
  An archived retained-history read writes nothing. Restore writes nothing; a
  later authorized active-Plant Feed open may insert only rows still missing
  after reloading current authorization and Plant state.
- Companion projection writes require current authorization and
  `Plant.status=active`. Archive preserves existing UI rows for authorized
  retained-history reads but blocks new governance projections; restore does
  not replay them without a fresh owning FT-013 command.
- If a projection references physical-action wording, it must show the current
  Safety Gate/task state instead of cleared action wording unless the safety
  lifecycle permits that wording.
- Classification retry, process restart, restore, or reconciliation cannot
  replay a held Companion candidate into UI Feed. Ordinary non-Companion
  classified publication and generic block behavior remain unchanged.
- Safety status projection never copies physical-action candidate wording.
  Archive preserves an existing row for authorized retained history but blocks
  a new decision/projection; restore does not replay it.

## Verification

Tests must prove:

- UI Feed projections are filtered by ActorContext and PlantAccessGrant.
- UI Feed content is absent from agent context builder fixtures.
- `visible_to_agents=false` and `consumable_by_agents=false` are preserved for
  UI-only content.
- Safety Gate approval, DecisionRecord approval, and UI prompt display remain
  separate authority classes.
- all Safety status matrix combinations reject unknown fields, preserve exact
  project-owned non-imperative summaries, carry at most two authoritative
  evidence refs, and never expose candidate text or grant approval/action
  authority.
- Redaction removes secrets/auth material from UI Feed output.
- Representative HTML/Markdown/prompt-/URL-looking candidate strings render
  literally with no active element, link, command, or action side effect.
- Candidate display remains unavailable to agent context/runtime authority;
  exact component and e2e mechanics remain owned by FT-008/FT-016.
- all three Companion variants reject unknown fields, preserve literal text,
  keep both agent flags false, and cannot grant governance, task, Plant-state,
  or Safety authority.
- held Companion safe-information/task/physical/blocked/mismatch/failure paths
  write no ordinary candidate/block/Safety UI row, retry/restore does not
  replay one, and non-Companion FT-008 behavior remains compatible.
- roster-introduction checks prove only an authorized active-Plant Feed open
  inserts missing rows; Plant create/startup/restore/archived reads write none;
  retries and concurrent opens do not duplicate rows; existing rows remain
  unchanged; persistence failure returns through `FEED_PERSISTENCE_FAILED`; and
  no introduction enters Agent Chat Bus or agent context.
