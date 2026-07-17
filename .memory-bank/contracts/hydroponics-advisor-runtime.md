---
description: Authorized Hydroponics Advisor input, missing-data policy, structured result, and pending handoff contract.
status: active
type: interface_contract
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/features/FT-010-hydroponics-advisor-missing-data-policy.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/states/safety-action-lifecycle.md
---
# Hydroponics Advisor Runtime

## Scope

This contract defines one invocation of the canonical
`hydroponics_advisor` product agent over current authorized PostgreSQL Plant
evidence. It owns the strict advisor request/result shapes, version-1 critical
pH/EC policy, project-owned missing-data wording, and mapping to the common
pending `MessageEnvelope`.

The advisor may produce cautious recommendation or hypothesis candidate text
only when both critical measurements are fresh for analysis. When either pH or
EC is missing or stale, the only accepted non-silent result is a low-risk
measurement request for exactly that project-computed set.

## Out of scope

- Safety classification, Safety Gate decision, physical-action approval,
  ordinary task persistence, action-task creation, or automated actuation;
  FT-011 and FT-012 own those effects.
- Public HTTP/model endpoints, frontend rendering, daily-flow orchestration, or
  browser-visible completion; FT-016 owns first-demo composition.
- New PostgreSQL tables, provider history, prompts, raw response persistence,
  Agno memory/tools/RAG/Team, sensor ingestion, crop recipes, nutrient
  schedules, dosage formulas, or cultivar thresholds.
- Reinterpreting photo files, Timeline, UI Feed, raw chat, or model text as
  current Plant evidence.

## Related specs

- [.memory-bank/contracts/agent-runtime-adapter.md](agent-runtime-adapter.md):
  shared provider-neutral outcome, post-model guard, audit, and envelope rules.
- [.memory-bank/contracts/agent-model-provider-profiles.md](agent-model-provider-profiles.md):
  explicit provider/model binding, egress, credentials, and no fallback.
- [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
  canonical `hydroponics_advisor` identity.
- [.memory-bank/contracts/message-envelope.md](message-envelope.md): pending
  non-consumable output boundary.
- [.memory-bank/domains/plant-operations.md](../domains/plant-operations.md):
  pH/EC values and 24-hour analysis freshness.
- [.memory-bank/domains/plant-state-observations.md](../domains/plant-state-observations.md):
  classified photo-derived and Plant State records.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md):
  observation/hypothesis/confirmation authority.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md):
  project-owned classification and downstream route classes.

## Module and command boundary

Implementation lives under `backend/app/hydroponics_advisor/` and reuses the
Agent Runtime provider binding, post-model authorization guard, timeline audit,
closed outcome, and `MessageEnvelopeV1` types.

The internal `HydroponicsAdvisorCommandV1` contains exactly:

- `schema_version=1`;
- application-generated UUIDv4 `run_id`;
- timezone-aware UTC `requested_at`;
- service-side `actor_context`;
- requested UUID `plant_id`;
- `request_reason=daily_checkin|plant_state_update|manual_review`;
- `analysis_goal=general_hydroponics_review|solution_related_review|missing_data_review`.

Callers cannot submit measurements, Plant-state rows, freshness flags, source
refs, prompts, instructions, candidate output, provider/model choice, output
schema, or authorization snapshots. There is no caller text field in version
1.

## Provider request version 1

`HydroponicsAdvisorProviderRequestV1` is one strict object with exactly:

- `schema_version=1`;
- canonical project-owned `agent_definition` for
  `agent_id=hydroponics_advisor`, decisions `speak|clarify|silent`, and strict
  output schema `HydroponicsAdvisorModelResultV1` version 1;
- the command `request_reason` and `analysis_goal`;
- timezone-aware UTC `computed_at`;
- exact `analysis_freshness` value defined below;
- `records`: 1 through 4 strict records in the order below;
- `source_refs`: ordered unique refs exactly equal to the records' refs.

Unknown fields at every level are rejected. UUIDs are lowercase canonical
strings, timestamps are UTC RFC 3339 strings, and pH/EC use the canonical
scale-2/scale-3 strings from PostgreSQL.

