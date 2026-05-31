---
description: Глобальные инварианты и запреты проекта (MUST/NEVER).
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Invariants

## MUST
- The MVP scope MUST remain one plant, `tomato_001`, until a later spec explicitly expands it.
- Implementation work MUST derive from PRD, requirements, SDD specs, task records, and linked source-of-truth artifacts.
- PostgreSQL/read model MUST be the runtime authority for mutable operational state.
- `timeline.jsonl` MUST remain append-only audit/export, not primary mutable state.
- Photo binaries MUST be stored as local files, not PostgreSQL or InfluxDB blobs.
- Every accepted photo MUST have canonical `plant_id`, globally unique `photo_id`, `captured_at`, `photo_type`, file path/reference, and `sha256`.
- `event_type=user_photo` MUST include mandatory `payload.plant_id`.
- Agent-originated work output MUST pass through runtime decision handling and `MessageEnvelope` before Agent Chat Bus publication.
- UI Feed and `ui_spoiler_note` MUST stay presentation-only with no agent-context consumption.
- Physical-action advice MUST pass Safety Gate and human approval before becoming user-visible cleared action wording or an action task.
- pH/EC measurements MUST include timestamp/provenance before freshness checks can use them.
- Dataset trainability MUST follow curator decision, split, evidence refs, status, and confirmation-source rules.
- Local photos/manifests MUST remain private by default.

## NEVER
- NEVER treat Agno invocation, workflow events, Team synthesis, memory, storage, or raw model reasoning as domain source of truth.
- NEVER use Agno Team `coordinate` as a domain coordinator.
- NEVER let raw Agno output enter Agent Chat Bus without the project-owned adapter boundary.
- NEVER pass UI Feed, spoiler notes, or raw chain-of-thought to agents as working context.
- NEVER promote agent-labeled hypotheses to confirmed plant state without human review or follow-up evidence.
- NEVER set `can_train_on=true` for raw, agent-labeled, eval, holdout, weak-evidence, or unreviewed `gold` items.
- NEVER display or imply immediate physical-action instructions without Safety Gate clearance.
- NEVER make human approval authorize automated device execution in the MVP.
- NEVER introduce production SaaS, multi-user tenancy, microservices, full dataset registry, real fine-tuning, server sync, or sensor runtime dependency before the MVP specs require them.
- NEVER use `server_verified` before a real server sync stage exists.
- NEVER log or export secrets, API keys, tokens, `.env` values, credentials, or auth material.

## Notes
- Ссылайся на этот файл из архитектурных, контрактных и execution docs, если правило является cross-cutting.
