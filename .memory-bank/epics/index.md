---
description: Active MVP v2 epic router.
status: active
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
---
# Epics Index

Active MVP v2 epics are draft L2 decomposition artifacts derived from the clarified PRD. They are not implementation plans and do not replace feature-level SDD design inside `/prd-to-tasks`.

## Active Epics

- [EP-001 Local Farm Access And Admin](EP-001-local-farm-access-admin.md): local Accounts, one Farm, role presets, PlantAccessGrant, Plant lifecycle, Boss Admin Surface, and admin audit.
- [EP-002 Plant Operations Evidence Authority](EP-002-plant-operations-evidence-authority.md): authorized daily Plant workflows, photo intake, runtime state, Plant history, and timeline audit/export.
- [EP-003 Agent Runtime And Context Hygiene](EP-003-agent-runtime-context-hygiene.md): real model-backed agents, runtime decision, MessageEnvelope, Agent Chat Bus, UI Feed isolation, Vision Observation, Plant State trust, and Hydroponics Advisor.
- [EP-004 Safety Tasks And Follow-Up](EP-004-safety-tasks-follow-up.md): Safety Gate, physical-action approval, human-performed action tasks, and follow-up outcomes.
- [EP-005 Companion Governance](EP-005-companion-governance.md): IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, DecisionRecord, and approved governance summary boundaries.
- [EP-006 Local Privacy And Operator Surface](EP-006-local-privacy-operator-surface.md): dataset governance, local privacy/exposure controls, storage prompt, and first-demo Web App/PWA operator surface.

## Routing

Global `/spec-design` gate is complete, and the next workflow pass may refresh it for expanded SDD coverage.

Run `/prd-to-tasks FT-<NNN>` for product feature tasking. That command owns feature-level SDD design before task slicing; use standalone `/spec-improve FT-<NNN>` only for repair or advanced refresh without generating tasks.
