---
description: Protected Companion IssueStack, proposal decision, close, and explicit invocation HTTP contract.
status: active
type: api_contract
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/domains/companion-governance.md
  - .memory-bank/contracts/companion-runtime.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
---
# Companion Governance HTTP

## Scope

Defines protected Plant-scoped IssueStack reads, issue detail, explicit
model-backed Companion invocation, current-proposal decision, and resolved
issue close commands.

## Out of scope

- Farm-level governance, raw chat/message submission, generic prompts, provider
  selection, frontend layout, Safety approval, Task completion, or automated
  model triggers;
- a public endpoint for focus, HumanAttention acknowledgement, proposal
  supersede, CompanionConclusion confirmation, or arbitrary Task creation.

All routes resolve ActorContext before business logic and set
`Cache-Control: no-store` on success and error.

## Authorization

- IssueStack/detail reads require current authorized Plant read. Active and
  retained archived history use their canonical permission modes.
- Explicit run, proposal decision, and close require current active membership,
  `Plant.status=active`, `can_operate=true`, and role `boss|engineer`.
- Engineer authority requires the current active Plant grant. Consultant,
  missing/revoked grant, disabled identity, and unauthorized Plant fail without
  existence leakage.
- No route reads `plant_approve_actions` or adds a governance permission.

## Common serialization and refs

Every request and response schema is strict: every listed field is present,
unknown fields are rejected, and nullable fields serialize as JSON `null`
rather than being omitted. UUID values use lowercase canonical strings and
timestamps use timezone-aware UTC RFC 3339 strings.

All `*_ref` members are strings, not ref objects. The exact FT-013 grammar is
`companion_issue:<uuid>`, `companion_attention:<uuid>`,
`companion_proposal:<uuid>`, and `decision_record:<uuid>`. Shared refs used by
this API are `plant:<uuid>`, `daily_checkin:<uuid>`,
`manual_measurement:<uuid>`, `message_envelope:<uuid>`,
  `safety_classification:<uuid>`, and `task:<uuid>`. Alias kinds are invalid.
Every public `*_event_ref` is the stored event ref's exact `timeline_ref`
string in `timeline.jsonl#<timeline_event_id>` form; the full internal
event-ref object is not serialized. Safe ref arrays preserve the exact
data-spec order and reject duplicates or caller-supplied additions.

## `GET /api/plants/{plant_id}/companion/issues`

Strict query parameters:

- `status`: optional `open|resolved|closed`;
- `cursor`: optional canonical opaque continuation;
- `limit`: optional integer `1..100`, default `50`.

Unknown/repeated query parameters fail validation. Items use the data-spec
order `(status_rank ASC,created_at ASC,issue_id ASC)`, with `open=0`,
`resolved=1`, and `closed=2`. Cursor is unpadded base64url of canonical compact
UTF-8 JSON containing exactly
`{"v":1,"status_rank":0,"created_at":"<UTC>","issue_id":"<uuid>"}`;
`status_rank` is an integer `0|1|2`, canonical re-encode identity is required,
and a cursor used with a `status` filter must carry that status's exact rank.

`200 IssueStackPageV1` contains exactly:

- `schema_version=1`;
- `plant_id`;
- nullable `focused_issue_ref`;
- `items`: zero through `limit` strict `IssueSummaryV1` objects;
- nullable `next_cursor`.

`IssueSummaryV1` contains exactly `issue_id`,
`issue_ref=companion_issue:<issue_id>`, `status`, `is_focused`,
`summary_text`, `record_version`, `created_at`, nullable `resolved_at`, and
nullable `closed_at`. The state matrix is exact: `open` has both terminal
timestamps null; `resolved` has non-null `resolved_at` and null `closed_at`;
`closed` has both non-null. Only `open` may be focused.

Archived retained-history reads return retained rows but cannot expose a run,
decision, close, Task, or agent-context capability.

## `GET /api/plants/{plant_id}/companion/issues/{issue_id}`

`200 CompanionIssueDetailV1` contains exactly:

- `schema_version=1`;
- `issue`: `IssueSummaryV1`;
- nullable `attention`: exact `CompanionAttentionViewV1` selected by the data
  spec's active-else-latest rule;
- ordered retained `proposals`: strict `CompanionProposalViewV1` array in
  `(proposal_sequence ASC,proposal_id ASC)` order;
- ordered retained `decision_records`: strict `DecisionRecordViewV1` array in
  `(decided_at ASC,decision_record_id ASC)` order;
- derived `conclusion`: exact `CompanionConclusionV1` from the data spec.

`CompanionAttentionViewV1` contains exactly:

