---
description: FT-016 Web App PWA Operator Surface And First Demo.
status: draft
type: feature
feature_id: FT-016
epic: EP-006
lifecycle: planned
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
---
# FT-016 Web App PWA Operator Surface And First Demo

## Use Cases

- Boss uses a role-aware local Web App/PWA surface to set up or use the Farm workspace, create/manage Engineer access, and see admin audit.
- Engineer uses the PWA to select authorized Plant, run daily check-in, upload photo, record pH/EC, see agent outputs, handle tasks/approvals, and record follow-up.
- User sees Safety Gate blocks/prompts, Companion HumanAttentionNeeded/proposal/decision path, dataset/local storage status, and Plant history.
- Consultant UI/path may be deferred from first demo while Consultant remains in product scope.

## Acceptance Criteria

- First demo includes Boss and at least one Engineer path on `tomato_001`.
- First demo includes Plant selector access checks, daily check-in, photo upload with file/catalog/sha256/manifest refs, manual pH/EC, real model-backed product agents, real vision processing, Plant State trust statuses, Hydroponics Advisor missing-data behavior, Task & Follow-up behavior, Safety Gate behavior, Companion HumanAttentionNeeded/proposal/decision path, dataset fields, timeline audit/export, and local storage prompt.
- UI remains role-aware and presentation-only where applicable.
- UI does not become backend authority or agent working context.

## Edge Cases & Failure Modes

- Unauthorized UI state cannot reveal or mutate Plant data.
- Frontend hide/show cannot replace backend authorization.
- UI markdown/cards/spoiler notes/admin notices cannot become agent facts.
- First-demo scope may defer advanced Boss Admin Surface, full role matrix, sync UI details, sensor runtime, and Consultant UI/path where allowed by PRD.

## Verification Targets

- E2E: Boss setup plus Engineer authorized Plant workflow.
- E2E: Safety Gate and Companion governance visible without unsafe authority mixing.
- E2E: unauthorized/archived Plant visibility checks.
- UI smoke: local storage prompt and role-aware navigation.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Operator PWA module and first-demo data flow.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): frontend/backend authorization boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md) and [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): UI Feed projection and context hygiene boundaries.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): human-facing presentation boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs shown in history.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md), [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md), [.memory-bank/states/companion-governance.md](../states/companion-governance.md), and [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): first-demo state surfaces.

## SDD Design Gate

Global `/spec-design` is complete for shared backbone/spec routing. Then run `/prd-to-tasks FT-016`; it must define exact route/view set, API dependency map, role-aware UI behavior, first-demo smoke flow, UI Feed projections, and e2e checks during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-016` only for repair or advanced refresh without task generation.
