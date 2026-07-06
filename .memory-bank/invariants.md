---
description: Глобальные инварианты и запреты проекта (MUST/NEVER).
status: active
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Invariants

This file contains only cross-cutting MUST/NEVER guardrails. Field lists, payload schemas,
state machines, freshness windows, transition formulas, and implementation shapes live in
their canonical domain, contract, state, runbook, or other subject spec.

## MUST
- The MVP scope MAY expand to a bounded local-first Farm workspace with local Accounts, role-scoped access, and multiple Plants only after PRD/spec promotion. Until the migration is specified, `tomato_001` remains the initial canonical Plant.
- Implementation work MUST follow Spec Before Code: PRD, requirements, SDD specs, task records, and linked source-of-truth artifacts.
- PostgreSQL/read model MUST remain the runtime authority for mutable operational state unless a later active architecture spec explicitly replaces that decision.
- `timeline.jsonl` MUST remain append-only audit/export, not primary mutable state.
- Photo catalog, file, manifest, upload-validation, and photo timeline details MUST be re-specified for MVP v2 before task decomposition.
- MVP product-agent runtime/demo flows MUST use real LLM/model-backed agents or real model-backed adapters over actual scoped Plant data; fake, mock, hardcoded, or stubbed agent outputs do not satisfy MVP acceptance criteria.
- Agent-originated domain output MUST pass through project-owned runtime decision, `MessageEnvelope`, and Agent Chat Bus publication boundaries before it becomes agent-consumable.
- UI Feed and `ui_spoiler_note` MUST stay presentation-only and unavailable as agent working context.
- Governance `DecisionRecord` MUST stay separate from Safety Gate physical-action approval.
- Physical-action advice MUST pass Safety Gate and authorized human approval before becoming cleared user-visible action wording or an action task.
- Archived Plant MUST be a global operational deny: dependent records remain
  retained without automatic transition, and restore MUST NOT resume or
  execute them without current authorization and owning lifecycle checks.
- pH/EC provenance and freshness MUST follow their owning runtime/state/safety specs; fresh data is never sufficient by itself for physical action.
- Dataset trainability MUST follow its owning dataset governance lifecycle; UI Feed, timeline snapshots, manifests, and raw agent output never grant trainability by themselves.
- MVP data and artifacts MUST remain local/private by default, and sync status MUST remain `local_only` until a later server-sync spec exists.

## NEVER
- NEVER treat Agno invocation, workflow events, Team synthesis, memory, storage, or raw model reasoning as domain source of truth.
- NEVER use Agno Team `coordinate` as a domain coordinator.
- NEVER let raw Agno output, provider history, raw reasoning, UI Feed content, timeline replay, or presentation-only summaries bypass the project-owned adapter/publication boundary into Agent Chat Bus or agent working context.
- NEVER use fake, mock, hardcoded, or stubbed product-agent outputs as the MVP runtime/demo path; test-only mocks are allowed only for automated tests.
- NEVER pass UI Feed, spoiler notes, or raw chain-of-thought to agents as working context.
- NEVER promote agent-labeled hypotheses to confirmed plant state without human review or follow-up evidence.
- NEVER set or imply `can_train_on=true` outside the dataset governance lifecycle.
- NEVER display or imply immediate physical-action instructions without Safety Gate clearance.
- NEVER make human approval authorize automated device execution in the MVP.
- NEVER introduce production SaaS, hosted/cloud sync as an MVP requirement, billing/subscription boundaries, enterprise identity, microservices, full dataset registry, real fine-tuning, server sync, sensor runtime dependency, automated physical actuation, or broad farm-management scope before a later product stage explicitly requires them.
- NEVER use `server_verified` before a real server sync stage exists.
- NEVER log or export secrets, API keys, tokens, `.env` values, credentials, or auth material.

## Notes
- Ссылайся на этот файл из архитектурных, контрактных и execution docs, если правило является cross-cutting.
