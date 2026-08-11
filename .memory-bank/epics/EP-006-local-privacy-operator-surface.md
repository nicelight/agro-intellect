---
description: EP-006 Local Privacy And Operator Surface.
status: draft
type: epic
epic_id: EP-006
lifecycle: planned
last_updated: 2026-08-12
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# EP-006 Local Privacy And Operator Surface

## Value

Deliver the first usable local Web App/PWA surface while preserving local privacy, dataset trainability guardrails, secret redaction, and prompt-only storage/sync behavior.

## Features

- [FT-014 Dataset Governance And Trainability](../features/FT-014-dataset-governance-trainability.md)
- [FT-015 Local Security Privacy And Storage Prompt](../features/FT-015-local-security-privacy-storage-prompt.md)
- [FT-016 Web App PWA Operator Surface And First Demo](../features/FT-016-web-app-pwa-operator-surface-first-demo.md)

## Success Metrics

- Dataset candidates remain non-trainable by default.
- MVP sync status remains `local_only`.
- Storage prompt appears over 200 MB without implying upload/server availability.
- FT-016 composes the first-demo Boss/Engineer PWA journey over available
  Plant operations, agent, Safety Gate/task, Companion, dataset, and
  timeline/history seams without transferring ownership of those backend
  behaviors into or out of their epics.

## Acceptance Criteria

- Secrets/auth material do not enter logs, timeline, manifests, Bus, UI Feed, screenshots, exports, or agent context.
- LAN mode, if present, is explicitly enabled and protected.
- UI is role-aware and uses backend authorization as authority.
- Web App/PWA owns the visible first-demo composition of Plant selection,
  check-in/photo/history, agent output, safety/task/approval/follow-up,
  Companion, dataset, timeline/export, and storage-prompt surfaces.
- Consultant remains in product scope while first-demo Consultant UI may be deferred.

## Constraints / Invariants

- No hosted cloud sync, server upload semantics, or `server_verified` before a later server-sync stage exists.
- No full dataset registry or real fine-tuning in MVP.
- Web App/PWA is the first product surface.

## Feature-Local Design Pressure

- Exact local storage accounting.
- Exact UI route/view set and PWA/offline boundary.
- Exact LAN/CORS/session control shape.

## FT-014 Implementation Status

- FT-014 is fully implemented: all thirteen indexed tasks are terminal `done`
  (TASK-047 W1; TASK-048, TASK-050/051/052/053, TASK-055 W2; TASK-049 W3;
  TASK-054 W4; TASK-057 W5; W6 remediation TASK-058, TASK-059, TASK-060).
  The ten T3 cards carry per-task `/verify` `PASS` and `/red-verify`
  `semantic-pass`; the W6 T1/T2 cards carry fresh `/verify` `PASS`. The
  feature `lifecycle` is `implemented`; the feature-level T2 completion gate
  recorded `SEMANTIC_VERDICT: semantic-pass`, while feature-level `verified`
  and promotion remain scheduler/owner-owned.
- EP-006 lifecycle stays `planned`; FT-015 and FT-016 remain unexecuted.
