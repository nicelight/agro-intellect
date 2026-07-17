---
description: Protected HTTP reads and commands for human approvals, tasks, completion, and follow-up outcomes.
status: active
type: api_contract
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/domains/task-approval-outcomes.md
  - .memory-bank/states/task-follow-up-lifecycle.md
---
# Task And Approval HTTP

## Scope

Defines the protected FastAPI/Pydantic-style read and mutation boundary for
FT-012 Approval, Task, and Outcome records. Internal ordinary-task creation
from MessageEnvelope/classification and post-commit Approval materialization
are not public HTTP endpoints.

## Out of scope

- raw provider/model APIs, Safety classification, a public agent invocation
  endpoint, frontend components, device commands, schedulers, and reminders;
- arbitrary task creation, caller-selected action kinds, editable task text,
  approval expiry extension, or Plant-state mutation.

## Common rules

- Every route resolves current ActorContext before service logic and returns
  `Cache-Control: no-store`.
- Path ids are lowercase canonical UUID strings. Unknown fields are rejected.
- Plant scope is loaded from PostgreSQL and compared with the current Farm and
  permission resolver; request bodies cannot supply Farm, Plant, actor,
  permission, evidence freshness, task kind, source text, timestamps, or audit
  refs unless explicitly listed below.
- Boss and a granted Engineer may read and mutate tasks for an active Plant.
  Approval additionally requires current `approve_action`; Engineer needs the
  current active grant flag. Consultant may read only through its authorized
  read surface and cannot invoke any mutation.
- Archived Plant may be read only through an applicable retained-history
  projection. The operational routes below never advance an archived record.
- Responses contain safe ids/attribution only; no session/auth provenance,
  candidate/provider payload, raw exception, hidden reasoning, or credential.

## Read routes

### `GET /api/plants/{plant_id}/tasks`

Query parameters:

- optional `status=open|completed`;
- optional `kind=check|measurement|action|follow_up`;
- `limit`, integer 1..100, default 50.

Returns `200 TaskListV1` with exactly:

- `schema_version=1`;
- `items`: `TaskViewV1` values ordered by
  `(created_at DESC, task_id DESC)`.

`TaskViewV1` contains `task_id`, `kind`, `status`, literal `display_text`,
`source_type`, ordered `source_refs`, nullable `due_at`, `created_at`, nullable
`completed_at`, `created_by`, nullable `completed_by`, nullable
`parent_action_task_id`, and nullable `outcome` for a follow-up. It exposes no
request fingerprint or internal authorization snapshot.

`created_by|completed_by` is the strict safe object
`{account_id,membership_id,role_preset,agent_id}`; `agent_id` is nullable and
all human fields are non-null. `OutcomeViewV1` is exactly
`{outcome_id,follow_up_task_id,value,evidence_refs,recorded_at,recorded_by}`,
where `recorded_by` is `{account_id,membership_id,role_preset}`.

### `GET /api/plants/{plant_id}/approvals`

Query parameters:

- optional `status=pending|approved|rejected`;
- `limit`, integer 1..100, default 50.

Returns `200 ApprovalListV1` with `schema_version=1` and items ordered by
`(created_at DESC, approval_id DESC)`. `ApprovalViewV1` contains
`approval_id`, `safety_decision_id`,
`action_kind`, `status`, `record_version`, `valid_until`, derived
`is_expired`, ordered source refs, `created_at`, nullable `decided_at`, and
nullable `decided_by`. `decided_by` is exactly
`{account_id,membership_id,role_preset,permission_source,grant_id}` with
`grant_id` present only for `plant_access_grant`. `is_expired` is computed at
response time and never stored.

Read routes never materialize, transition, or repair operational records.

## Human approval command

### `POST /api/plants/{plant_id}/safety-decisions/{safety_decision_id}/approval`

The strict body `ApprovalDecisionRequestV1` contains exactly:

- `schema_version=1`;
- `request_id`: UUIDv4 command identity;
- `expected_version`: positive integer;
- `decision`: `approved|rejected`.

The path supplies `plant_id` and `safety_decision_id`; they are included in the
server canonical fingerprint and are not duplicated in the body. The service
may idempotently materialize a missing eligible Approval, then performs the
current authority, active-Plant, immutable-decision, version, expiry, and
pH/EC freshness checks from the canonical lifecycle.

Success returns `200 ApprovalDecisionResultV1` containing exactly:

