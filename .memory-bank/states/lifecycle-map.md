---
description: Pre-PRD lifecycle hints for MVP v2 decomposition.
status: active
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/glossary.md
  - .memory-bank/invariants.md
---
# Lifecycle Map

This is a pre-PRD framing artifact only. It records lifecycle hints that affect epic
and feature cuts. Detailed state machines belong to canonical state specs.

| Entity | Lifecycle Summary | States | Transitions Needing Later Detail | Questions |
|---|---|---|---|---|
| Account | Local identity exists for login/session, authorization, attribution, and audit. | active, disabled. | direct create with required password hash; disable; audit attribution. | First-Boss bootstrap CLI contract remains for FT-002/FT-003 design. |
| FarmMembership | Connects Account to the single local Farm and carries role preset. | active, disabled. | direct active creation with Account; role/status change; admin audit. | Plant grants remain a separate FT-002 flow. |
| Plant | Farm-managed Plant can be created by active Boss/Engineer, used operationally, and archived/restored by Boss. | active, archived. | create with Engineer creator-grant atomicity, Boss-only archive/restore, authorized history/audit/export access after archive. | Exact retained-history UI/API behavior belongs to later specs. |
| PlantAccessGrant | Gives per-Plant visibility and work authorization; Engineer creation starts an active creator grant with `plant_approve_actions=false`. | active, revoked. | atomic creator grant, Boss grant/revoke/update `plant_approve_actions`, filtering of context builders and UI. | Exact persistence and HTTP representation belongs to `/prd-to-tasks FT-002`. |
| Daily Check-In | Authorized actor records current Plant evidence. | started/completed style states are expected but not specified here. | observation entry, pH/EC recording, photo upload, audit refs, agent publication trigger. | Exact check-in state model belongs to feature specs. |
| Photo Artifact | Uploaded photo becomes local artifact plus catalog/audit refs. | accepted/local artifact states are expected but not specified here. | validation, sha256, file write, catalog row, initial capture manifest, timeline refs. | Exact manifest/schema details belong to /spec-design. |
| Agent Output | Real model-backed execution result becomes a project-owned pending MessageEnvelope or model-declared silence. | speak, silent, clarify, escalate candidate decisions plus pending classification. | adapter validation, MessageEnvelope creation, strict project-owned classification, then guarded Bus/UI/task/Safety routing. | Exact envelope, adapter, and shared classification result belong to /spec-design. |
| Physical-Action Proposal | Risky plant-system advice is blocked/routed until safety and human gates pass. | blocked/pending approval/approved/rejected style states are expected but not specified here. | stale/missing data handling, Safety Gate pass/fail, approver authority, action_task unlock, follow-up. | Exact freshness windows and action taxonomy belong to later specs. |
| CompanionProposal | Companion proposal is visible to humans but not operative until valid human decision. | pending, approved, rejected, superseded. | supersede previous pending proposal for same Plant issue, approve/reject, create DecisionRecord. | Exact expiry policy is not needed for PRD; no time-based expiry is required by PRD. |
| DecisionRecord | Typed governance decision directs allowed workflow effects through backend rules. | approved/rejected decision record semantics. | create from valid proposal decision, produce compact agent-consumable summary, route safe task requests. | Exact workflow-effect catalog belongs to /spec-design. |
| Dataset Candidate | Evidence remains non-trainable until governance rules allow a future change. | `candidate_status`: `candidate`, `needs_review`, `confirmed`, `rejected`, `excluded`; `candidate_origin`: `raw|agent_labeled`; `quality_tier`: `standard|gold`. | evidence refs, review/confirmation source, split, derived `can_train_on`. | Full dataset registry and fine-tuning are out of MVP. |
