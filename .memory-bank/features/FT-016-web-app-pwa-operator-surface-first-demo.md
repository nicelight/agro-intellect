---
description: FT-016 Web App PWA Operator Surface And First Demo.
status: draft
type: feature
feature_id: FT-016
epic: EP-006
lifecycle: planned
last_updated: 2026-07-12
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
- Authorized/classified model text is shown literally through escaped/text-node
  rendering; markup-, prompt-, command-, and URL-looking sequences remain inert
  text with no HTML/Markdown interpretation or action activation.

## Edge Cases & Failure Modes

- Unauthorized UI state cannot reveal or mutate Plant data.
- Frontend hide/show cannot replace backend authorization.
- UI markdown/cards/spoiler notes/admin notices cannot become agent facts.
- Candidate text cannot create active markup/links/actions or be copied into
  agent instruction/runtime-authority channels.
- First-demo scope may defer advanced Boss Admin Surface, full role matrix, sync UI details, sensor runtime, and Consultant UI/path where allowed by PRD.

## Verification Targets

- E2E: Boss setup plus Engineer authorized Plant workflow.
- E2E: Safety Gate and Companion governance visible without unsafe authority mixing.
- E2E: unauthorized/archived Plant visibility checks.
- UI smoke: local storage prompt and role-aware navigation.
- UI security smoke: representative HTML/Markdown/prompt-/URL-looking candidate
  text renders literally and triggers no link, command, or action behavior.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Operator PWA module and first-demo data flow.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): frontend/backend authorization boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md) and [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): UI Feed projection and context hygiene boundaries.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): human-facing presentation boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs shown in history.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md), [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md), [.memory-bank/states/companion-governance.md](../states/companion-governance.md), and [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): first-demo state surfaces.

## Feature-Local Design Pressure

- Exact route/view set, API dependency map, role-aware UI behavior, first-demo
  smoke flow, UI Feed projections, literal candidate rendering mechanics, and
  e2e checks.

## SDD Design Gate

- Global/shared status: complete; AD-004, MessageEnvelope, UI Feed, Agent Chat
  Bus, and Safety Action Lifecycle define opaque candidate data, literal
  presentation, no instruction-channel promotion, and unchanged authority
  boundaries.
- Feature-local status: pending `/prd-to-tasks FT-016` for concrete component,
  route/view, and e2e mechanics.
