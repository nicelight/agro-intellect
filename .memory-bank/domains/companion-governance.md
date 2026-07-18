---
description: PostgreSQL authority, transactions, idempotency, and projection ownership for Companion governance.
status: active
type: data_spec
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/domains/task-approval-outcomes.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/timeline-event.md
---
# Companion Governance Data

## Scope

Defines the exact PostgreSQL records, relations, uniqueness, fingerprints,
locking, transaction boundaries, Timeline refs, and Bus/UI projection
ownership for Plant-scoped Companion governance.

## Out of scope

- Provider request/result schemas and model invocation;
- Safety Gate approval, `action` Task creation, Plant-state mutation, frontend
  layout, workers, schedulers, reminders, outbox, or Timeline replay;
- a persisted CompanionConclusion, separate IssueStack table, or persisted
  Companion runtime receipt/MessageEnvelope replay store.

## Shared storage rules

- Primary and foreign keys are native PostgreSQL UUID mapped as Python
  `uuid.UUID`; new ids are application-generated UUIDv4.
- Farm/Plant/history relations use `ON DELETE RESTRICT`; governance rows are
  never hard-deleted.
- Timestamps are server-owned timezone-aware UTC values.
- Human/model text is normalized, trimmed UTF-8 without control characters.
  Compact summaries are `1..500` Unicode code points; proposal/rationale and
  ordinary-task display text are `1..2000` code points.
- Safe refs are ordered unique ASCII `kind:<lowercase-canonical-uuid>` arrays.
  FT-013 owns exactly `companion_issue:<issue_id>`,
  `companion_attention:<attention_id>`,
  `companion_proposal:<proposal_id>`, and
  `decision_record:<decision_record_id>`. It reuses shared
  `plant:<plant_id>`, `daily_checkin:<check_in_id>`,
  `manual_measurement:<measurement_id>`,
  `message_envelope:<message_id>`,
  `safety_classification:<message_id>`, and `task:<task_id>`. Aliases such as
  `issue:`, `human_attention_needed:`, `proposal:`, or `decision:` are invalid.
  `CompanionConclusionV1` has no self-ref because it is derived; its nullable
  relation refs use the exact FT-013 kinds above. Auth material, provider
  payloads, hidden reasoning, UI payloads, raw chat, and arbitrary metadata are
  forbidden.
- Fingerprints are lowercase SHA-256 of canonical compact UTF-8 JSON with
  sorted object keys, canonical UUID/timestamp strings, original Unicode, and
  no insignificant whitespace.

## `companion_issues`

One row is one retained Plant-scoped issue:

- `issue_id`: UUID primary key;
- `farm_id`, `plant_id`: restrictive UUID FKs;
- `status`: `open|resolved|closed`;
- `is_focused`: non-null boolean;
- `summary_text`: compact human-visible issue summary;
- `record_version`: positive integer, initially `1`, incremented by every
  focus, resolution, or close mutation;
- `created_by_run_id`: UUIDv4 of the Companion run that created the issue;
- `created_at`, nullable `resolved_at`, nullable `closed_at`;
- nullable `close_request_id`, `close_request_fingerprint`;
- `opened_event_ref`, nullable `resolved_event_ref`, nullable
  `closed_event_ref` in the canonical Timeline ref shape.

Checks enforce `open` has no resolution/close fields, `resolved` has
`resolved_at` but no close fields, and `closed` has both timestamps and
complete close request/event fields. Resolved/closed rows cannot be focused.
A partial unique index permits at most one `is_focused=true` row per Plant.
`created_by_run_id` is unique.

`IssueStackV1` is derived by listing these rows for one authorized Plant,
ordered ascending by `(status_rank,created_at,issue_id)`, where the exact rank
is `open=0`, `resolved=1`, and `closed=2`. The nullable focused issue is
identified by the partial unique row. IssueStack is not stored separately, and
the HTTP cursor carries the same rank as its first ordering component.

