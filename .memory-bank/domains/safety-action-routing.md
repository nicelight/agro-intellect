---
description: PostgreSQL classification and Safety action-decision authority through pending human approval.
status: active
type: data_spec
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/features/FT-011-safety-gate-physical-action-routing.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Safety Action Routing Data

## Scope

This specification defines PostgreSQL authority for immutable project-owned
classifications and physical-action Safety decisions through
`pending_human_approval`. It fixes action support, `approval_input=2h`
evaluation, proposal expiry, transaction/idempotency rules, and the derived
non-imperative UI status projection.

## Out of scope

- Human approve/reject decisions, approval rows, `action_task`, completion,
  follow-up, and outcomes; FT-012 owns every transition after
  `pending_human_approval`.
- Raw candidate/model text storage, a new public HTTP endpoint, dedicated
  Timeline events, device execution, target pH/EC, quantities, dosage formulas,
  nutrient recipes, or schedules.

## Related specs

- [.memory-bank/contracts/safety-gate-runtime.md](../contracts/safety-gate-runtime.md):
  strict model candidate and backend mapping.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md):
  shared classification result and authority phases.
- [.memory-bank/domains/plant-operations.md](plant-operations.md): current
  manual-measurement authority and `approval_input=2h` semantics.
- [.memory-bank/contracts/access/actor-context.md](../contracts/access/actor-context.md):
  current read/approval authority.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): presentation-only
  Safety status payload.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md):
  active-Plant transactional guard and no restore replay.

## `safety_classifications`

One immutable row is keyed by the pending message:

- `message_id`: native UUID primary key; it equals the
  `SafetyClassificationResultV1.message_id` and has no FK because
  MessageEnvelope remains a transient handoff;
- `farm_id`, `plant_id`: native UUID FKs with `ON DELETE RESTRICT`;
- `origin_agent_id`: lowercase canonical agent id;
- `classifier_version`: fixed `safety_gate_v1`;
- `classification`, nullable `safe_task_kind`, and `reason_code`: the exact
  shared result values;
- nullable `physical_action_kind`: one exact ten-kind union from the Safety
  Gate Runtime contract, non-null only for `physical_action`;
- `provider_status`: `completed | not_configured | failed | invalid`;
- nullable safe `model_ref=provider_profile:model_id`;
- `input_sha256`, `result_sha256`: lowercase 64-character digests;
- `created_at`: timezone-aware UTC server timestamp.

The strict shared classification matrix is enforced in both model validation
and database constraints. `physical_action_kind` is required only for
`physical_action`; every other class stores null. A provider status other than
`completed` requires `blocked_uncertain`, null action/task kind, and
`classification_uncertain`.

`input_sha256` hashes the canonical compact UTF-8 JSON serialization of the
complete validated MessageEnvelope (`sort_keys=true`, no insignificant
whitespace, original Unicode). `result_sha256` hashes the same serialization
of the final shared result plus nullable physical-action kind and provider
status. Digests detect conflicting reuse; neither digest replaces validation
or authorization.

The first committed row for `message_id` is immutable. An identical input and
result digest is an idempotent duplicate. Any mismatch returns
`SAFETY_CLASSIFICATION_CONFLICT`, creates no write/projection/route, and leaves
the first row unchanged. There is no update or delete service path in MVP.

## `safety_action_decisions`

Exactly one immutable decision may exist for a persisted `physical_action`
classification:

- `decision_id`: application-generated native UUIDv4 primary key;
- `classification_message_id`: unique native UUID FK to
  `safety_classifications.message_id`, `ON DELETE RESTRICT`;
- `farm_id`, `plant_id`: native UUID FKs with `ON DELETE RESTRICT`, equal to
  the classification scope;
- safe actor attribution: `actor_account_id`, `actor_membership_id`,
  `actor_role_preset`, `permission_source`, and nullable `grant_id`;
- `action_kind`: the exact persisted physical-action kind;
- `safety_status`:
  `safety_blocked | needs_fresh_evidence | pending_human_approval`;
- `reason_code`:
  `unsupported_action | approval_authority_missing |
  approval_input_missing_or_stale | ready_for_human_approval`;
- nullable `ph_measurement_id`, `ec_measurement_id`: native UUID FKs to the
  selected authoritative measurement rows, `ON DELETE RESTRICT`;
- nullable `ph_status`, `ec_status`: `fresh | stale | missing`;
- nullable `ph_measured_at`, `ec_measured_at`;
- nullable `expires_at`;
- `evaluated_at`, `created_at`: timezone-aware UTC server timestamps using the
  same evaluation instant;
- `summary_text`: one exact project-owned non-imperative phrase below.

The row never contains MessageEnvelope candidate text, model output, target
values, quantities, approval fields, task ids, executable commands, or an
arbitrary metadata object.

## Deterministic Safety evaluation

The evaluator processes a persisted physical-action classification in this
exact order inside one current-state decision transaction:

1. Reload the classification, Farm/Plant, session/account/membership/grant,
   and require current `normal_read` authority plus `Plant.status=active`.
