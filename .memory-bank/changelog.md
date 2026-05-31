---
description: Лог изменений Memory Bank.
status: active
---
# Changelog

## [2026-05-31] FT-009 spec-improve finalized
- Added a feature-local SDD tech spec for FT-009 Dataset Governance and Trainability to complete the handoff surface.
- Clarified dataset item boundary, transition service, trainability recomputation, evidence refs, curator rules, API/service surface, and verification targets without creating a full dataset registry.
- Updated FT-009, spec-index, tech-specs router, and Memory Bank routing.

## [2026-05-31] FT-013 spec-improve completed
- Completed feature-level SDD design for FT-013 Safety Gate for Physical-Action Advice.
- Added deterministic Safety Gate policy, action taxonomy, pH/EC approval freshness, `SafetyGateDecision`, fail-closed outcomes, display checks, Bus/UI/task handoffs, and verification targets.
- Updated FT-013, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-005 spec-improve completed
- Completed feature-level SDD design for FT-005 UI Feed and Context Hygiene.
- Added UI Feed presentation storage, event payloads, controlled spoiler notes, context filtering, timeline/export snapshot rules, display safety, API surface, and verification targets.
- Updated FT-005, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-012 spec-improve completed
- Completed feature-level SDD design for FT-012 Agent Runtime Decisions and MessageEnvelope Output Contracts.
- Added runtime decision state machine, adapter boundary, `MessageEnvelope` schema, decision-to-event mapping, concise-output rules, `silent` audit, and safety/escalation boundary.
- Updated FT-012, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-004 spec-improve completed
- Completed feature-level SDD design for FT-004 Agent Chat Bus Event Stream and Publication Boundary.
- Added Bus working-stream persistence, envelope validation, event payload minimums, publication service, context filtering, influence levels, and anti-cheat verification targets.
- Updated FT-004, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-001 spec-improve completed
- Completed feature-level SDD design for FT-001 Daily Check-in, Observations, and Manual Measurements.
- Added observation/measurement fields, explicit no-data state, pH/EC units and provenance, computed freshness projection, API shape, timeline payloads, and verification targets.
- Updated FT-001, spec-index, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-002 spec-improve completed
- Completed feature-level SDD design for FT-002 Photo Intake, Catalog, and Capture Manifests.
- Added photo upload API, backend-generated `photo_id`, file path layout, initial capture manifest v1, publication sequence, `user_photo` timeline payload, and verification targets.
- Updated FT-002, spec-index, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-010 spec-improve completed
- Completed feature-level SDD design for FT-010 Local Security, Privacy, and Lazy Sync.
- Added LAN bearer-token auth, CORS allowlist, upload limits/MIME allowlist, safe path handling, secret redaction, privacy, `local_only`, and 200 MB prompt-only verification targets.
- Updated FT-010, spec-index, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-009 spec-improve completed
- Completed feature-level SDD design for FT-009 Dataset Governance and Trainability.
- Added dataset lifecycle transition matrix, actor/source rules, forbidden transitions, trainability side effects, transition audit refs, and verification targets.
- Updated FT-009 and spec-index routing to mark the feature design gate complete.

## [2026-05-31] Architecture docs consolidated
- Merged source-of-truth, module boundary, and Agno boundary architecture rules into `.memory-bank/architecture/system-architecture.md`.
- Removed split architecture docs and updated Memory Bank routing links to the consolidated architecture backbone.

## [2026-05-27] Constitution ratified
- Ratified project-specific Constitution from `/constitution` interview.
- Updated analysis routing to recommend `/write-prd`.
- Updated `/constitution` interview formatting instructions for `(adv)` markers.

## [2026-05-27] Initial setup
- Created Memory Bank skeleton
- Seeded core docs (product, requirements, testing, task registry)
