---
description: Archived MVP v1 global invariants and prohibitions.
status: archived
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/archive/mvp-v1/constitution.md
  - .memory-bank/archive/mvp-v1/prd.md
  - .memory-bank/archive/mvp-v1/spec-index.md
---
# Invariants

This archived file contains the MVP v1 cross-cutting MUST/NEVER guardrails. Field lists,
payload schemas, state machines, freshness windows, transition formulas, and implementation
shapes lived in their owning domain, contract, state, runbook, or feature-local tech specs.

## MUST

- The MVP scope MUST remain one plant, `tomato_001`, until a later spec explicitly expands it.
- Implementation work MUST follow Spec Before Code: PRD, requirements, SDD specs, task records, and linked source-of-truth artifacts.
- PostgreSQL/read model MUST be the runtime authority for mutable operational state; `timeline.jsonl` MUST remain append-only audit/export. See [runtime-data-model.md](domains/runtime-data-model.md) and [timeline-event.md](contracts/timeline-event.md).
- Photo catalog, file, manifest, upload-validation, and photo timeline details MUST follow [photo-artifacts.md](domains/photo-artifacts.md), [local-security.md](runbooks/local-security.md), and relevant feature-local tech specs.
- Timeline event envelope and payload specifics MUST follow [timeline-event.md](contracts/timeline-event.md) and relevant feature-local tech specs.
- Agent-originated domain output MUST pass through project-owned runtime decision, `MessageEnvelope`, and Agent Chat Bus publication boundaries before it becomes agent-consumable. See [message-envelope.md](contracts/message-envelope.md) and [agent-chat-bus.md](contracts/agent-chat-bus.md).
- UI Feed and `ui_spoiler_note` MUST stay presentation-only and unavailable as agent working context. See [ui-feed.md](contracts/ui-feed.md).
- Physical-action advice MUST pass Safety Gate and human approval before becoming cleared user-visible action wording or an action task. See [safety-approval.md](states/safety-approval.md).
- pH/EC provenance and freshness MUST follow their owning runtime/state/safety specs; fresh data is never sufficient by itself for physical action.
- Dataset trainability MUST follow [dataset-governance.md](states/dataset-governance.md); UI Feed, timeline snapshots, manifests, and raw agent output never grant trainability by themselves.
- MVP data and artifacts MUST remain local/private by default, and sync status MUST remain `local_only` until a later server-sync spec exists.

## NEVER

- NEVER treat Agno invocation, workflow events, Team synthesis, memory, storage, or raw model reasoning as domain source of truth.
- NEVER use Agno Team `coordinate` as a domain coordinator.
- NEVER let raw Agno output, provider history, raw reasoning, UI Feed content, timeline replay, or presentation-only summaries bypass the project-owned adapter/publication boundary into Agent Chat Bus or agent working context.
- NEVER pass UI Feed, spoiler notes, or raw chain-of-thought to agents as working context.
- NEVER promote agent-labeled hypotheses to confirmed plant state without human review or follow-up evidence.
- NEVER set or imply `can_train_on=true` outside the dataset governance lifecycle.
- NEVER display or imply immediate physical-action instructions without Safety Gate clearance.
- NEVER make human approval authorize automated device execution in the MVP.
- NEVER introduce production SaaS, multi-user tenancy, microservices, full dataset registry, real fine-tuning, server sync, or sensor runtime dependency before the MVP specs require them.
- NEVER use `server_verified` before a real server sync stage exists.
- NEVER log or export secrets, API keys, tokens, `.env` values, credentials, or auth material.
