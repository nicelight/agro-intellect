---
description: Глобальные инварианты и запреты проекта (MUST/NEVER).
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Invariants

This file contains only cross-cutting MUST/NEVER guardrails. Field lists, payload schemas,
state machines, freshness windows, transition formulas, and implementation shapes live in
their owning domain, contract, state, runbook, or feature-local tech specs.

## MUST
- The MVP scope MUST remain one plant, `tomato_001`, until a later spec explicitly expands it.
- Implementation work MUST follow Spec Before Code: PRD, requirements, SDD specs, task records, and linked source-of-truth artifacts.
- PostgreSQL/read model MUST be the runtime authority for mutable operational state; `timeline.jsonl` MUST remain append-only audit/export. See [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md): runtime entity authority, and [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md): timeline event contract.
- Photo catalog, file, manifest, upload-validation, and photo timeline details MUST follow [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md): photo artifact boundary, [.memory-bank/runbooks/local-security.md](runbooks/local-security.md): local security/privacy rules, and relevant feature-local tech specs.
- Timeline event envelope and payload specifics MUST follow [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md): append-only audit/export contract and relevant feature-local tech specs.
- Agent-originated domain output MUST pass through project-owned runtime decision, `MessageEnvelope`, and Agent Chat Bus publication boundaries before it becomes agent-consumable. See [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md): output contract, and [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md): Bus publication boundary.
- UI Feed and `ui_spoiler_note` MUST stay presentation-only and unavailable as agent working context. See [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md): UI Feed context hygiene.
- Physical-action advice MUST pass Safety Gate and human approval before becoming cleared user-visible action wording or an action task. See [.memory-bank/states/safety-approval.md](states/safety-approval.md): safety approval lifecycle.
- pH/EC provenance and freshness MUST follow their owning runtime/state/safety specs; fresh data is never sufficient by itself for physical action.
- Dataset trainability MUST follow [.memory-bank/states/dataset-governance.md](states/dataset-governance.md): dataset governance lifecycle; UI Feed, timeline snapshots, manifests, and raw agent output never grant trainability by themselves.
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

## Notes
- Ссылайся на этот файл из архитектурных, контрактных и execution docs, если правило является cross-cutting.
