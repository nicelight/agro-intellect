---
description: Feature-scope input for Companion governance and local Farm/Admin accounts in MVP v2.
status: draft
type: analysis
last_updated: 2026-06-02
---
# MVP Scope Expansion Feature-Scope Input

## Status

This is an MVP v2 feature-scope input. The active PRD has already promoted the accepted
direction into [.memory-bank/prd.md](../prd.md) with `clarification_status: complete`.
This document now records scope and impact for downstream `/spec-init`, `/prd`, and
`/spec-design`; it is not a separate integration workflow.

- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](companion-issue-stack-decision-governance.md): Companion `IssueStack`, proposal, and decision governance.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](accounts-farm-access-admin-analysis.md): Accounts, Farm access, Boss admin, personnel, and Plant management.

This document is not a binding feature spec and does not authorize implementation tasks.
Binding implementation scope must come from the active PRD, generated requirements,
SDD backbone, feature specs, and task records.

## Accepted Direction

The MVP should expand from a single-user / one-plant tomato assistant into a bounded
local-first farm workspace:

- one local Farm workspace in the MVP;
- local Accounts with roles;
- Boss admin for personnel, Plant lifecycle, and per-Plant access;
- Engineer and Consultant roles with constrained access;
- multiple Plants are allowed, with `tomato_001` becoming the initial migrated Plant;
- Companion governance is part of the MVP, not only a future architecture note.

The MVP should still avoid production SaaS scope:

- no hosted multi-tenant SaaS requirement;
- no billing/subscription boundary;
- no cloud/server sync requirement;
- no password recovery or enterprise identity provider requirement unless a later PRD adds it;
- no automated physical actuation.

## Constitution And PRD Status

The Constitution has been amended for bounded local-first Farm workspace scope, and the
active PRD is complete. No additional Constitution amendment is required for the scope
captured here.

## Product Scope Target

### Core Actors

- `Boss`: farm owner/admin; manages personnel, roles, Plant lifecycle, Plant access, and admin audit.
- `Engineer`: operator for assigned Plants; performs check-ins, photos, measurements, tasks, and
  action approvals only when granted.
- `Consultant`: advisory/read/comment role; no operational authority by default.
- `Companion`: discussion coordinator that maintains explicit governance state, but cannot bypass
  backend rules or Safety Gate.

### Core Domain Additions

- `Account`
- `Farm`
- `FarmMembership`
- `Plant`
- `PlantAccessGrant`
- admin audit record
- `IssueStack`
- `CompanionProposal`
- `DecisionRecord`
- `HumanAttentionNeeded`

## Architecture Plan

### Authority Model

- PostgreSQL/read model remains runtime authority for mutable state.
- Every plant-bound runtime record should become Farm/Plant scoped.
- Actor identity and permission context must be available to application workflows.
- `timeline.jsonl` remains append-only audit/export, not authority.
- Agent Chat Bus remains agent working context, but context builders must become permission-aware.
- UI Feed remains presentation-only and must not become agent context.
- Companion governance decisions are not Safety Gate approvals.

### Application Boundary

Introduce an `ActorContext` concept at the application/API boundary:

- `account_id`
- `farm_id`
- role/membership refs
- plant permission grants
- session/auth provenance

Controllers validate request/auth shape. Application services enforce authorization and domain rules.
Domain policies remain testable and deterministic.

### Security Baseline

Update the local security model from "loopback/LAN token baseline" to "local auth/authz baseline":

- loopback default remains;
- explicit LAN mode requires authentication;
- sessions/tokens must be redacted from logs, timeline, manifests, Bus, UI Feed, screenshots, and exports;
- every API route that reads or mutates plant/farm data must enforce authorization;
- admin actions require audit events.

### Companion Governance Boundary

Companion may:

- maintain an explicit `IssueStack`;
- choose `current_issue` with rationale;
- publish `CompanionConclusion`;
- create `CompanionProposal`;
- raise `HumanAttentionNeeded`;
- close discussion issues when rules allow.

Companion must not:

- make binding system decisions without a valid `DecisionRecord`;
- use markdown/UI text as authority;
- put unapproved proposals into agent working context;
- bypass Safety Gate or physical-action approval.

## Feature Plan

Candidate MVP features for `/prd` decomposition:

- `FT-015 Local Accounts, Sessions, and Actor Context`
- `FT-016 Farm, Plant Lifecycle, and Plant Access Grants`
- `FT-017 Boss Admin Surface and Admin Audit`
- `FT-018 Companion Issue Stack and Decision Governance`

These IDs are planning targets. `/prd` owns final feature numbering and names.

