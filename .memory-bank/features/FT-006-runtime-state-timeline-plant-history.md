---
description: FT-006 Runtime State Timeline And Plant History.
status: active
type: feature
feature_id: FT-006
epic: EP-002
lifecycle: verified
last_updated: 2026-07-11
spec_design_status: complete
spec_design_links:
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/testing/plant-history.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-006 Runtime State Timeline And Plant History

## Use Cases

- Backend persists mutable Plant operational state in PostgreSQL/read model.
- Backend appends audit/export events to `timeline.jsonl`.
- Authorized users view Plant card/history.
- Archived Plants retain authorized history/audit/export access.

## Acceptance Criteria

- PostgreSQL/read model is mutable runtime authority unless later active architecture spec changes it.
- `timeline.jsonl` is append-only audit/export, not primary mutable state.
- Photo files and manifests are local artifacts, not mutable runtime authority.
- Plant history projects implemented operation, measurement, photo, and admin
  evidence from authoritative rows and audit refs.
- Its typed reference boundary may later include tasks, approvals, outcomes,
  agent outputs, and governance records after their owning features implement
  them; those future record families are integration seams, not FT-006 closure
  conditions.

## Edge Cases & Failure Modes

- Timeline replay cannot override runtime state.
- Unauthorized actors cannot access Plant history/audit/export.
- Archived Plant history remains retained but not part of normal operations.
- Export/audit refs cannot include secrets/auth material.

## Verification Targets

- Unit: authority boundary rules for runtime state vs timeline/export.
- Integration: timeline refs resolve back to authoritative runtime records where required.
- API integration: archived Plant retained history remains accessible to an
  authorized Boss without requiring a PWA view.

## Behavior specs