- `schema_version=1`;
- `approval`: `ApprovalViewV1`;
- nullable `action_task`: `TaskViewV1`, present only for `approved`;
- `result=created|duplicate`.

Approval and action Task are one PostgreSQL transaction. This endpoint never
accepts or returns a target value, quantity, dosage, schedule, device command,
or execution result.

## Task completion command

### `POST /api/plants/{plant_id}/tasks/{task_id}/complete`

The strict body `CompleteTaskRequestV1` contains exactly
`{schema_version=1,request_id}`. The server fingerprint also includes the path
Task id.

Success returns `200 CompleteTaskResultV1` containing:

- `schema_version=1`;
- completed `task: TaskViewV1`;
- nullable `follow_up_task: TaskViewV1`, present exactly when an `action`
  completion creates or returns its unique automatic follow-up;
- `result=created|duplicate`.

The route rejects `kind=follow_up`; only the Outcome route can complete it.
It performs no physical action and treats completion only as a human record.

## Follow-up outcome command

### `POST /api/plants/{plant_id}/tasks/{task_id}/outcome`

The strict body `RecordOutcomeRequestV1` contains exactly:

- `schema_version=1`;
- `request_id`: UUIDv4 command identity;
- `value`: `improved|worsened|unchanged|no_data`;
- `evidence_refs`: zero through four ordered unique safe refs.

`task_id` must identify an open `follow_up` in the path Plant. Non-`no_data`
requires at least one evidence ref; `no_data` may use an empty array. The
service reloads every ref from its owning PostgreSQL authority.

Success returns `200 RecordOutcomeResultV1` containing exactly:

- `schema_version=1`;
- completed `task: TaskViewV1`;
- `outcome: OutcomeViewV1`;
- `result=created|duplicate`.

Outcome creation and follow-up completion are one PostgreSQL transaction. The
response does not claim confirmed Plant-state promotion.

## Internal ordinary-task command

The non-HTTP `create_ordinary_task` command is the only arbitrary-looking task
creation path. It accepts service-side current ActorContext, a validated
pending MessageEnvelope, its persisted matching Safety classification, and a
request id equal to the immutable envelope `run_id`. It has no public JSON body
and creates only the exact classified `check|measurement|follow_up` kind.
`action`, mismatched kind/scope, unpersisted classification,
unauthorized/archived Plant, and conflicting message reuse fail closed.

## Error mapping

All errors use the global safe envelope with request correlation:

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `TASK_REQUEST_INVALID` | cross-field request violation not handled by schema validation |
| 404 | `TASK_SCOPE_NOT_FOUND` | Plant/record is missing or current actor is unauthorized; no existence leak |
| 409 | `TASK_PLANT_NOT_ACTIVE` | an otherwise authorized operational scope is archived |
| 409 | `APPROVAL_NOT_CURRENT` | approval expired or current Safety evidence/decision is no longer eligible |
| 409 | `TASK_VERSION_CONFLICT` | version, terminal state, request id/fingerprint, or natural-key content conflicts |
| 409 | `TASK_INVALID_TRANSITION` | Task/Approval kind or state does not accept the requested command |
| 422 | `TASK_EVIDENCE_REQUIRED` | Outcome evidence refs violate the closed policy |
| 500 | `TASK_AUDIT_FAILED` | required Timeline append failed and runtime mutation was rolled back |
| 500 | `TASK_PERSISTENCE_FAILED` | authoritative mutation could not commit |

FastAPI/Pydantic validation remains `422`; protected context is never echoed.
Identical retry is a success result, not `409`.

## Compatibility and verification

- Generated OpenAPI must expose the exact paths, strict bodies, enums, and
  response unions without an arbitrary metadata field.
- API tests prove ActorContext-before-business-logic, no-store, no-existence
  leak, Boss/Engineer/Consultant matrix, inclusive expiry boundary, conflicts,
  archive freeze, response redaction, and identical retry behavior.
- Integration tests prove HTTP results match the authoritative PostgreSQL rows
  and Timeline refs and never perform device or Plant-state effects.

## Related specs

- [.memory-bank/contracts/api-guidelines.md](api-guidelines.md)
- [.memory-bank/contracts/access/actor-context.md](access/actor-context.md)
- [.memory-bank/domains/task-approval-outcomes.md](../domains/task-approval-outcomes.md)
- [.memory-bank/states/task-follow-up-lifecycle.md](../states/task-follow-up-lifecycle.md)