An issue detail orders retained attention by
`(attention_sequence ASC,attention_id ASC)`, proposals by
`(proposal_sequence ASC,proposal_id ASC)`, and DecisionRecords by
`(decided_at ASC,decision_record_id ASC)`. Its singular `attention` is the
active row when one exists; otherwise it is the final row ordered by
`(attention_sequence DESC,attention_id DESC)`, or null when no attention has
ever existed. A latest DecisionRecord is the first row ordered by
`(decided_at DESC,decision_record_id DESC)`.

## `companion_human_attention`

One row is one human-attention cycle for an issue:

- `attention_id`: UUID primary key;
- `farm_id`, `plant_id`, `issue_id`: restrictive UUID FKs;
- `attention_sequence`: positive per-issue sequence;
- `status`: `active|satisfied`;
- `summary_text`: compact literal attention summary;
- `current_proposal_id`: restrictive UUID FK to the current proposal;
- `record_version`: positive integer, initially `1`, incremented when the
  current proposal is replaced or attention is satisfied;
- `created_at`, nullable `satisfied_at`, nullable
  `satisfied_by_decision_record_id`.

`(issue_id,attention_sequence)` is unique and a partial unique index permits
at most one active attention per issue. Active rows have no satisfaction
fields; satisfied rows have both. The attention/current-proposal relation uses
deferrable restrictive FKs so the first attention and proposal can be inserted
atomically without a nullable committed state.

## `companion_proposals`

One row is one immutable-version proposal attempt:

- `proposal_id`: UUID primary key;
- `farm_id`, `plant_id`, `issue_id`, `attention_id`: restrictive UUID FKs;
- `proposal_sequence`: positive monotonic per-issue sequence;
- `state`: `pending|approved|rejected|superseded`;
- `record_version`: `1` while pending and `2` after its only terminal
  transition;
- `proposal_summary`, `proposal_text`, nullable `rationale_text`;
- `proposed_effect`:
  `discussion_only|check|measurement|follow_up|none`;
- nullable `task_display_text`, present exactly for
  `check|measurement|follow_up` and absent otherwise;
- `suggested_resolution`: `keep_open|resolved`;
- `source_run_id`, `source_message_id`, and
  `source_classification_message_id`: UUIDs identifying the explicit run,
  pending MessageEnvelope, and persisted matching classification;
- ordered `source_refs` including the authoritative run input refs plus the
  message/classification refs;
- `run_request_fingerprint`;
- `created_at`, nullable `terminal_at`, nullable `decision_record_id`;
- `created_event_ref`, nullable `superseded_event_ref`.

`(issue_id,proposal_sequence)` and `source_run_id` are unique. A partial unique
index permits one pending proposal per issue. The message/classification ids
are equal and unique under the implemented FT-011 classification authority.
Pending rows have version `1` and no terminal/decision fields. Approved or
rejected rows have version `2`, terminal time, and DecisionRecord. Superseded
rows have version `2`, terminal time, and a supersede event but no decision.

Proposal `source_refs` contain exactly the one-through-four provider-request
record refs in their request order, followed by
`message_envelope:<source_message_id>` and
`safety_classification:<source_classification_message_id>`. They therefore
contain three through six items, remain unique, and never include run identity,
proposal self-ref, Timeline refs, UI refs, or caller-supplied refs.

## `decision_records`

One immutable row is the successful human decision and effect result:

- `decision_record_id`: UUID primary key;
- `farm_id`, `plant_id`, `issue_id`, `proposal_id`, `attention_id`: restrictive
  UUID FKs; `proposal_id` is unique;
- `decision`: `approved|rejected`;
- `decision_summary`: compact normalized human summary;
- `allowed_workflow_effect`:
  `discussion_only|check|measurement|follow_up|none`;
- `issue_resolution`: `keep_open|resolved`;
- nullable `workflow_effect_ref`, present exactly as `task:<uuid>` for the
  three Task effects and null for `discussion_only|none`;