- `attention_id`, `attention_ref=companion_attention:<attention_id>`, and
  `issue_ref`;
- `attention_sequence`, `status=active|satisfied`, `summary_text`,
  `current_proposal_ref`, and `record_version`;
- `created_at`, nullable `satisfied_at`, and nullable
  `satisfied_by_decision_record_ref`.

`current_proposal_ref` is always non-null. For `active`, both satisfaction
fields are null; for `satisfied`, both are non-null. `attention` is null only
when the issue has no attention rows.

`CompanionProposalViewV1` contains exactly:

- `proposal_id`, `proposal_ref`, `issue_ref`, `attention_ref`, and
  `proposal_sequence`;
- `state=pending|approved|rejected|superseded` and `record_version`;
- `proposal_summary`, `proposal_text`, nullable `rationale_text`,
  `proposed_effect`, nullable `task_display_text`, and
  `suggested_resolution`;
- ordered `source_refs` in the exact data-spec composition;
- `created_at`, nullable `terminal_at`, nullable `decision_record_ref`,
  `created_event_ref`, and nullable `superseded_event_ref`.

`pending` has version 1 and all terminal/decision/supersede fields null.
`approved|rejected` have version 2, non-null terminal time and DecisionRecord
ref, and null supersede ref. `superseded` has version 2, non-null terminal time
and supersede ref, and null DecisionRecord ref. `task_display_text` is non-null
exactly for `check|measurement|follow_up`.

`DecisionRecordViewV1` contains exactly:

- `decision_record_id`, `decision_record_ref`, `issue_ref`, `attention_ref`,
  and `proposal_ref`;
- `decision=approved|rejected`, `decision_summary`,
  `allowed_workflow_effect`, and `issue_resolution`;
- nullable `workflow_effect_ref`, present exactly as `task:<uuid>` for an
  approved `check|measurement|follow_up` effect and null otherwise;
- `decider_account_id`, `decider_membership_id`,
  `decider_role_preset=boss|engineer`, `decider_permission_source`, and
  nullable `decider_grant_id`;
- `decided_at`, ordered `source_refs`, `decision_event_ref`, and
  `safety_gate_authority=not_granted`.

Approval exposes the exact persisted proposal effect. Rejection exposes
`allowed_workflow_effect=none` and a null workflow ref.

`CompanionConclusionV1` contains exactly `schema_version=1`, `issue_id`,
`issue_status`, `is_focused`, `conclusion_status`, nullable
`current_attention_ref`, nullable `current_proposal_ref`, nullable
`latest_decision_record_ref`, nullable `decision`, nullable
`decision_summary`, nullable `allowed_workflow_effect`, nullable `decided_at`,
and `safety_gate_authority=not_granted`. Its complete discriminant/nullability
matrix and deterministic latest DecisionRecord selection are owned by the data
spec. Both `awaiting_human` and open `decided` accept
`is_focused=true|false` under that matrix; focus transfer alone never makes a
retained open issue unreadable. The HTTP serializer may not infer a looser
combination from projections.

This authorized human read may return persisted proposal/rationale text. Those
fields remain JSON text data, are never returned by the feed endpoint, and must
not be copied to Bus, model context, Timeline, or active HTML/Markdown.

## `POST /api/plants/{plant_id}/companion/runs`

This is the only MVP model trigger. Feed reads, page refresh, domain events,
Task completion, startup, and reconciliation never call it.

Strict `CompanionRunRequestV1` contains exactly:

- `schema_version=1`;
- `request_id`: UUIDv4 and Agent Runtime `run_id`;
- nullable `issue_id`;
- nullable `expected_issue_version`.

`issue_id` and `expected_issue_version` are either both null (create one new
issue) or both present (target one existing open issue). Callers cannot submit
issue/proposal text, refs, prompt, instructions, effect, resolution, model,
provider, output schema, role, grant, or authorization data.

`200 CompanionRunResponseV1` contains exactly:

- `schema_version=1`, `run_id`;
- `route_status=proposal_created|proposal_duplicate|silent|not_governable`;
- nullable `issue_ref`, `attention_ref`, `proposal_ref`,
  `classification_ref` according to the runtime contract;
- nullable safe `model_ref`, present only when this response retains the
  current call's runtime outcome and null for every `proposal_duplicate`;
- nullable `reason_code=no_material_output|insufficient_evidence|
  physical_action_not_allowed|classification_uncertain|
  classification_mismatch` from the closed runtime result matrix.

The exact nullability matrix is:

| `route_status` | Governance refs | Classification/model refs | `reason_code` |
|---|---|---|---|
| `proposal_created` | issue, attention, and proposal refs non-null | classification and model refs non-null | null |
| `proposal_duplicate` | issue, attention, and proposal refs non-null | classification ref non-null; model ref null | null |
| `silent` | all governance refs null | classification ref null; model ref non-null | `no_material_output|insufficient_evidence` |
| `not_governable` | all governance refs null | classification and model refs non-null | one exact physical/uncertain/mismatch reason |

No other field combination is valid. Internal `failed` results never serialize
as this 200 response; they use the total error mapping below.

`silent` and `not_governable` are successful non-mutating outcomes, not
provider failures. Response never includes provider output, prompt, hidden
reasoning, candidate/proposal text, ActorContext, or credentials.

An identical committed retry returns `proposal_duplicate` by re-reading the
proposal and matching persisted classification. It returns their issue,
attention, proposal, and classification refs, makes no provider call, has
`model_ref=null`, and does not reconstruct a common Agent Runtime outcome or
transient MessageEnvelope. A losing concurrent attempt also discards its
current-call runtime outcome and returns the same duplicate shape; sanitized
runtime audit remains its provider-call evidence. A separate persisted runtime
receipt is neither required nor permitted for this branch.

## `POST /api/plants/{plant_id}/companion/proposals/{proposal_id}/decision`

Strict `CompanionDecisionRequestV1` contains exactly:

- `schema_version=1`;
- `request_id`: UUIDv4;
- `expected_version`: literal `1` for the current pending proposal;
- `decision`: `approved|rejected`;
- `decision_summary`: normalized compact text `1..500` code points;
- `issue_resolution`: `keep_open|resolved`.

The path supplies Plant/proposal identity. The service loads the issue,
attention, model proposal, persisted classification, and effect; caller cannot
replace the proposed effect or Task text. Approval adopts the proposal effect;
rejection forces `none`.

`200 CompanionDecisionResultV1` contains exactly:

- `schema_version=1`;
- `result=created|duplicate`;
- `decision_record`: strict DecisionRecord view;
- nullable `workflow_task_ref`, present only for
  `check|measurement|follow_up`;
- `issue`: updated `IssueSummaryV1`;
- `conclusion`: derived `CompanionConclusionV1`.

`workflow_task_ref` equals `decision_record.workflow_effect_ref` item for item;
both are null for rejection and `discussion_only|none`. The conclusion is
derived after the same committed transaction and must match the returned issue
and DecisionRecord. No response grants Safety authority or returns an
action/device field.

## `POST /api/plants/{plant_id}/companion/issues/{issue_id}/close`

Strict `CompanionIssueCloseRequestV1` contains exactly:

- `schema_version=1`;
- `request_id`: UUIDv4;
- `expected_version`: positive integer.

Only a current `resolved` issue may close. `200 CompanionIssueCloseResultV1`
contains exactly `schema_version=1`, `result=closed|duplicate`, and updated
`IssueSummaryV1`. No reopen endpoint exists.

## Error mapping

All errors use the global safe envelope with request correlation:

