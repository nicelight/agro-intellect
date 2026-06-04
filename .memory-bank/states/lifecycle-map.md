---
description: Pre-PRD lifecycle hints for MVP v2 decomposition.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/analysis/product-brief.md
  - .memory-bank/glossary.md
  - .memory-bank/invariants.md
---
# Lifecycle Map

This is a pre-PRD framing artifact only. It records lifecycle hints that affect epic
and feature cuts. Detailed state machines belong to `/spec-design` or feature-local
`/spec-improve`.

| Entity | Lifecycle Summary | States | Transitions Needing Later Detail | Questions |
|---|---|---|---|---|
| Account | Local identity exists for login/session, authorization, attribution, and audit. | local active/invited/disabled style states are expected but not specified here. | create/add/invite, activate, disable/remove, audit attribution. | Exact local account invite/session behavior belongs to /spec-design. |
| FarmMembership | Connects Account to the single local Farm and carries role preset. | active/invited/disabled/removed style states are expected but not specified here. | role assignment/change, membership status change, admin audit. | Exact membership state names belong to /spec-design. |
| Plant | Farm-managed Plant can be used operationally, archived, and restored. | active, archived. | create, archive, restore, authorized history/audit/export access after archive. | Exact retained-history UI/API behavior belongs to later specs. |
| PlantAccessGrant | Gives per-Plant visibility and work authorization. | granted, revoked style states are expected but not specified here. | grant, revoke, update `plant_approve_actions`, filtering of context builders and UI. | Exact permission representation belongs to /spec-design. |
| Daily Check-In | Authorized actor records current Plant evidence. | started/completed style states are expected but not specified here. | observation entry, pH/EC recording, photo upload, audit refs, agent publication trigger. | Exact check-in state model belongs to feature specs. |
| Photo Artifact | Uploaded photo becomes local artifact plus catalog/audit refs. | accepted/local artifact states are expected but not specified here. | validation, sha256, file write, catalog row, initial capture manifest, timeline refs. | Exact manifest/schema details belong to /spec-design. |
| AgentProfile | Product agent definition binds competence, visible context, tools, permissions, outputs, and memory scope inside the shared harness. | defined/active/disabled/versioned style states are expected but not specified here. | create/update profile, bind tools, bind memory scope, disable unsafe profile, version prompt/tool contracts. | Exact AgentProfile schema and versioning belong to /spec-design. |
| AgentHarnessRun | One shared harness run turns scoped context into validated outputs, proposals, observations, traces, or pauses. | context_built/model_called/proposal_received/validated/permissioned/approval_paused/observed/finalized style states are expected but not specified here. | context build, model call, tool/action proposal, schema validation, permission decision, approval pause, structured observation, trace/eval refs. | Exact loop state model, budgets, retry policy, and error observations belong to /spec-design. |
| AgentMemoryRecord | Long-term agent memory preserves source-ref backed Plant analysis for later scoped retrieval. | candidate/active/stale/superseded/archived style states are expected but not specified here. | create candidate from evidence, validate provenance, make retrievable, mark stale/superseded, archive, filter by ActorContext and PlantAccessGrant. | Exact memory lifecycle, trust labels, freshness handling, and compaction policy belong to /spec-design. |
| Agent Output | Real model-backed execution result becomes project-owned publishable output or remains silent. | speak, silent, clarify, escalate runtime decisions. | adapter validation, MessageEnvelope creation, Bus publication, UI Feed projection. | Exact envelope and adapter contracts belong to /spec-design. |
| Physical-Action Proposal | Risky plant-system advice is blocked/routed until safety and human gates pass. | blocked/pending approval/approved/rejected style states are expected but not specified here. | stale/missing data handling, Safety Gate pass/fail, approver authority, action_task unlock, follow-up. | Exact freshness windows and action taxonomy belong to later specs. |
| CompanionProposal | Companion proposal is visible to humans but not operative until valid human decision. | pending, approved, rejected, superseded. | supersede previous pending proposal for same Plant issue, approve/reject, create DecisionRecord. | Exact expiry policy is not needed for PRD; no time-based expiry is required by PRD. |
| DecisionRecord | Typed governance decision directs allowed workflow effects through backend rules. | approved/rejected decision record semantics. | create from valid proposal decision, produce compact agent-consumable summary, route safe task requests. | Exact workflow-effect catalog belongs to /spec-design. |
| Dataset Candidate | Evidence remains non-trainable until governance rules allow a future change. | raw/agent_labeled/needs_review/confirmed/rejected/gold/excluded style vocabulary exists. | evidence refs, review/confirmation source, split, `can_train_on` recomputation. | Full dataset registry and fine-tuning are out of MVP. |