## Existing Feature Impact

High-impact rework:

- `FT-001`: daily check-in becomes actor/farm/plant scoped.
- `FT-002`: photo intake/catalog/manifests become actor/farm/plant scoped.
- `FT-003`: runtime state and timeline audit add account/farm/plant refs and governance state/audit.
- `FT-010`: local security becomes account/session/authz/admin-audit security.
- `FT-011`: UI adds login/session state, Plant selector, role-aware views, and Boss admin.
- `FT-014`: physical-action approval gains approver identity/permission while remaining separate from governance decisions.

Medium-impact rework:

- `FT-004`: Bus events and context builders become permission-aware; governance event types may be added.
- `FT-005`: UI Feed gains governance/admin presentation events without agent-context leakage.
- `FT-008`: tasks become actor/farm/plant scoped; task creation must respect permissions.
- `FT-009`: dataset governance must isolate evidence/export/trainability by Farm/Plant access.
- `FT-012`: MessageEnvelope separates normal Companion output from typed governance effects.
- `FT-013`: Safety Gate checks actor permission where relevant and remains a hard boundary.

Lower-impact but still affected:

- `FT-006`: Vision Observation inputs and outputs are scoped to authorized Plant context.
- `FT-007`: Hydroponics Advisor inputs, advice, and missing-data tasks are scoped to authorized Plant context.

## Workflow Route

Continue after explicit user instruction from the completed PRD:

1. `/spec-init`
   - Refresh SDD route map if needed.
2. `/prd`
   - Update product, requirements, RTM, epics, features, testing, and navigation.
3. `/spec-design`
   - Rebuild global architecture backbone for Account/Farm/Plant/ActorContext and Companion governance.
4. `/spec-improve`
   - First improve new foundation features.
   - Then re-improve affected existing features in dependency order.
5. `/prd-to-tasks`
   - Only after affected feature specs are complete.

## Suggested Spec-Improve Order

1. New Account/Farm/Governance foundation features.
2. `FT-003` runtime authority and audit.
3. `FT-010` security/auth/authz.
4. `FT-011` UI and Boss admin surface.
5. `FT-004`, `FT-005`, `FT-012` agent and presentation contracts.
6. `FT-013`, `FT-014`, `FT-008` safety, approval, and task semantics.
7. `FT-001`, `FT-002`, `FT-006`, `FT-007`, `FT-009` feature-local scoping updates.

## Closed PRD Decisions

- Deployment is loopback by default; LAN is optional only when explicitly enabled with auth/session/CORS controls.
- MVP is limited to one local Farm workspace.
- Multi-Farm membership/tenancy is out of MVP.
- Roles are Boss/Engineer/Consultant presets plus PlantAccessGrant; the only MVP permission override is `plant_approve_actions`.
- Boss may approve physical-action proposals; Engineer may approve only with per-Plant `plant_approve_actions`; Consultant never approves.
- Consultant is read/comment/advice only and does not create domain task/recommendation records or approvals.
- Plant removal is archive/restore only; no hard delete in MVP.
- `IssueStack` is Plant-scoped.
- `DecisionRecord` may route Plant-scoped workflow and safe check/measurement/follow-up task requests, but cannot mutate Plant state or unlock physical actions.
- A new CompanionProposal for the same Plant issue supersedes the previous pending proposal; no parallel proposals.
- Agent-consumable governance summary is compact typed facts from a valid DecisionRecord only.
- `tomato_001` is the initial Plant inside the local Farm.
- MVP runtime/demo agents must be real LLM/model-backed flows over actual scoped Plant data; fake/mock/stub outputs are not acceptable as the MVP runtime path.

## Non-Negotiable Guardrails

- Governance `DecisionRecord` is not Safety Gate approval.
- Boss/admin authority cannot bypass Safety Gate.
- Physical-action advice still requires fresh data, Safety Gate, and valid human approval.
- UI Feed, admin UI text, unapproved proposals, and raw chat do not become agent facts.
- Agents must receive only authorized, typed, agent-consumable context.
- Product-agent runtime/demo flows must use real LLM/model-backed agents over actual scoped Plant data; test-only mocks are not acceptable as MVP runtime.
- Secrets/session/auth material must never enter logs, timeline, manifests, UI Feed, Bus, screenshots, or exports.

## Verification Gates After Spec Changes

Run after the spec-layer update:

```bash
node scripts/mb-lint.mjs
node scripts/mb-doctor.mjs
```

Run fresh-context Memory Bank review after `/prd` and again after `/spec-design` or the major
feature `/spec-improve` wave.
