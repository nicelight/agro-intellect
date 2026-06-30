---
description: FT-001 - Daily check-in, observations, and manual measurements.
status: draft
lifecycle: planned
parent_epic: EP-001
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md
---
# FT-001 Daily Check-in, Observations, and Manual Measurements

## Parent Epic

- [EP-001 Evidence Intake and Runtime Authority](../epics/EP-001-evidence-intake-runtime-authority.md): evidence intake and authority boundaries for `tomato_001`.

## Purpose

Capture the daily user ritual for `tomato_001`: check-in prompt, textual observation, and manual pH/EC measurements with timestamp, provenance, and freshness semantics for later analysis and safety decisions.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-001, FR-004, UX/interaction flow, edge cases, acceptance criteria, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-001 and REQ-004.
- [.memory-bank/constitution.md](../constitution.md): KISS, source-of-truth discipline, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): route map for runtime data model, source-of-truth, timeline, and first-demo verification areas.
- [.memory-bank/testing/index.md](../testing/index.md): daily flow and pH/EC freshness verification.

## Use Cases

- The system starts or guides the daily ritual with a short check-in prompt.
- The user records textual observations for the current day.
- The user enters pH and EC measurements when available.
- The system records timestamps, provenance, and event/state refs for observations and measurements.
- Downstream agents can see whether pH/EC is fresh for analysis or stale/missing.

## Acceptance Criteria

- Daily check-in data is bound to `tomato_001` and recorded as traceable state/event data.
- Textual observations can be recorded for the day.
- Manual pH and EC entries include timestamp and provenance.
- pH/EC measurements are fresh for analysis for up to 24 hours.
- pH/EC measurements are fresh for physical-action approval for up to 2 hours.
- Missing pH/EC does not block observation intake.
- Missing or stale pH/EC can be represented for downstream clarification, measurement tasks, and Safety Gate blocks.

## Edge Cases / Failure Modes

- The daily check-in has no observation text: allow an explicit empty/no-data state rather than inventing a user observation.
- pH or EC is missing: keep intake valid and require downstream measurement requests for solution-related analysis.
- pH/EC is older than 24 hours: stale for analysis.
- pH/EC is older than 2 hours: stale for physical-action approval.
- Measurement timestamp or provenance is missing: reject or mark incomplete before it can satisfy freshness rules.
- A measurement is attached to a plant other than `tomato_001`: reject for MVP scope.

## Test Strategy Pointers

- `workflow:daily-check-in-smoke` for prompt, observation, optional measurement, state/event persistence, and timeline-backed traceability.
- `integration:observation-state-events` for observation persistence and event refs.
- `policy:ph-ec-freshness` for 24-hour analysis and 2-hour physical-action approval windows.
- `workflow:missing-or-stale-measurement-task` for downstream request behavior when pH/EC is missing or stale.

## Constraints / Invariants

- Scope is one plant: `tomato_001`.
- Do not infer measurements from photos or agent hypotheses.
- Manual measurements need timestamp and provenance.
- pH/EC freshness is a downstream safety input, not an automatic authorization for physical action.
- Keep intake simple enough for the first demo.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. `/spec-improve FT-001` completed the feature-local SDD gate.

- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): observation/measurement refs and pH/EC freshness inputs.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): PostgreSQL/read-model authority and artifact boundaries.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): event refs and append-only audit/export trail.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): 24-hour analysis and 2-hour approval freshness windows.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): daily-flow smoke and policy gates.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](../tech-specs/FT-001-daily-check-in-observations-manual-measurements.md): feature-local decisions for observation/measurement fields, freshness projection, timeline payloads, API shape, and verification targets.

No FT-001 design blocker remains for `/prd-to-tasks FT-001`.
