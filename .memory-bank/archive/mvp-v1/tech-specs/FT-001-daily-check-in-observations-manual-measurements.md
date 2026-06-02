---
description: Feature-local SDD tech spec for FT-001 daily check-in, observations, and manual measurements.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-001-daily-check-in-observations-manual-measurements.md
  - .memory-bank/spec-index.md
---
# FT-001 Daily Check-in, Observations, and Manual Measurements Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-001 before `/prd-to-tasks FT-001`.

FT-001 owns the first evidence-intake slice for `tomato_001`:

- daily check-in prompt support;
- user textual observation or explicit no-data state;
- manual pH/EC input;
- measurement provenance and timestamps;
- freshness representation for downstream analysis and Safety Gate decisions;
- daily observation and manual measurement timeline refs.

FT-001 does not own photo upload, agent conclusions, task creation, Safety Gate decisions, UI layout, or physical-action approval.

## Normative Inputs

- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): daily observation, manual measurement, freshness inputs, and PostgreSQL authority.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): table boundaries, timeline append semantics, and read API authority.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): `daily_observation` and `manual_measurement` audit/export events.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): 24-hour analysis freshness and 2-hour approval freshness windows.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API shape and error envelope.
- [.memory-bank/testing/index.md](../testing/index.md): daily flow and pH/EC freshness verification gates.
- [.memory-bank/invariants.md](../invariants.md): plant scope, runtime authority, timestamp/provenance, and Safety Gate constraints.

## Design Decisions

### Daily Check-In Semantics

- The MVP daily ritual is plant-bound and uses `plant_id=tomato_001`.
- The default prompt text may be the short product prompt: `Как томат сегодня?`
- A check-in can contain observation text, manual measurements, both, or an explicit no-data observation state.
- Missing observation text is valid only when represented explicitly as no-data/empty state; the system must not invent a user observation.
- Check-in timestamps must be timezone-aware.

Recommended states for `daily_observations`:

| State | Meaning |
|---|---|
| `observed` | User provided observation text. |
| `no_observation_provided` | User explicitly completed or skipped the observation without text. |

### Daily Observation Fields

The `daily_observations` boundary from FT-003 remains authoritative. FT-001 refines the minimum fields:

| Field | Rule |
|---|---|
| `observation_id` | Backend-generated globally unique observation ID. |
| `plant_id` | Mandatory; MVP value `tomato_001`. |
| `observed_at` | Timezone-aware timestamp for the observation/check-in. |
| `recorded_at` | Timezone-aware server record time. |
| `observation_state` | `observed` or `no_observation_provided`. |
| `observation_text` | Required for `observed`; null/empty for `no_observation_provided`. |
| `source_type` | `user` for MVP manual check-ins. |
| `source_id` | Stable local source such as `local_user`. |
| `event_refs` | Timeline refs for the corresponding `daily_observation` event. |

Implementation may add a `checkin_date` or correlation ID for UI grouping, but it must not replace `observed_at`, `plant_id`, or timeline refs.

### Manual Measurement Fields

Manual measurement records may include pH, EC, or both. At least one measured value is required for a measurement record.

| Field | Rule |
|---|---|
| `measurement_id` | Backend-generated globally unique measurement ID. |
| `plant_id` | Mandatory; MVP value `tomato_001`. |
| `measured_at` | Timezone-aware timestamp when the user measured pH/EC. |
| `recorded_at` | Timezone-aware server record time. |
| `source_type` | `user` for MVP manual entries. |
| `source_id` | Stable local source such as `local_user`. |
| `ph` | Optional numeric pH value; if present, syntactically valid pH range is 0-14. |
| `ec_ms_cm` | Optional numeric EC value in mS/cm; if present, must be non-negative. |
| `provenance_note` | Optional short user/device note. |
| `observation_ref` | Optional link to the daily observation/check-in that submitted it. |
| `event_refs` | Timeline refs for the corresponding `manual_measurement` event. |