- `decider_account_id`, `decider_membership_id`,
  `decider_role_preset=boss|engineer`, `decider_permission_source`, nullable
  `decider_grant_id`;
- `request_id`: unique UUIDv4 command identity;
- `request_fingerprint`: canonical decision fingerprint;
- `decided_at`, ordered `source_refs`, `decision_event_ref`;
- `safety_gate_authority`: literal `not_granted`.

Approval copies the proposal effect exactly. Rejection always stores `none` and
has no workflow ref. There is no status, retry counter, failed effect, mutable
summary, raw proposal/rationale copy, or Safety/action authority field.

DecisionRecord `source_refs` are derived, never caller-supplied, in this exact
order:

1. `companion_issue:<issue_id>`;
2. `companion_attention:<attention_id>`;
3. `companion_proposal:<proposal_id>`;
4. `safety_classification:<proposal.source_classification_message_id>`;
5. each provider-request input ref from the proposal, in its original order,
   after removing the already present issue ref.

The array therefore has five through seven unique items. It excludes the
transient MessageEnvelope ref, DecisionRecord self-ref, workflow Task ref,
Timeline refs, UI refs, and actor/auth refs; those identities have their own
typed fields. The canonical ordinary-task branch separately derives its exact
Task refs from DecisionRecord/proposal/message/classification authority.

## Derived `ApprovedGovernanceSummaryV1`

Agent context resolves one non-persisted strict summary from an immutable
approved DecisionRecord and its approved proposal. Fields serialize in this
exact order:

1. `schema_version=1`;
2. `decision_record_id`, `decision_record_ref`;
3. `plant_id`, `plant_ref`;
4. `issue_id`, `issue_ref`;
5. `proposal_id`, `proposal_ref`, `proposal_version=2`;
6. `decision=approved`, `decision_summary`;
7. `allowed_workflow_effect`;
8. `decider_role_preset=boss|engineer`;
9. `decided_at`;
10. `source_refs` exactly equal, item for item and in order, to the immutable
    DecisionRecord `source_refs`;
11. `safety_gate_authority=not_granted`.

UUID ids and derived refs use the canonical forms above; timestamps are UTC
RFC 3339 strings. Unknown or nullable fields do not exist in this schema. The
summary is eligible only when the DecisionRecord is approved, its proposal is
`approved`, version `2`, and linked back to that same record, and current
normal-read authorization plus `Plant.status=active` succeeds. A rejected,
missing, mismatched, archived, unauthorized, or otherwise non-projectable
record is omitted from agent context rather than weakened or reconstructed
from Bus/UI/Timeline data.

The summary excludes issue focus/status, current attention, conclusion state,
workflow Task state, proposal/task display text, rationale, raw chat/provider
content, account/membership/grant ids, UI payloads, Timeline refs, and mutable
projection data. The Bus persists only the DecisionRecord reference; this DTO
is derived on authorized context read and creates no second governance or Bus
authority.

## Derived `CompanionConclusionV1`

Reads derive one strict summary containing:

- `schema_version=1`, `issue_id`, `issue_status`, `is_focused`;
- `conclusion_status=awaiting_human|decided|closed`;
- nullable `current_attention_ref`, `current_proposal_ref`,
  `latest_decision_record_ref`;
- nullable `decision`, `decision_summary`, `allowed_workflow_effect`,
  `decided_at`;
- `safety_gate_authority=not_granted`.

It contains no raw proposal/rationale/chat and is never persisted or emitted as
a Timeline event.

Every field is present in serialization; nullable fields use JSON `null` and
are never omitted. The exact discriminant matrix is:

