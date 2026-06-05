---
description: Router for active MVP v2 epics derived from the clarified PRD.
status: active
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
---
# Epics Index

Active MVP v2 epics:

- [EP-001 Local Farm Access And Admin](EP-001-local-farm-access-and-admin.md): Accounts, one Farm, roles, ActorContext, Plant lifecycle/access, Boss Admin, and admin audit.
- [EP-002 Plant Evidence And Runtime Authority](EP-002-plant-evidence-and-runtime-authority.md): authorized Plant operations, check-in, photos, runtime state, timeline, and history.
- [EP-003 Shared Agent Harness And Context Boundaries](EP-003-shared-agent-harness-and-context-boundaries.md): AgentHarness, AgentProfile, AgentMemoryRecord, context builder, MessageEnvelope, Agent Chat Bus, UI Feed isolation, and real model runtime.
- [EP-004 Safety-Gated Advisory And Task Loop](EP-004-safety-gated-advisory-and-task-loop.md): Plant state/advisor behavior, Safety Gate, physical-action approval, tasks, approvals, and follow-up.
- [EP-005 Companion Governance](EP-005-companion-governance.md): IssueStack, HumanAttentionNeeded, CompanionProposal, DecisionRecord, and approved governance summaries.
- [EP-006 Dataset Privacy And Local Deployment](EP-006-dataset-privacy-and-local-deployment.md): dataset governance, trainability guardrails, local storage prompt, local privacy, loopback/LAN controls, and secret redaction.

Do not create TASK records directly from these epics. Global `/spec-design` is
complete, feature-level `/spec-improve` is complete for FT-001..FT-017, and
schema-backed TASK-001..TASK-099 records already exist. Use
`.memory-bank/tasks/index.json` and the indexed task records for execution routing.