2. If `action_kind` is one of
   `pump_command|light_command|dosing_command|pruning|transplanting|
   root_trimming|other_physical_action`, persist
   `safety_blocked/unsupported_action` without evaluating pH/EC.
3. For `ph_adjustment|ec_adjustment|solution_change`, require current
   `approve_action` authority. Boss is allowed; Engineer requires the current
   active grant flag; Consultant is denied. Denial persists
   `safety_blocked/approval_authority_missing` without evaluating pH/EC.
4. Select latest authoritative non-null pH and EC measurement rows through the
   Plant Operations ordering rules and compute both at the one
   `evaluated_at` instant using purpose `approval_input` and window 2 hours.
5. If either value is missing, stale, or future-dated, persist
   `needs_fresh_evidence/approval_input_missing_or_stale`.
6. If both are fresh, persist
   `pending_human_approval/ready_for_human_approval` with
   `expires_at=min(ph_measured_at+2h, ec_measured_at+2h)`.

The canonical closed freshness interval remains
`evaluated_at-2h <= measured_at <= evaluated_at`; therefore an exact-boundary
measurement is fresh and may yield `expires_at=evaluated_at`. FT-012 must
re-resolve authority, active Plant, the immutable pending decision, and current
freshness at approval time; this snapshot is never reusable authorization.

Cached freshness booleans, analysis freshness (`24h`), Timeline, UI Feed,
photo manifests, agent/model text, and caller claims are never evidence
authority. Both pH and EC are mandatory for all three supported kinds.

## Project-owned summaries

The stored/UI summary is selected only by backend status and action kind:

- pending `ph_adjustment`:
  `Предложена ручная корректировка pH. Требуется решение уполномоченного пользователя.`
- pending `ec_adjustment`:
  `Предложена ручная корректировка EC питательного раствора. Требуется решение уполномоченного пользователя.`
- pending `solution_change`:
  `Предложена ручная замена питательного раствора. Требуется решение уполномоченного пользователя.`
- missing/stale evidence:
  `Перед предложением действия нужны свежие измерения pH и EC.`
- missing approval authority:
  `Действие заблокировано: у текущего пользователя нет права подтверждения.`
- unsupported action:
  `Действие не поддерживается безопасным процессом MVP.`

The phrases are literal non-imperative presentation text. They do not copy or
summarize the candidate with a model and cannot become agent context,
instructions, an approval, or an action command.

## Transaction, projection, and replay

- Decision insertion reloads the active Plant and current actor permission in
  the same transaction. It also reads the selected pH/EC rows in that
  transaction for supported/authorized kinds.
- The decision row and exactly one `safety_status` UIFeedEvent commit atomically
  or neither does. `ui_event_id=decision_id`; the classification message key
  and decision id make an identical retry idempotent, while content conflict
  fails closed.
- UI source refs are ordered and capped at four:
  `message_envelope:<message_id>`,
  `safety_classification:<message_id>`, then present pH and EC
  `manual_measurement:<measurement_id>` refs.
- The UI event is presentation only, visible to `boss|engineer`, and keeps
  both agent-consumability flags false. Backend feed authorization still
  applies per Plant.
- Archive before commit produces no decision or projection. Archive preserves
  existing rows unchanged and makes them retained/non-operative. Restore does
  not make FT-011 retry, refresh, promote, or reproject a prior decision. A new
  FT-011 classification/Safety evaluation requires a new Agent Runtime request
  and message id. A separate explicit FT-012 approve/reject command may
  reference the retained decision only when it is still pending and unexpired
  and the command revalidates current ActorContext, active Plant, approval
  authority, immutable decision, and selected pH/EC freshness.
- A safety decision has no update/delete/execute path in FT-011. FT-012 may
  reference only a current `pending_human_approval` decision and owns every
  later record/state.
- No dedicated Timeline event is written; these PostgreSQL rows are the durable
  FT-011 trace.

## Persistence errors

- `SAFETY_DECISION_CONFLICT`: same classification has different canonical
  decision content; no mutation or projection.
- `SAFETY_DECISION_GUARD_DENIED`: current authorization or active-Plant guard
  fails before the decision write; no row/projection and no replay.
- `SAFETY_DECISION_EVIDENCE_INVALID`: selected measurement scope/type/value is
  inconsistent with Plant Operations authority; fail closed with no partial
  write.
- `SAFETY_DECISION_PERSISTENCE_FAILED`: decision/UI transaction fails; neither
  row is authoritative.

Errors expose no candidate text, provider payload, credentials, auth material,
or raw exception.

## Verification

Migration/model tests MUST prove native UUID parity, restrictive FKs, exact
enums/matrix constraints, classification and decision uniqueness, immutable
first-write-wins behavior, and no raw candidate columns. PostgreSQL service
tests MUST prove all ten action kinds, manual nutrient addition as
`ec_adjustment`, device dosing as unsupported, Boss/Engineer/Consultant rules,
independent pH/EC 2-hour boundaries, missing/stale/future evidence, exact-boundary
expiry, atomic decision/UI writes, duplicate/conflict concurrency, archive and
grant races, no restore replay, exact non-imperative payloads, and zero
approval/task/actuation effect.