| `conclusion_status` | Issue state/focus | Current refs | Latest-decision group |
|---|---|---|---|
| `awaiting_human` | `open`, focused or unfocused | active `current_attention_ref` and its pending `current_proposal_ref` are non-null | all latest-decision fields are null when no prior decision exists; otherwise `latest_decision_record_ref`, `decision`, `decision_summary`, `allowed_workflow_effect`, and `decided_at` are all non-null from the deterministic latest row |
| `decided` | `open`, focused or unfocused after a prior `keep_open`, or `resolved` and not focused | both current refs are null | the complete latest-decision group is non-null |
| `closed` | `closed`, not focused | both current refs are null | the complete latest-decision group is non-null |

Focus is an independent Plant navigation axis for open issues. Moving focus to
another open issue does not invalidate either permitted open conclusion row:
an active attention/pending proposal remains `awaiting_human`, while a
satisfied attention with a latest keep-open DecisionRecord remains `decided`.
No other combination is valid. In particular, a partial latest-decision group,
an awaiting conclusion without an active/current pair, an open decided issue
without a complete latest decision, a focused resolved or closed issue, or a
closed issue without a prior DecisionRecord is an authoritative-read
inconsistency; the repository fails closed rather than inventing nulls or
selecting projection data.

## Proposal persistence transaction

`persist_companion_proposal` receives only a validated Companion runtime
handoff, matching persisted classification, current ActorContext, and the run
request fingerprint. The envelope/classification origin MUST be canonical
`companion`, so the shared server-derived consumer route is exactly
`companion_governance_hold`. Any other/mismatched/caller-selected route is
ineligible.

1. Lock/reload current session, membership, Plant, grant, and require active
   Plant plus `can_operate=true` for Boss or granted Engineer.
2. Lock the Plant's currently focused issue when present. For a new issue,
   insert one open focused issue; for an existing issue, lock it and require
   `open`, expected version, same Plant, and current authorization. If another
   issue was focused, clear its focus and increment its version; set the target
   focused and increment its version only when that flag actually changes.
3. Lock the active attention/current pending proposal. If attention is active,
   reuse it, supersede the current pending proposal, and advance its current
   proposal/version. Otherwise create a new attention sequence.
4. Insert the new pending proposal with the next issue sequence.
5. Insert/update the strict non-consumable attention/proposal UI rows. Proposal
   `ui_event_id` equals `proposal_id`; an existing proposal projection is
   updated in place when its authoritative state becomes terminal.
6. Append the required opened/created/superseded Timeline events and persist
   their refs, then commit all PostgreSQL rows together.

The held classification can produce only this governance transaction. It
never invokes ordinary FT-008 Bus/UI candidate publication, FT-011 Safety
routing, or the FT-012 `classified_message` Task branch. Compact proposal/
attention UI rows are derived from the committed governance authority and
never copy raw proposal text, rationale, provider text, or candidate output.

The source run id plus fingerprint is the natural idempotency key. An identical
committed retry returns the existing issue/attention/proposal and its persisted
classification ref. Those committed records are sufficient to form the safe
`proposal_duplicate` governance refs, but they are not a persisted Agent
Runtime outcome and never reconstruct or replay a transient MessageEnvelope.
A different target/content with the same id conflicts. Concurrent attempts for
the same run id may both execute the provider, but uniqueness plus re-read
permits only one product effect; the loser returns identical duplicate or
conflict.

Different run ids are not duplicates and do not conflict merely because they
overlap in wall-clock time. The Plant/focus and target-issue locks serialize
their persistence transactions. If both remain current:

- two existing-issue runs both commit in lock order; the second writer assigns
  the next proposal sequence, supersedes the first writer's pending proposal,
  and keeps the same active attention;
- two new-issue runs both create retained open issues/proposals in lock order;
  the second writer clears the first issue's focus and becomes the only focused
  issue.

The successful governance write order, not provider completion,
`requested_at`, or UUID lexical order, defines which command is later. A
different run conflicts only when an intervening decision/close/focus version,
archive, authorization change, or another stated current guard makes its
target ineligible. Provider I/O is never held inside this transaction.

