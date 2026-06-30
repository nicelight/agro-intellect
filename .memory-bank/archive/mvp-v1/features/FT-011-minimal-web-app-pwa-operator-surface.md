---
description: FT-011 - Minimal Web App/PWA operator surface.
status: draft
lifecycle: planned
parent_epic: EP-004
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-011-minimal-web-app-pwa-operator-surface.md
---
# FT-011 Minimal Web App/PWA Operator Surface

## Parent Epic

- [EP-004 Local Operations and Operator UI](../epics/EP-004-local-operations-operator-ui.md): local operations and first operator UI.

## Purpose

Define the smallest user-facing Web App/PWA feature that lets the primary user operate the daily `tomato_001` monitoring loop and see safe, controlled agent outputs.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): product summary, UX/interaction flow, minimum UI, frontend dependency, acceptance criteria, and UI/e2e verification note.
- [.memory-bank/requirements.md](../requirements.md): REQ-013.
- [.memory-bank/constitution.md](../constitution.md): KISS, bounded agent autonomy, human gate, source-of-truth discipline, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): route map for UI information architecture/PWA flow, UI Feed, safety approval, and lazy sync.
- [.memory-bank/tech-specs/FT-011-minimal-web-app-pwa-operator-surface.md](../tech-specs/FT-011-minimal-web-app-pwa-operator-surface.md): feature-local SDD tech spec for route/view set, daily operator workflow, API consumption, safety display, PWA/offline boundaries, and UI/e2e targets.
- [.memory-bank/testing/index.md](../testing/index.md): UI/e2e smoke and user-visible safety gates.

## Use Cases

- The user opens the local Web App/PWA for `tomato_001`.
- The user answers the daily check-in prompt in chat.
- The user uploads photos and enters manual pH/EC values when available.
- The user views the plant card, day history, photo history, task list, recommendations, and approval prompts.
- The user reads concise agent conclusions and optional controlled spoiler notes.
- The user approves or rejects risky human-performed action proposals.
- The UI shows a 200 MB upload prompt without implying server sync or changing sync status.

## Acceptance Criteria

- The first product surface is a Web App/PWA.
- Minimum UI includes chat, photo upload, plant card, daily check-in, manual pH/EC input, task list, day history, photo history, recommendations, human approval prompt, and controlled spoiler notes.
- The UI can present daily flow state across check-in, photo upload, optional pH/EC handling, agent conclusions, safety review, task/follow-up, and timeline-backed history.
- UI Feed events and `ui_spoiler_note` stay presentation-only and are never passed to agents as working context.
- Controlled spoiler notes do not expose raw chain-of-thought or become confirmed facts.
- Companion responses and UI notes cannot display physical-action instructions without Safety Gate clearance.
- Approval prompts represent human-performed task tracking only, not automated device execution.
- UI/e2e smoke is required once this UI flow exists.

## Edge Cases / Failure Modes

- UI tries to pass UI Feed or spoiler content to agents: fail context-filtering tests.
- UI displays direct physical-action advice before Safety Gate clearance: block display or replace with pending-approval wording.
- UI implies action approval triggers device execution: reject; MVP action tasks are human-performed.
- UI shows raw model reasoning or treats spoiler notes as facts: reject.
- UI upload prompt over 200 MB implies server existence or mutates sync status: reject.
- UI text or state cannot trace back to domain event/state refs where required: fail workflow or integration verification.

## Test Strategy Pointers

- `e2e:daily-ui-smoke` for the critical daily flow once UI exists.
- `integration:ui-feed-presentation` for UI Feed rendering without agent-context leakage.
- `policy:context-filtering` for spoiler notes never entering agent working context.
- `policy:user-visible-action-advice-fail-closed` for Companion and UI physical-action wording.
- `workflow:approval-prompt-human-action` for approved human-performed action tasks without device execution.
- `policy:lazy-sync-200mb-prompt` for prompt-only behavior in the UI.

## Constraints / Invariants

- This is the MVP operator surface, not a landing page or production SaaS UI.
- Keep UI scope to the PRD minimum.
- UI Feed is presentation only.
- Raw reasoning is not user-facing source of truth.
- Safety Gate controls action-implying user-visible text.
- Local-first/private-by-default behavior still applies.

## SDD Design Gate

Feature-local `/spec-improve FT-011` is complete.

Normative feature-local design:

- [.memory-bank/tech-specs/FT-011-minimal-web-app-pwa-operator-surface.md](../tech-specs/FT-011-minimal-web-app-pwa-operator-surface.md): resolves minimal routes/views, daily operator workflow, surface behavior, API dependency map, UI Feed consumption, safety display checks, local auth/LAN considerations, PWA/offline boundaries, and verification targets.

Normative backbone inputs:

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): frontend/backend boundary and daily sequence.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): frontend/backend HTTP boundary.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): presentation-only feed, spoiler notes, and display safety.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): approval prompts and physical-action display checks.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): UI/e2e smoke expectations once UI exists.

No feature-local SDD blocker remains for `/prd-to-tasks FT-011`.