### Record selection and order

The assembler resolves current `normal_read` authority for the same active
Plant, then selects at most four records:

1. the exact `plant` record first;
2. latest non-null pH `manual_measurement` when present;
3. latest non-null EC `manual_measurement` when present and not the same row as
   pH;
4. fill the remaining one or two slots from the latest completed
   `daily_checkin` and latest non-rejected `plant_state_record`, choosing the
   newest available contextual rows and ordering selected context oldest-to-
   newest.

This bound preserves the shared Agent Runtime audit and MessageEnvelope
1-through-4 source-ref contract. If distinct pH and EC rows consume both
measurement slots, only the newer check-in/Plant-state context is included. If
one measurement row supplies both values, both context rows may be included.

Plant, daily-check-in, and manual-measurement records reuse the exact payload
and deterministic ordering rules from `AgentInputRecordV1`. The strict
`plant_state_record` is
`{record_type=plant_state_record,source_ref,payload}` with
`source_ref=plant_state_record:<state_record_id>` and payload containing only:

- `state_record_id`, `record_kind`, `observation_key`;
- nullable `polarity`, `severity`, `assessment_kind`, and `direction`;
- `trust_status=unknown|observed|hypothesis|conflicting|confirmed`;
- `observed_at`, `recorded_at`, finite `confidence` in `[0,1]`;
- ordered non-empty safe `source_refs`.

Rejected records, summary text, confirmation actors, run/message ids,
ActorContext/session/account/membership/grant values, authorization snapshots,
UI Feed, raw chat, Timeline replay, provider history, hidden reasoning,
credentials, and local paths are forbidden.

### Analysis freshness value

`analysis_freshness` contains exactly:

- `window_hours=24`;
- `computed_at`, equal to request `computed_at`;
- `ph` and `ec`, each exactly
  `{status=fresh|stale|missing,source_ref,measured_at}`;
- `missing_or_stale`, ordered as `ph`, then `ec`, containing every non-fresh
  value exactly once.

For a missing value, `source_ref` and `measured_at` are null. For fresh or
stale, they identify the selected measurement row. Freshness is independently
derived from `measured_at` using the closed interval
`computed_at - 24h <= measured_at <= computed_at`; future-dated evidence is
stale. Cached booleans, model labels, Timeline, UI content, and agent text are
never freshness authority.

Version 1 treats both pH and EC as critical for every advisor analysis goal.
This conservative rule is the bounded MVP policy; later sensor/environment
fields require a new canonical contract version rather than silent extension.

## Model result version 1

`HydroponicsAdvisorModelResultV1` is a strict object with exactly:

- `schema_version=1`;
- `runtime_decision=speak|clarify|silent`;
- nullable `advice_kind=recommendation|hypothesis|measurement_request|clarification`;
- nullable normalized `candidate_output` from 1 through 1000 Unicode code
  points;
- nullable finite `confidence` in `[0,1]`;
- `requested_measurements`, an ordered unique subset of `ph|ec`;
- `source_refs`, an ordered unique subset of request refs;
- nullable `reason_code`.

The exact matrix is:

| Decision / kind | Candidate/confidence | Requested measurements and refs | Reason |
|---|---|---|---|
| `speak / measurement_request` | both null; adapter creates wording/confidence | measurements equal `analysis_freshness.missing_or_stale`; refs equal the deterministic policy refs below | `critical_measurements_required` |
| `speak / recommendation|hypothesis` | output and confidence required | measurements `[]`; refs 1..4 in request order and include the fresh pH and EC source refs after deduplication | null |
| `clarify / clarification` | output required; confidence null | measurements `[]`; refs 1..4 in request order and include the fresh pH and EC source refs after deduplication | null |
| `silent / null` | both null | measurements `[]`; refs `[]` | `no_material_output|insufficient_evidence` |

If `missing_or_stale` is non-empty, only the first row is valid. Recommendation,
hypothesis, clarification, or silence is rejected as `AGENT_OUTPUT_INVALID`;
missing evidence cannot be converted into advice or acceptable model silence.
If `missing_or_stale` is empty, `measurement_request` is invalid.