There is no classification-effect replay worker or receipt. Retry, restart,
restore, and reconciliation cannot turn a held classification into an
ordinary Bus/UI/Safety/Task effect. A later DecisionRecord transaction is the
only possible workflow-effect authority.

## Decision transaction

`decide_companion_proposal`:

1. Locks and reloads current session/membership/Plant/grant, then the Plant's
   currently focused issue when any, target issue, attention, proposal,
   matching classification, and existing DecisionRecord by proposal or
   request id. The Plant lock serializes this focus order with proposal runs.
2. Requires active Plant, current `can_operate`, role `boss|engineer`, current
   pending proposal at `expected_version=1`, active attention pointing to it,
   open issue, and exact scope.
3. Builds the canonical request fingerprint from schema version, request id,
   Plant/issue/proposal ids, expected version, decision, decision summary, and
   issue resolution.
4. Applies proposal terminal state, attention satisfaction, and immutable
   DecisionRecord. `issue_resolution=keep_open` leaves the target open and
   makes it focused, atomically clearing and version-incrementing a different
   previously focused open issue; the target version increments only when its
   focus flag changes. `resolved` makes the target resolved and unfocused
   without changing another issue's focus. The source graph is flushed in the
   caller-owned UoW before an operative Task call.
5. For `check|measurement|follow_up`, calls the existing ordinary-task service
   through its canonical `source_branch=governance_decision` command branch
   inside the same SQLAlchemy Session/UoW. It passes the immutable approved
   DecisionRecord and the owning proposal that was locked pending version `1`
   at decision start and is now flushed approved version `2` for that same
   record, plus satisfied attention, matching persisted classification, exact
   kind/text, DecisionRecord request identity/fingerprint, and caller-owned
   UoW. The Task service derives refs/fingerprint, revalidates current Task
   authority and the exact post-transition graph, flushes without commit, and
   returns the resulting Task ref.
   `discussion_only|none` call no Task.
6. For approval, inserts the guarded DecisionRecord Bus reference whose context
   resolver returns exactly `ApprovedGovernanceSummaryV1`; rejection inserts
   no Bus fact. Both update proposal UI and insert the decision UI row.
   `event_id`/`ui_event_id` use the UUIDv4 `decision_record_id`; Bus stores only
   the approved DecisionRecord ref.
7. Appends `companion_decision_recorded` plus
   `companion_issue_resolved` when applicable, persists refs, and commits.

Every DB mutation/effect/projection is all-or-nothing. Invalid/unknown effect,
Task failure, projection conflict, Timeline append failure, or DB failure rolls
back the PostgreSQL transaction and returns no DecisionRecord. A Timeline line
already appended before a later commit failure remains non-authoritative noise.

`proposal_id` and `request_id` are idempotency keys. Identical retry returns the
first result. Opposite decision, stale version, reused request id with different
fingerprint, terminal/superseded proposal, or mismatched current attention is a
conflict with no effect.

## Ordinary-task source extension

The implemented FT-012 `tasks` table and its single canonical
`create_ordinary_task` service are extended narrowly; FT-013 MUST NOT create a
parallel Task writer:

- add `source_type=governance_decision`;
- add nullable unique restrictive `decision_record_id`;
- require kind `check|measurement|follow_up`, matching proposal effect and
  persisted safe-task classification;
- require `classification_message_id` null for the new source identity while
  preserving message/classification refs in `source_refs`;
- keep `action`, approval, completion, Outcome, device, and Plant-state
  authority forbidden;
- derive the exact DecisionRecord/proposal/message/classification/upstream Task
  refs and governance-command fingerprint owned by the Task contract;
- use the DecisionRecord request identity and same active-Plant/current Task
  authority within the caller's transaction;
- flush but never independently commit, roll back, or close the caller-owned
  SQLAlchemy Session/UoW.

All existing FT-012 source matrices and rows remain valid.

## Close transaction

