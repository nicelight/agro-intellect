---
description: EP-004 - Local operations and operator UI for the MVP.
status: draft
lifecycle: planned
---
# EP-004 Local Operations and Operator UI

## Value

Keep the MVP local-first, private by default, and operable through the smallest PRD-grounded Web App/PWA surface, without implying production SaaS, server sync, or automated plant control.

## Success metrics

- Backend defaults to loopback binding and explicit protected LAN mode.
- Upload handling rejects unsafe size, MIME/content type, path, and path traversal inputs.
- Secrets do not leak to logs, timeline, manifests, UI Feed, Agent Chat Bus, screenshots, or exports.
- Local photos and manifests remain private unless the user explicitly approves upload/sync.
- `sync.status=local_only` remains the only MVP sync status; the 200 MB prompt does not change sync state.
- The user can run the daily `tomato_001` flow through a local Web App/PWA.

## Acceptance criteria

- Backend binds to loopback by default.
- LAN mode requires explicit enablement and authentication/token protection.
- API CORS uses an allowlist.
- Uploads validate size, MIME/content type, safe paths, and reject path traversal.
- `.env` values, API keys, tokens, and credentials are redacted from logs, `timeline.jsonl`, photo manifests, UI Feed, Agent Chat Bus, screenshots, and export candidates.
- MVP sync status supports `local_only`, and `server_verified` does not appear before a server sync stage exists.
- The first product surface is a Web App/PWA.
- The UI supports the PRD minimum operator surface for chat, check-in, photo upload, pH/EC input, plant state, tasks, history, recommendations, approvals, and controlled spoiler notes.
- UI/e2e smoke is required once the UI flow exists.

## Source artifacts

- [.memory-bank/prd.md](../prd.md): FR-017, local security/privacy non-functional requirements, UX/interaction flow, minimum UI, acceptance criteria, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 6, 21, 23, 24, 28, and 30 for compressed local operations and UI context.
- [.memory-bank/requirements.md](../requirements.md): REQ-012 and REQ-013 with RTM links.
- [.memory-bank/features/FT-010-local-security-privacy-lazy-sync.md](../features/FT-010-local-security-privacy-lazy-sync.md): local security, privacy, and lazy sync.
- [.memory-bank/features/FT-011-minimal-web-app-pwa-operator-surface.md](../features/FT-011-minimal-web-app-pwa-operator-surface.md): minimal Web App/PWA operator surface.

## Normative inputs

- [.memory-bank/constitution.md](../constitution.md): low-maintenance, local-first, KISS, bounded agent autonomy, and human gate for physical actions.
- [.memory-bank/spec-index.md](../spec-index.md): SDD route map for planned local security runbook, candidate lazy sync workflow, UI information architecture/PWA flow, UI Feed, and safety approval specs.
- [.memory-bank/testing/index.md](../testing/index.md): local security, lazy sync, UI/e2e, and user-visible safety gates.

## Constraints / invariants

- The MVP is local-first and private by default.
- Server sync is out of MVP.
- `server_verified` is forbidden before a real server sync stage exists.
- The 200 MB prompt is only a UI prompt and does not mutate sync authority.
- This is an operator surface, not a marketing site, production SaaS frontend, or multi-user system.
- UI Feed is presentation only, and Safety Gate still controls action-implying user-visible text.

## Features included

- [FT-010 Local Security, Privacy, and Lazy Sync](../features/FT-010-local-security-privacy-lazy-sync.md): loopback/LAN baseline, CORS allowlist, upload validation, path traversal rejection, secret redaction, private-by-default artifacts, `local_only`, and 200 MB prompt boundary.
- [FT-011 Minimal Web App/PWA Operator Surface](../features/FT-011-minimal-web-app-pwa-operator-surface.md): daily operator surface for chat, intake, state display, recommendations, approvals, history, tasks, and controlled spoiler notes.