For a measurement request, deterministic policy refs are: Plant ref first,
then the stale pH ref and stale EC ref in that order when present, deduplicated.
Missing values add no synthetic measurement ref. The model cannot substitute,
drop, reorder, or invent the request set or refs.

Unknown fields, action/approval/Safety fields, target values, dosage/schedule
structures, confirmation claims, refs outside the request, or invalid matrix
combinations reject the entire result. Provider output is never partially
repaired.

## Pending MessageEnvelope mapping

For `measurement_request`, the project adapter creates the candidate text; the
model does not supply it:

- pH only: `Нужно свежее измерение pH перед рекомендацией.`
- EC only: `Нужно свежее измерение EC перед рекомендацией.`
- both: `Нужны свежие измерения pH и EC перед рекомендацией.`

It maps to `runtime_decision=speak`,
`candidate_claim_type=task_request`, `confidence=1.0`, and the deterministic
policy refs. Confidence describes certainty of the project-computed
missing-data condition, not agronomic certainty.

Recommendation maps to `candidate_claim_type=recommendation`, hypothesis to
`hypothesis`, and clarification to the standard `runtime_decision=clarify` /
`candidate_claim_type=clarification`. Model text remains opaque untrusted data.
`silent` returns no envelope.

Every non-silent branch returns only the common immutable
`MessageEnvelopeV1` with `publication_state=pending_classification` and
`consumable_by_agents=false`. FT-010 creates no classification, Bus/UI event,
task, approval, Plant-state mutation, or action.

## Safety and task handoff

- A measurement-request envelope can create an ordinary measurement task only
  after the project-owned classifier returns matching
  `safe_task_request/measurement` and FT-012 applies its current authorization,
  active-Plant, evidence, idempotency, and persistence rules.
- Recommendation/hypothesis/clarification text cannot publish until its
  matching classification and owning downstream current guard permit a route.
- Any physical-action meaning routes to FT-011 through
  `physical_action`; uncertainty fails closed through `blocked_uncertain`.
- A model-selected kind, candidate wording, fresh pH/EC, Boss role,
  `MessageEnvelope`, or classification result is not Safety approval.
- FT-010 cannot request or create `action_task`, approval, device command,
  dosing, solution, pump, light, pH/EC correction, pruning, transplanting, or
  root-trimming execution.

## Provider, authorization, and failure behavior

The existing explicit `deepseek` or `gemini` profile may serve the text-only
advisor. `chatgpt_oauth` remains fail closed without its approved adapter.
There is no default or fallback.

Provider I/O occurs outside database transactions. Before the request is
assembled and again after model I/O, the service requires current same-Farm
session/account/membership/grant read authority and active Plant state. An
archive, revoke, identity change, invalid result, provider failure, or audit
failure returns the matching shared closed outcome with no envelope/effect and
no replay after restore.

Provider request/response bodies, candidate text, prompts, hidden reasoning,
credentials, and authorization state are not persisted or copied into errors
or task evidence. The existing sanitized `agent_runtime_decided` event and
common stable failure catalog remain authoritative; FT-010 adds no event type
or runtime table.

## Verification

Tests MUST prove exact request/result shapes, record order and bounds,
independent pH/EC freshness boundaries, future-dated staleness, deterministic
missing-data request mapping, rejection of advice/silence while critical data
is unavailable, fresh-evidence ref requirements, pending-only Safety/task
separation, current authorization/archive races, explicit provider/no-fallback
composition, redaction, and one non-skipped canonical-product-agent real-model
smoke over authorized PostgreSQL evidence.

The credentialed missing-data fixture must invoke exactly one explicitly bound
DeepSeek or Gemini model and return audited `envelope_ready` with the exact
pending `task_request` envelope for its computed missing/stale set. Clarify,
silence, recommendation, hypothesis, fake/canned output, fallback, skip,
blocked/failed/unaudited outcome, or direct task/Safety effect does not satisfy
that fixture.