- `.memory-bank/behavior-specs/FT-006-BHV-001-active-history-from-authority.behavior.json`
- `.memory-bank/behavior-specs/FT-006-BHV-002-archived-retained-history.behavior.json`
- `.memory-bank/behavior-specs/FT-006-BHV-003-timeline-replay-not-authority.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): runtime state, timeline, and storage separation.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): authority layers and runtime invariants.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): append-only audit/export event contract.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): Plant trust and promotion boundary for history views.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): authorized history access and redacted errors.

## Feature-Local Design Pressure

- Exact runtime-state ownership, timeline event taxonomy, history projections,
  export refs, retained-history authorization, and retention behavior.

## Specification Composition

Status: complete.

- [Plant History Data](../domains/plant-history.md) defines Plant card/history
  projections, retained-history authorization, source rows, timeline
  consistency, and redaction rules.
- [Plant History HTTP](../contracts/plant-history-http.md) defines protected
  history card/list routes, pagination, response shapes, and errors.
- [Timeline Event](../contracts/timeline-event.md) defines append-only audit/
  export refs and replay limits consumed by FT-006.
- [ActorContext](../contracts/access/actor-context.md) and [Plant And Access Lifecycle](../states/plants/plant-and-access-lifecycle.md)
  define normal-read and retained-history permissions plus archived-Plant
  operational denial.
- [Plant Operations Data](../domains/plant-operations.md), [Photo Artifacts](../domains/photo-artifacts.md),
  and [Admin Audit](../domains/admin/admin-audit.md) define the current source
  rows that FT-006 may project into Plant history.
- [Plant History Verification](../testing/plant-history.md) defines the
  focused evidence matrix.

Raw timeline export packages, PWA history UI, Vision, agents, Safety Gate,
tasks/follow-up, Companion governance, and dataset history entries remain
outside FT-006 until their owning features/specs exist.

Future task, approval, outcome, agent, and governance history families are
extension seams only. FT-006 does not require those records to exist and does
not own their creation or lifecycle.

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-006.md): ordered task queue,
  dependencies, verification strategy, and UAT.

## Implementation Evidence

- `TASK-023-T3-FT-006-W1` is recorded `done` by the scheduler after Plant
  history projection service implementation, an initial verifier/red-verify
  redaction failure, scoped redaction repair, repeat independent `VERDICT:
  PASS`, repeat per-task `SEMANTIC_VERDICT: semantic-pass`, focused Plant
  history tests `5/5`, full regression `220/220`, embedded path redaction probe
  PASS, cursor/source_type probe PASS, `mb-lint` PASS, and `git diff --check`
  PASS.
- Evidence:
  [initial implementation](../../.tasks/TASK-023-T3-FT-006-W1/TASK-023-T3-FT-006-W1-S-IMPL-final-report-code-01.md),
  [repair implementation](../../.tasks/TASK-023-T3-FT-006-W1/TASK-023-T3-FT-006-W1-S-IMPL-final-report-code-02.md),
  [repeat verify](../../.tasks/TASK-023-T3-FT-006-W1/TASK-023-T3-FT-006-W1-S-VERIFY-final-report-code-02.md),
  [repeat red-verify](../../.tasks/TASK-023-T3-FT-006-W1/TASK-023-T3-FT-006-W1-S-RED-VERIFY-final-report-docs-02.md).
- `TASK-024-T3-FT-006-W2` is recorded `done` by the scheduler after protected
  Plant history card/list HTTP implementation, independent `VERDICT: PASS`,
  per-task `SEMANTIC_VERDICT: semantic-pass`, focused API tests `6/6`,
  combined service/API tests `11/11`, full regression `226/226`, HTTP/OpenAPI
  adversarial probe PASS, static source-of-truth scans PASS, `mb-lint` PASS,
  and `git diff --check` PASS.
- Evidence:
  [implementation](../../.tasks/TASK-024-T3-FT-006-W2/TASK-024-T3-FT-006-W2-S-IMPL-final-report-code-01.md),
  [verify](../../.tasks/TASK-024-T3-FT-006-W2/TASK-024-T3-FT-006-W2-S-VERIFY-final-report-code-01.md),
  [red-verify](../../.tasks/TASK-024-T3-FT-006-W2/TASK-024-T3-FT-006-W2-S-RED-VERIFY-final-report-docs-01.md).
- `TASK-027-T3-FT-006-W3` is recorded `done` after strict cursor repair and
  replacement of unstable retry-era URL/path machinery with the controlling
  URL-first/KISS policy. Final independent `VERDICT: PASS`, task-level
  `SEMANTIC_VERDICT: semantic-pass`, focused FT-006 `14/14`, and full
  regression `238/238` are recorded; all earlier retry failures remain in the
  task evidence history.
- Current repair evidence:
  [implementation](../../.tasks/TASK-027-T3-FT-006-W3/TASK-027-T3-FT-006-W3-S-IMPL-final-report-code-09.md),
  [verify](../../.tasks/TASK-027-T3-FT-006-W3/TASK-027-T3-FT-006-W3-S-VERIFY-final-report-code-09.md),
  [red-verify](../../.tasks/TASK-027-T3-FT-006-W3/TASK-027-T3-FT-006-W3-S-RED-VERIFY-final-report-docs-02.md).
- Scheduler waived the missing exact `HUMAN_CHECKPOINT: done` markers for
  TASK-023, TASK-024, and TASK-027 under the advisory T2/T3 process override.
  TASK-027 records that owner decision without fabricating the marker.
- FT-006 is synchronized as `verified` from the current feature-level
  `semantic-pass` report while all historical failure evidence remains intact.

This evidence does not claim raw export packages, PWA UI, Plant operation
writes, photo upload ownership, Vision, agents, Safety Gate, task/follow-up,
Companion, dataset, remote sync, a new persistent history table, or
event-sourcing authority.

## Semantic Verification

SEMANTIC_VERDICT: semantic-pass

- Fresh feature-level adversarial review after `TASK-027-T3-FT-006-W3`
  confirmed that the original malformed-cursor and response privacy findings
  are resolved under the controlling URL-first/KISS contract.
- PostgreSQL/read-model authority, timeline audit/export-only behavior,
  active/archived authorization, strict secret/auth redaction, recursive
  obvious-path handling, safe URL/ref preservation, and cursor canonicality
  passed independent PostgreSQL service and authenticated HTTP probes.
- Current evidence:
  [feature red-verify report 02](../../.tasks/FT-006/FT-006-S-RED-VERIFY-final-report-docs-02.md).
- Historical evidence remains preserved:
  [feature red-verify report 01](../../.tasks/FT-006/FT-006-S-RED-VERIFY-final-report-docs-01.md).
- Ambiguous delimiter-free URL-first values and safe relative refs may remain
  visible by design when stronger local-path discrimination would require
  cumbersome parsing. Obvious paths remain best-effort redaction targets;
  credential/auth/secret redaction remains strict and separate.
- This boundary sync records the owner's `implemented -> verified` lifecycle
  decision; the delegated Reviewer report itself made no lifecycle decision.