Do not infer pH/EC from photos, agent hypotheses, or UI text. Manual measurement freshness can only use values with `measured_at`, provenance/source, and plant binding.

### Freshness Representation

- Freshness is computed from `measured_at` at read/policy time.
- Do not treat cached freshness flags as authority if they disagree with `measured_at`.
- pH and EC freshness are evaluated independently; pH may be fresh while EC is missing or stale.
- Analysis freshness window is up to 24 hours.
- Physical-action approval freshness window is up to 2 hours.
- Fresh measurements are necessary inputs for relevant Safety Gate decisions, but never sufficient to authorize physical actions.

Recommended derived projection for current measurement context:

| Field | Rule |
|---|---|
| `latest_ph_ref` | Latest valid pH measurement ref, if any. |
| `latest_ec_ref` | Latest valid EC measurement ref, if any. |
| `ph_fresh_for_analysis` / `ec_fresh_for_analysis` | `true` only when latest value age is <= 24 hours. |
| `ph_fresh_for_approval` / `ec_fresh_for_approval` | `true` only when latest value age is <= 2 hours. |
| `missing_or_stale` | List of values missing/stale for the requested downstream purpose. |

FT-001 exposes missing/stale state for downstream features. FT-008 owns measurement task creation, FT-007 owns advisor missing-data policy, and FT-013 owns Safety Gate blocking.

### Timeline Events

A successful observation write must append a `daily_observation` timeline event. Minimum payload:

- `plant_id`;
- `observation_id`;
- `observation_state`;
- `observed_at`.

A successful manual measurement write must append a `manual_measurement` timeline event. Minimum payload:

- `plant_id`;
- `measurement_id`;
- `measured_at`;
- which values were provided: `ph`, `ec_ms_cm`, or both.

Timeline payloads may include safe measurement refs and provenance metadata. They must not contain secrets or raw reasoning.

## API Surface

Minimum FT-001-owned API surface:

- `GET /api/plants/{plant_id}/daily-checkin/prompt`
  - returns the current short prompt and plant binding.
- `POST /api/plants/{plant_id}/daily-checkins`
  - accepts observation state/text and optional pH/EC manual measurement values;
  - returns created observation and measurement refs plus derived freshness projection.
- `POST /api/plants/{plant_id}/measurements`
  - records manual pH/EC outside a full check-in when needed.
- `GET /api/plants/{plant_id}/measurements/latest`
  - returns latest pH/EC refs and derived freshness projection from PostgreSQL/read model.

All errors use the API guidelines error envelope. Expected machine-readable codes include `validation_error`, `unsupported_plant`, `missing_measurement_value`, `missing_timestamp`, `invalid_ph`, `invalid_ec`, and `stale_measurement`.

## Verification Targets

Required before FT-001 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema/unit tests for observation states, required observation fields, manual measurement fields, timezone-aware `observed_at`/`measured_at`, pH range, EC non-negative validation, and at-least-one measurement value.
- Policy tests for pH and EC freshness: 24-hour analysis window, 2-hour physical-action approval window, independent pH/EC freshness, missing values, and stale values.
- Integration tests proving daily observations and manual measurements persist in PostgreSQL/read model with event refs.
- Timeline tests proving `daily_observation` and `manual_measurement` events include required payload identifiers.
- Authority tests proving latest measurement/freshness projections are computed from PostgreSQL measurement records, not from timeline or UI text.
- Negative tests for unsupported plant IDs, missing measurement timestamp/provenance, invented observation text, and stale measurement incorrectly satisfying approval freshness.
- Workflow smoke for check-in with observation only, measurement only, both observation and measurements, and explicit no-observation state.

## Gaps And Non-Goals

- No FT-001 blocker remains for `/prd-to-tasks FT-001`.
- Exact ORM names, migration names, UI component behavior, and fixture shapes belong to implementation tasks.
- Sensor ingestion, automated measurement devices, task creation, hydroponics advice, Safety Gate classification, and physical-action approval are outside FT-001 MVP scope.
