---
description: Integration plan for introducing Companion governance and local Farm/Admin accounts into the MVP spec layer.
status: draft
type: analysis
last_updated: 2026-06-01
---
# MVP Scope Expansion Integration Plan

## Status

This is a pre-PRD planning artifact. It records the intended route for promoting two
draft analysis notes into the spec layer:

- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](companion-issue-stack-decision-governance.md): Companion `IssueStack`, proposal, and decision governance.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](accounts-farm-access-admin-analysis.md): Accounts, Farm access, Boss admin, personnel, and Plant management.

This document is not a binding feature spec and does not authorize implementation tasks.
Binding changes must go through `/constitution`, `/write-prd`, `/prd`, `/spec-design`,
and feature-level `/spec-improve`.

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

## Constitution Amendment Needed

The current Constitution and PRD prohibit multi-user/SaaS-like expansion before the MVP
needs it. Because Accounts/Farm/Boss Admin are now intentionally in MVP scope, the first
workflow step must be `/constitution`.

Expected amendment shape:

- Replace the absolute "no multi-user architecture before MVP" constraint with a bounded rule:
  local-first, single-Farm, multi-account, role-scoped MVP is allowed when explicitly specified.
- Keep the low-maintenance principle.
- Keep production SaaS, complex sync, cloud hosting, billing, and broad farm-management scope out
  unless a later product stage explicitly adds them.
- Keep Safety Gate and human approval non-negotiable.

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

Add new MVP features after `/write-prd` and `/prd`:

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

Use one combined delta route because Companion and Accounts share role and decision semantics:

1. `/constitution`
   - Amend MVP scope and low-maintenance constraints.
2. `/write-prd`
   - Use both delta sources plus this plan as context.
   - Clarify product decisions before writing binding PRD content.
3. `/spec-init`
   - Refresh SDD route map if needed.
4. `/prd`
   - Update product, requirements, RTM, epics, features, testing, and navigation.
5. `/spec-design`
   - Rebuild global architecture backbone for Account/Farm/Plant/ActorContext and Companion governance.
6. `/spec-improve`
   - First improve new foundation features.
   - Then re-improve affected existing features in dependency order.
7. `/prd-to-tasks`
   - Only after affected feature specs are complete.

## Suggested Spec-Improve Order

1. New Account/Farm/Governance foundation features.
2. `FT-003` runtime authority and audit.
3. `FT-010` security/auth/authz.
4. `FT-011` UI and Boss admin surface.
5. `FT-004`, `FT-005`, `FT-012` agent and presentation contracts.
6. `FT-013`, `FT-014`, `FT-008` safety, approval, and task semantics.
7. `FT-001`, `FT-002`, `FT-006`, `FT-007`, `FT-009` feature-local scoping updates.

## Open Decisions For `/constitution` And `/write-prd`

- Is MVP deployment strictly local/LAN, or is hosted access allowed later only?
- Is MVP limited to one Farm workspace?
- Can one Account belong to multiple Farms in MVP?
- Are roles only presets, or can Boss grant per-permission overrides in MVP?
- Which roles can approve physical-action proposals?
- Is Consultant allowed to comment only, or create recommendations/tasks?
- What exact action archives/removes a Plant: archive, delete, hide, or transfer?
- What is the scope of `IssueStack`: per Farm, per Plant, per conversation, per daily check-in, or per workflow session?
- What decisions can `DecisionRecord` make: discussion direction only, task creation, workflow routing, or state changes?
- How does `CompanionProposal.version` expire or get superseded?
- What approved governance summary becomes agent-consumable?
- How should `tomato_001` migrate into the new Farm/Plant model?

## Non-Negotiable Guardrails

- Governance `DecisionRecord` is not Safety Gate approval.
- Boss/admin authority cannot bypass Safety Gate.
- Physical-action advice still requires fresh data, Safety Gate, and valid human approval.
- UI Feed, admin UI text, unapproved proposals, and raw chat do not become agent facts.
- Agents must receive only authorized, typed, agent-consumable context.
- Secrets/session/auth material must never enter logs, timeline, manifests, UI Feed, Bus, screenshots, or exports.

## Verification Gates After Spec Changes

Run after the spec-layer update:

```bash
node scripts/mb-lint.mjs
node scripts/mb-doctor.mjs
```

Run fresh-context Memory Bank review after `/prd` and again after `/spec-design` or the major
feature `/spec-improve` wave.