`close_companion_issue` requires current Boss/granted-Engineer `can_operate`,
active Plant, `status=resolved`, exact expected version, and a unique request
id/fingerprint. It transitions to `closed`, clears focus, appends
`companion_issue_closed`, and commits the ref atomically. Identical retry
returns the closed row; every other terminal/reused/stale request conflicts.

## Bus/UI compatibility changes

- Extend existing strict validators and DB constraints additively for
  `decision_record` Bus refs and the three `companion_governance` UI variants.
- `agent_bus_events.authorization_scope` becomes nullable only for backend
  domain adapters; actor-originated rows remain non-null. Context reconstruction
  must reload DecisionRecord/summary through this repository and omit missing,
  unauthorized, non-projectable, or archived operational state.
- Existing FT-008/FT-011 rows, uniqueness, literal text, and agent-consumability
  flags remain unchanged.
- Attention/proposal/decision UI rows are derived only. They never transition
  governance or serve as Task/Safety authority. Their role visibility includes
  authorized Consultant read context, while every mutation remains restricted
  to Boss/granted Engineer by the owning command.

Projection `source_refs` are derived in these exact orders and remain within
the shared four-ref Bus/UI limit:

- attention UI: issue, attention, current proposal;
- proposal UI: issue, attention, proposal, matching Safety classification;
- decision UI: issue, proposal, DecisionRecord, then workflow Task when
  non-null;
- approved DecisionRecord Bus row: DecisionRecord, issue, proposal, then
  workflow Task when non-null.

Each word above means its canonical ref kind from the shared storage rules.
The Bus `record_ref` equals the first DecisionRecord ref. A terminal proposal
UI update keeps the original ref order and event identity; it changes only the
strict state/version/summary projection fields.

Timeline event `source_refs` are also exact:

- issue opened and proposal created: the owning proposal `source_refs`;
- proposal superseded: issue, attention, superseded proposal, replacement
  proposal;
- decision recorded: DecisionRecord `source_refs`, followed by the workflow
  Task ref when non-null;
- issue resolved: issue, DecisionRecord;
- issue closed: issue.

The Timeline event's `source_type/source_id` remains its primary source
identity and is not duplicated merely to change the arrays above. Payload
`source_ref_count` equals the final event array length where that field is
registered.

## Migration sequence

Two ordered additive FT-013 revisions keep the proposal-authority and binding
decision-effect outcomes independently executable without weakening the final
schema:

1. The governance-aggregate revision runs after the actual implemented FT-012
   head. It creates all four governance tables, including the otherwise-unused
   DecisionRecord table needed by the proposal/attention terminal FKs, plus
   checks, partial/natural unique indexes, restrictive/deferrable relations,
   no cascades, and the strict Companion UI variants. This revision exposes no
   decision command and creates no DecisionRecord row by itself.
2. The decision-effect compatibility revision runs after the aggregate
   revision. It adds the narrow FT-012 DecisionRecord Task source extension,
   enables the DecisionRecord Bus domain-ref constraints, makes domain-adapter
   authorization scope nullable without weakening actor-originated validation,
   and advances every affected exact-head assertion.

Each FT-013 migration-owning task advances every exact-head regression that
exists after its dependencies, including
`tests/backend/safety_gate/test_migration_models.py` and
`tests/backend/task_follow_up/test_migration_models.py`, as well as the older
Access/Admin, Photo Intake, Plant Operations, Agent Chat, and Foundation head
assertions. A migration task may not leave any of those tests pinned to its
predecessor revision or treat the update as out of scope.

Planning does not hardcode today's FT-008 head. Downgrades remove only the
owning revision's extensions in reverse dependency order and never rewrite
retained earlier rows.

## Stable domain failures