| HTTP | Public code | Internal source/condition |
|---:|---|---|
| 404 | `COMPANION_SCOPE_NOT_FOUND` | `COMPANION_COMMAND_FORBIDDEN`, nested `TASK_COMMAND_FORBIDDEN`, `AGENT_CONTEXT_DENIED/context_denied`, `AGENT_PUBLICATION_BLOCKED`, or `SAFETY_CLASSIFICATION_GUARD_DENIED` when current Plant/issue/proposal scope is missing or unauthorized; no existence leak |
| 409 | `COMPANION_PLANT_NOT_ACTIVE` | `COMPANION_PLANT_NOT_ACTIVE`, nested `TASK_PLANT_NOT_ACTIVE`, or a current runtime/classifier guard that specifically resolves an otherwise authorized archived Plant |
| 409 | `COMPANION_ISSUE_NOT_OPEN` | `COMPANION_ISSUE_NOT_OPEN` for a run target, decision, or close state |
| 409 | `COMPANION_PROPOSAL_NOT_CURRENT` | `COMPANION_PROPOSAL_NOT_CURRENT` for stale, terminal, superseded, or wrong-current attention/proposal |
| 409 | `COMPANION_VERSION_CONFLICT` | `COMPANION_VERSION_CONFLICT`, nested `TASK_VERSION_CONFLICT`, or `SAFETY_CLASSIFICATION_CONFLICT`, including request/fingerprint reuse and stated concurrency/version conflicts |
| 422 | `COMPANION_EFFECT_INVALID` | `COMPANION_EFFECT_INVALID`; no decision/effect was written |
| 422 | `VALIDATION_FAILED` | FastAPI/Pydantic, malformed path/query/cursor, unknown/repeated fields, or strict cross-field validation |
| 500 | `COMPANION_RUNTIME_AUDIT_FAILED` | `AGENT_AUDIT_FAILED`; the real runtime audit failed before a usable handoff |
| 500 | `COMPANION_AUDIT_FAILED` | governance `COMPANION_AUDIT_FAILED` or nested `TASK_AUDIT_FAILED`; required governance/Task Timeline append failed and the complete decision UoW rolled back |
| 500 | `COMPANION_CLASSIFICATION_PERSISTENCE_FAILED` | `SAFETY_CLASSIFICATION_PERSISTENCE_FAILED`; no authoritative classification/proposal exists |
| 500 | `COMPANION_READ_INCONSISTENT` | `COMPANION_READ_INCONSISTENT`, nested `TASK_SOURCE_INVALID`, or `AGENT_CONTEXT_DENIED/input_contract_violation`; authoritative input/read/source rows violate the closed runtime, Task-source, approved-summary, or conclusion matrix |
| 500 | `COMPANION_PERSISTENCE_FAILED` | `COMPANION_PERSISTENCE_FAILED` or nested `TASK_PERSISTENCE_FAILED`; authoritative governance/projection/Task transaction failed |
| 500 | `COMPANION_INTERNAL_ERROR` | unexpected redacted internal failure, including impossible nested `TASK_REQUEST_INVALID|TASK_SCOPE_NOT_FOUND|TASK_INVALID_TRANSITION|TASK_EVIDENCE_REQUIRED`; no partial success may be returned |
| 502 | `COMPANION_PROVIDER_FAILED` | `AGENT_PROVIDER_FAILED` from the configured Companion provider |
| 502 | `COMPANION_OUTPUT_INVALID` | `AGENT_OUTPUT_INVALID` from strict Companion result validation |
| 503 | `COMPANION_RUNTIME_NOT_CONFIGURED` | `AGENT_RUNTIME_NOT_CONFIGURED`; Companion binding, egress, dependency, or credential unavailable before model I/O |

`SAFETY_CLASSIFIER_NOT_CONFIGURED`, `SAFETY_CLASSIFIER_PROVIDER_FAILED`, and
`SAFETY_CLASSIFIER_OUTPUT_INVALID` are not HTTP failures when their canonical
`blocked_uncertain` classification is committed: the route returns
`200 not_governable` with `reason_code=classification_uncertain`. A physical
classification similarly returns `physical_action_not_allowed`, and an exact
kind/effect mismatch returns `classification_mismatch`. If the classifier row
cannot commit or its current guard fails, the table above applies instead.

The route must retain enough typed condition information to distinguish an
authorized archived Plant from an unauthorized/missing scope; it may not map
every common guard denial to one status by string matching. Raw internal codes,
exception text, provider payloads, and protected identities are not included
in the public message.

Identical retry is a success result, not `409`. Runtime invalid/guard-denied
branches use the closed Companion runtime mapping without exposing raw output.
The six named nested Task failures are the complete reachable
`governance_decision` union. The four impossible Task codes above are contract
violations rather than additional public Companion states; tests fail the
internal branch and assert the redacted 500 fallback plus full rollback.

## Compatibility and verification

- Generated OpenAPI exposes exact paths, strict request/response unions,
  all view fields, ref grammars, nullability matrices, enums, bounds, and
  errors without arbitrary metadata.
- API tests cover Boss, granted Engineer, Consultant, revoked/missing grant,
  archive retained reads versus denied commands, no-store, no-existence leak,
  exact status-rank ordering/cursor continuation, cursor/filter rank mismatch,
  canonicality, and redaction.
- Decision tests prove caller cannot select effect/Task kind, unknown or
  mismatched persisted effect rejects atomically, and every response keeps
  `safety_gate_authority=not_granted`.
- Detail/read tests prove active-else-latest attention selection, ascending
  proposal/DecisionRecord arrays, deterministic latest DecisionRecord,
  complete CompanionConclusion groups, strict event/source refs, and
  `COMPANION_READ_INCONSISTENT` without projection fallback.
- Invocation tests prove GET/refresh/events never call a model, only the
  explicit POST reaches the Companion runtime, and an early committed
  duplicate returns persisted refs with null `model_ref` and zero provider or
  MessageEnvelope reconstruction.
- Error tests exercise every common runtime, classification, and governance
  source branch in the total mapping, including separate runtime-audit versus
  governance-audit codes and successful persisted classifier uncertainty.
- Decision-route error tests inject all six reachable nested Task failures plus
  the impossible-code fallback, proving exact translation and complete
  DecisionRecord/proposal/attention/issue/Task/projection rollback.
