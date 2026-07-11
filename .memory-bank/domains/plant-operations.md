---
description: Concrete Plant operations check-in, observation, manual measurement, and freshness data specification.
status: active
type: data_spec
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/features/FT-004-authorized-plant-operations-daily-check-in.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plant-state-trust.md
---
# Plant Operations Data

## Scope

Defines the FT-004 runtime data shape for authorized daily check-ins,
observation evidence, manual pH/EC measurements, source refs, timeline refs,
and derived freshness projections.

## Out of scope

Photo file/catalog storage, Plant history presentation, agent output, Safety
Gate approval, task/follow-up state machines, PWA components, sensors, and
automated actuation.

## Related specs

- [.memory-bank/contracts/plant-operations-http.md](../contracts/plant-operations-http.md)
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md)
- [.memory-bank/contracts/access/actor-context.md](../contracts/access/actor-context.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md)
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md)

## Runtime records

All identifiers use PostgreSQL native `uuid`, SQLAlchemy `Uuid(as_uuid=True)`,
Python `uuid.UUID`, and application-generated `uuid.uuid4`.

`daily_checkins`:

- `check_in_id`: primary UUID.
- `farm_id`: FK to `farms.farm_id`, `ON DELETE RESTRICT`.
- `plant_id`: FK to `plants.plant_id`, `ON DELETE RESTRICT`.
- `actor_account_id`, `actor_membership_id`: safe attribution refs.
- `check_in_state`: `completed`.
- `observed_at`: timezone-aware user observation time or server receive time.
- `recorded_at`: timezone-aware server record time.
- `observation_state`: `observed | no_observation_provided`.
- `observation_text`: required non-blank text only for `observed`; null for
  `no_observation_provided`.
- `source_refs`: JSON object with safe Account/Membership/Plant/session
  provenance refs, excluding auth material.
- `event_refs`: JSON object containing the required timeline event id(s).
- `created_at`: timezone-aware server timestamp.

`manual_measurements`:

- `measurement_id`: primary UUID.
- `farm_id`, `plant_id`: same authority scope as `daily_checkins`.
- nullable `check_in_id`: FK to `daily_checkins.check_in_id`, `ON DELETE
  RESTRICT`, when submitted as part of a check-in.
- `actor_account_id`, `actor_membership_id`: safe attribution refs.
- `measured_at`: timezone-aware timestamp for when the value was measured.
- `recorded_at`: timezone-aware server record time.
- nullable `ph`: numeric pH value, valid when `0 <= ph <= 14`.
- nullable `ec_ms_cm`: numeric EC value in mS/cm, valid when `ec_ms_cm >= 0`.
- nullable `provenance_note`: short user/device note; redacted before audit.
- `source_type`: `manual_user`.
- `source_refs`: safe provenance refs.
- `trust_status`: `confirmed` for manual human-entered values; later conflicts
  are represented by Plant State Trust, not by overwriting the measurement.
- `event_refs`: JSON object containing the required timeline event id.
- `created_at`: timezone-aware server timestamp.

At least one of `ph` or `ec_ms_cm` is required for a measurement record.

### Canonical measurement values

- pH is stored and exposed at scale 2; EC is stored and exposed at scale 3.
- Accepted finite in-range numeric input is normalized with decimal
  `ROUND_HALF_UP` to those scales before the ORM row, immediate result,
  freshness projection, and timeline summary are constructed.
- The one normalized value is used by PostgreSQL, the success response,
  subsequent reads, and audit/export summaries. Those surfaces MUST NOT report
  different values for the same `measurement_id`.

## Check-in rules

- A check-in is created only for an active Plant and an ActorContext whose
  Plant permission resolves `can_operate=true`.
- Boss and granted Engineer can create check-ins. Consultant can read/comment
  where allowed by downstream reads but cannot create check-ins or
  measurements.
- Archived, missing, unauthorized, revoked-grant, wrong-Farm, and disabled
  membership paths fail before persistence and write no timeline event.
- A check-in must contain at least one of:
  - `observation_state=observed` with non-blank `observation_text`;
  - `observation_state=no_observation_provided`;
  - one valid manual pH/EC measurement.
- Missing observation text is never invented. A skipped observation is explicit
  `no_observation_provided`.
- `observation_state` may be omitted only when `observation_text` is also
  omitted and a valid measurement is present. Supplying non-blank observation
  text without an explicit state is invalid and MUST NOT be silently converted
  to `no_observation_provided`.
- Photo upload is not performed by FT-004. A check-in response may expose a
  photo upload entry-point/ref for FT-005, but it must not claim photo
  acceptance.

## Freshness projection

Freshness is derived at read/policy time from `measured_at`; cached booleans
are not authority.

- `analysis` freshness window: 24 hours.
- `approval_input` freshness window: 2 hours.
- pH and EC freshness are computed independently.
- A value is fresh only when its timestamp is within the closed interval
  `computed_at - window <= measured_at <= computed_at`. Future-dated evidence
  is retained as entered but is stale for both purposes until server time
  reaches it; no clock-skew allowance is implicit.
- Missing or stale values remain explicit in projection output and must not be
  silently treated as fresh.
- Fresh pH/EC is never sufficient to authorize physical action. Safety Gate and
  authorized human approval remain separate.

Projection fields:

- nullable `latest_ph_ref`, `latest_ec_ref`.
- nullable `latest_ph`, `latest_ec_ms_cm`.
- `ph_fresh_for_analysis`, `ec_fresh_for_analysis`.
- `ph_fresh_for_approval_input`, `ec_fresh_for_approval_input`.
- `missing_or_stale`: list of `ph` and/or `ec` for the requested purpose.
- `computed_at`: timezone-aware server timestamp.

## Timeline refs

- A successful check-in writes a `daily_checkin_recorded` timeline event.
- A successful manual measurement writes a `manual_measurement_recorded`
  timeline event.
- The runtime rows store the generated timeline event ids in `event_refs`.
- Timeline failure handling, event envelope, JSONL append rules, event ref
  shape, and replay limits are owned by
  [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md).

`daily_checkin_recorded` uses `source_type=daily_checkin`,
`source_id=check_in_id`, and a redacted `payload_summary` containing
`observation_state`, `observed_at`, `recorded_at`, optional
`measurement_refs`, and safe source refs.

`manual_measurement_recorded` uses `source_type=manual_measurement`,
`source_id=measurement_id`, and a redacted `payload_summary` containing
`check_in_id` when present, `measured_at`, `recorded_at`, value-presence flags
for pH/EC, optional numeric pH/EC values, `trust_status`, and safe source refs.
The `provenance_note` is included only after redaction.

## Verification

- Migration/model tests prove UUID PK/FK parity, restrictive FKs, allowed
  states, pH/EC constraints, non-blank observation text, at-least-one
  measurement value, and no cascading authority delete.
- Service tests prove authorized Boss/Engineer writes, Consultant/archived/
  revoked/unauthorized denials, no partial writes, and safe source refs.
- Freshness tests cover 24h analysis, 2h approval input, missing values, stale
  values, future-dated values, and independent pH/EC computation.
- PostgreSQL-backed normalization tests prove excess-scale accepted inputs use
  one canonical value in the ORM result, database reread, freshness projection,
  and timeline summary.
- Observation validation tests prove supplied text without a state is rejected
  without a check-in, measurement, or timeline success event.
- Authority tests prove freshness and latest measurements come from
  PostgreSQL/read model, not timeline, UI Feed, photo manifests, or agent text.