- `COMPANION_COMMAND_FORBIDDEN`: current governance operation authority absent.
- `COMPANION_PLANT_NOT_ACTIVE`: Plant is archived/non-operative.
- `COMPANION_ISSUE_NOT_OPEN`: issue target cannot accept a run/decision.
- `COMPANION_PROPOSAL_NOT_CURRENT`: proposal/attention is stale, terminal, or superseded.
- `COMPANION_VERSION_CONFLICT`: expected version, request fingerprint, sequence,
  focus, or uniqueness conflict.
- `COMPANION_EFFECT_INVALID`: effect/classification/task-kind mismatch or
  forbidden effect.
- `COMPANION_READ_INCONSISTENT`: authoritative rows violate the closed derived
  attention/proposal/DecisionRecord/conclusion matrix; no projection fallback
  is used.
- `COMPANION_AUDIT_FAILED`: required Timeline append failed; DB mutation rolled back.
- `COMPANION_PERSISTENCE_FAILED`: authoritative transaction could not commit.

The nested canonical `governance_decision` ordinary-task seam translates its
complete reachable failure union before the Companion HTTP boundary:

| Task failure | Companion failure |
|---|---|
| `TASK_COMMAND_FORBIDDEN` | `COMPANION_COMMAND_FORBIDDEN` |
| `TASK_PLANT_NOT_ACTIVE` | `COMPANION_PLANT_NOT_ACTIVE` |
| `TASK_VERSION_CONFLICT` | `COMPANION_VERSION_CONFLICT` |
| `TASK_SOURCE_INVALID` | `COMPANION_READ_INCONSISTENT` |
| `TASK_AUDIT_FAILED` | `COMPANION_AUDIT_FAILED` |
| `TASK_PERSISTENCE_FAILED` | `COMPANION_PERSISTENCE_FAILED` |

`TASK_REQUEST_INVALID`, `TASK_SCOPE_NOT_FOUND`, `TASK_INVALID_TRANSITION`, and
`TASK_EVIDENCE_REQUIRED` belong to other/public Task command branches and MUST
NOT be emitted by the strict internal governance branch. Receiving one is an
internal contract violation, not a new product error, and maps to
`COMPANION_INTERNAL_ERROR` with the whole decision UoW rolled back.

Failures expose no protected existence details, raw provider/proposal content,
auth material, or internal exception.

## Verification

- Migration/model tests inspect native UUID parity, restrictive/deferrable FKs,
  exact enums/check matrices, partial uniqueness, the ordered aggregate then
  decision-effect heads, Task source compatibility, nullable domain Bus scope,
  and actual migration-head order.
- PostgreSQL tests prove IssueStack read/write and exact
  `(status_rank,created_at,issue_id)` ordering/cursor continuation, one focus,
  exact attention/proposal/DecisionRecord detail ordering, proposal sequence,
  active-attention reuse, supersede, same-run retry/conflict, distinct-run
  serialized supersede/refocus, valid focused/unfocused open conclusion reads,
  keep-open decision focus transfer, parent locks, archive race, and retained
  closed history.
- Decision tests prove Boss/granted Engineer allow, Consultant/missing grant
  deny, exact effect matrix, pending-v1 to flushed-approved-v2 same-UoW Task
  eligibility, committed duplicate/wrong-phase rejection, all reachable nested
  Task failure translations, full rollback on Task/projection/audit failure,
  and no `action`, Plant-state, Safety, device, or failed-decision authority.
- Projection/context tests prove one strict UI row per record identity, proposal
  state update idempotency, only valid approved DecisionRecord Bus refs,
  exact `ApprovedGovernanceSummaryV1` reconstruction/omission, exact ref/
  source-ref grammar, the complete focused/unfocused CompanionConclusion
  nullability matrix, and zero raw
  proposal/rationale/chat leakage.
- Classification-consumer tests prove only a matching Companion hold may call
  proposal persistence; safe-information/task classifications create no
  ordinary FT-008/FT-012 effect, held physical/blocked/mismatch/failure creates
  no governance or ordinary row, and retry/restore/reconciliation has no replay
  path.
