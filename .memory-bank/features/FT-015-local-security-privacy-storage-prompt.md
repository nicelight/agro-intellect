---
description: FT-015 Local Security Privacy And Storage Prompt.
status: draft
type: feature
feature_id: FT-015
epic: EP-006
lifecycle: planned
last_updated: 2026-08-13
clarification_status: complete
last_clarified: 2026-08-12
clarification_questions: 4
spec_design_status: complete
spec_design_links:
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/architecture/foundation-runtime-substrate.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/contracts/auth/session-http.md
  - .memory-bank/contracts/product-surface-redaction.md
  - .memory-bank/contracts/photo-intake-http.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/vision-observation-runtime.md
  - .memory-bank/contracts/plant-state-runtime.md
  - .memory-bank/contracts/hydroponics-advisor-runtime.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/contracts/task-follow-up-runtime.md
  - .memory-bank/contracts/companion-runtime.md
  - .memory-bank/contracts/dataset-agents-runtime.md
  - .memory-bank/testing/local-privacy-storage.md
  - .memory-bank/runbooks/foundation-local-runtime.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-015 Local Security Privacy And Storage Prompt

## Use Cases

- App runs local-first and private by default.
- Default backend exposure is loopback.
- Optional LAN mode, if present, is explicitly enabled and protected.
- Accepted local photo originals occupy more than 200 MiB and the UI shows a
  prompt without upload/server implication.
- Each Account has independent transient storage-prompt interaction state; one
  Account's action does not suppress or change the prompt for another Account.
- Logs, exports, screenshots, Bus, UI Feed, manifests, and agent context redact auth material.

## Acceptance Criteria

### FT-015-AC-001 — Local-only sync authority

- REQ: REQ-020
- MVP sync status remains `local_only`; `server_verified` and server upload
  semantics are forbidden until a later server-sync stage exists.
- Verification: status/configuration checks reject every non-`local_only` MVP
  value and prove prompt actions cannot mutate sync authority.

### FT-015-AC-002 — Protected local exposure

- REQ: REQ-020
- Default backend exposure is loopback. LAN mode, if implemented, requires
  explicit enablement, authentication, authorization, session/token
  protection, and CORS/origin controls without weakening local auth/authz.
- Verification: configuration and protected-route checks cover loopback
  default, explicit LAN enablement, authentication, and allowed origins.

### FT-015-AC-003 — Runtime log and API-error redaction

- REQ: REQ-020
- Secrets, sessions, tokens, credentials, `.env` values, API keys, and auth
  material do not enter application logs or safe API errors.
- Verification: the configured secret corpus is exercised through actual log
  and error serialization; raw values are absent and failures expose only the
  registered safe error.

### FT-015-AC-004 — Storage-prompt responsibility boundary

- REQ: REQ-020, REQ-021
- FT-015 owns storage-pressure accounting, the protected status contract,
  prompt eligibility and interaction semantics, and deterministic backend
  verification. FT-016 owns only the Svelte/PWA component, transient client
  state, and browser/first-demo composition; it consumes FT-015 behavior and
  does not redefine storage accounting or sync authority.
- Verification: decomposition/source-scope review and consumer-contract checks
  prove one FT-015 accounting/status owner and no duplicate FT-016 authority.

### FT-015-AC-005 — Photo-only pressure threshold

- REQ: REQ-020
- Prompt eligibility is Farm-wide and becomes true only when the sum of
  `size_bytes` for accepted original photo binaries is strictly greater than
  `209715200` bytes (200 MiB). Each accepted photo is counted once from its
  authoritative Photo Catalog row; manifests, PostgreSQL storage, Timeline,
  logs, caches, temporary/failed/orphan files, screenshots, application
  assets, derived/export artifacts, and Dataset Candidate refs are excluded.
- Verification: aggregation checks cover below, exact, and above-threshold
  totals, one count per accepted Photo Catalog item, and every named exclusion.

### FT-015-AC-006 — Per-Account interaction isolation

- REQ: REQ-020
- `acknowledge` and `dismiss` both close only the current rendered prompt for
  the authenticated Account. Neither action writes backend state; the prompt
  may appear again on the next page load or fresh status load while photo
  pressure remains over threshold. Client state is discarded on Account/auth
  change, and one Account's action cannot affect another Account.
- Verification: browser/consumer checks cover both actions, fresh-load
  reappearance, Account switching, absence of a prompt-mutation write, and
  unchanged `local_only` status.

### FT-015-AC-007 — Photo-manifest redaction

- REQ: REQ-020
- Secrets, sessions, tokens, credentials, `.env` values, API keys, and auth
  material do not enter accepted or failed photo-manifest output.
- Verification: actual manifest serialization removes or rejects the
  configured corpus before the atomic write while preserving the source
  credential value used by its owner.

### FT-015-AC-008 — Timeline append redaction

- REQ: REQ-020
- The forbidden secret/auth corpus does not enter Timeline append output.
- Verification: the registered Timeline append writer is exercised with the
  configured corpus; raw values are absent and uncertain output fails closed
  without leaking the rejected value.

### FT-015-AC-009 — Bus and UI Feed redaction

- REQ: REQ-020
- The forbidden secret/auth corpus does not enter Agent Chat Bus or UI Feed
  persistence/serialization.
- Verification: actual typed Bus/UI publication paths redact or reject the
  configured corpus before persistence and preserve agent-consumability
  isolation.

### FT-015-AC-010 — Generic Agent Runtime context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, and provider history do not enter generic `ProviderRequestV1`.
- Verification: the generic Agent Runtime assembler and provider-boundary spy
  prove the strict allowlist and absence of every forbidden value.

### FT-015-AC-011 — Browser-capture redaction boundary

- REQ: REQ-020, REQ-021
- FT-015 creates no competing frontend or screenshot path. The current tree has
  no browser capture surface; FT-016 MUST apply Product Surface Redaction before
  any screenshot/browser artifact is captured.
- Verification: current source/dependency inspection proves the surface is
  absent, and the FT-016 consumer contract retains the canonical redaction spec
  as a required input.

### FT-015-AC-012 — Retained-history and export redaction

- REQ: REQ-020
- The forbidden secret/auth corpus does not enter Plant History or retained-
  history/export serialization.
- Verification: the actual Plant History/export serializer is exercised with
  the configured corpus; raw values are absent and uncertain output fails
  closed without leaking the rejected value.

### FT-015-AC-013 — Vision Observation context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, provider history, and unregistered metadata do not enter
  `VisionProviderRequestV1` or its verified media handoff.
- Verification: the Vision assembler and provider/media spy prove the exact
  request allowlist, media identity, and absence of every forbidden value.

### FT-015-AC-014 — Plant State context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, provider history, and unregistered metadata do not enter
  `PlantStateProviderRequestV1`.
- Verification: the Plant State assembler and provider spy prove the strict
  request allowlist and absence of every forbidden value.

### FT-015-AC-015 — Hydroponics Advisor context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, provider history, and unregistered metadata do not enter
  `HydroponicsAdvisorProviderRequestV1`.
- Verification: the Advisor assembler and provider spy prove the strict
  request allowlist and absence of every forbidden value.

### FT-015-AC-016 — Safety Gate context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, provider history, and unregistered metadata do not enter
  `SafetyGateProviderRequestV1`.
- Verification: the Safety Gate assembler and provider spy prove the strict
  request allowlist and absence of every forbidden value.

### FT-015-AC-017 — Task and Follow-Up context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, provider history, and unregistered metadata do not enter
  `TaskFollowUpProviderRequestV1`.
- Verification: the Task and Follow-Up assembler and provider spy prove the
  strict request allowlist and absence of every forbidden value.

### FT-015-AC-018 — Companion context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, provider history, and unregistered governance metadata do not enter
  `CompanionProviderRequestV1`; its registered typed governance subset remains
  untrusted and non-authoritative.
- Verification: the Companion assembler and provider spy prove the strict
  request allowlist, the allowed typed subset, and absence of every forbidden
  value.

### FT-015-AC-019 — Dataset Agents context redaction

- REQ: REQ-020
- The forbidden secret/auth corpus, raw ActorContext, cookies, headers, UI
  content, provider history, and unregistered metadata do not enter
  `DatasetGovernanceProviderRequestV1` or
  `TrainingDataCuratorProviderRequestV1`.
- Verification: both thin adapters are exercised through their shared Dataset
  Agent runtime flow and provider spies; each strict request contains no
  forbidden value and retains no MessageEnvelope/Bus/UI/Safety authority.

## Edge Cases & Failure Modes

- Storage prompt cannot imply upload, server availability, or sync status
  change. Covered by FT-015-AC-001 and FT-015-AC-006.
- Exactly `209715200` counted bytes is not over the threshold and does not make
  the prompt eligible. Covered by FT-015-AC-005.
- Manifest growth and duplicate Dataset Candidate refs cannot make the prompt
  eligible because only accepted original photo bytes are counted. Covered by
  FT-015-AC-005.
- Acknowledge/dismiss by one Account cannot suppress the prompt for another.
  Covered by FT-015-AC-006.
- Acknowledge/dismiss creates no durable preference, cooldown, storage episode,
  growth-delta tracker, Timeline event, upload approval, or sync mutation.
  Covered by FT-015-AC-001 and FT-015-AC-006.
- LAN mode cannot weaken local auth/authz. Covered by FT-015-AC-002.
- Secret redaction applies to errors, logs, audit/export, UI, and agent context.
  Covered by FT-015-AC-003 and FT-015-AC-007 through FT-015-AC-019.
- Local artifact privacy is default; upload/sync is not an MVP requirement.
  Covered by FT-015-AC-001 and FT-015-AC-003.

## Verification Targets

- Unit: shared redaction primitives, independently owned output/request
  serializers, and photo-only threshold calculation at below, exact, and
  above-threshold boundaries.
- Integration: loopback default, LAN controls if implemented, `local_only` status.
- Integration: the protected status contract returns photo pressure without a
  prompt-mutation endpoint or durable acknowledgment state.
- E2E: the FT-015 prompt appears only over 200 MiB of accepted original photos
  and uses no upload/server wording; acknowledge/dismiss closes only the
  current Account's rendered instance, reload may show it again, Account
  switching does not leak state, and FT-016 owns this browser composition.

## Clarifications

### 2026-08-12 — Ownership, photo accounting, and Account scope

- The operator assigned the complete storage-prompt capability to FT-015.
  Under the accepted KISS split, FT-015 owns its policy, accounting, protected
  status contract, and interaction semantics; FT-016 owns only the mechanical
  Svelte/PWA rendering and browser composition.
- Storage pressure counts only accepted original photo binaries, once per
  authoritative Photo Catalog row, and becomes eligible strictly above 200
  MiB. Non-photo and non-authoritative storage is excluded.
- Prompt interaction state is independent for each Account. Both acknowledge
  and dismiss simply close the current rendered instance, persist nothing,
  and may reappear after reload while pressure remains over threshold.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): local privacy, deployment, and security constraints.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): loopback/LAN, CORS, authz, upload, and redacted errors.
- [.memory-bank/contracts/product-surface-redaction.md](../contracts/product-surface-redaction.md): shared product-output redaction rule and owner-preserving fail-closed boundary.
- [.memory-bank/contracts/photo-intake-http.md](../contracts/photo-intake-http.md#storage-status-behavior): protected authoritative storage-status handoff consumed by FT-016.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): local artifact and sync-status authority.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): local artifact privacy and `local_only` evidence refs.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): storage prompt projection without agent-context leakage.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): redacted audit/export surface.

## Canonical SDD Disposition

- `reuse` —
  [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md),
  [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md),
  [.memory-bank/contracts/auth/session-security.md](../contracts/auth/session-security.md),
  and
  [.memory-bank/runbooks/foundation-local-runtime.md](../runbooks/foundation-local-runtime.md)
  define the supported loopback runtime and controls required if a future LAN
  capability is introduced.
- `not_applicable` — LAN implementation in FT-015: the PRD makes LAN optional,
  it is not required for the first demo, and the current supported runtime has
  no LAN/CORS/bearer mode. FT-015 proves the loopback path and does not add an
  optional exposure capability.
- `extend` —
  [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md)
  owns fail-closed `local_only` settings validation.
- `extend` —
  [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md#farm-photo-storage-pressure)
  owns the exact authoritative aggregation and threshold.
- `extend` —
  [.memory-bank/contracts/photo-intake-http.md](../contracts/photo-intake-http.md#storage-status-behavior)
  owns the protected status shape, auth/error behavior, and stateless consumer
  handoff.
- `create` —
  [.memory-bank/contracts/product-surface-redaction.md](../contracts/product-surface-redaction.md)
  closes the product runtime redaction concern that the Foundation-only
  evidence contract explicitly did not own.
- `create` —
  [.memory-bank/testing/local-privacy-storage.md](../testing/local-privacy-storage.md)
  owns deterministic verification across runtime, storage, consumer, and
  redaction boundaries.
- `reuse` —
  [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md) and AD-009 retain
  presentation/context isolation and FT-016 Svelte/PWA ownership. No behavior
  example is needed because the exact threshold and interaction matrices are
  already canonical.

## Feature-Local Design Pressure

- FT-015 owns storage-prompt policy, accounting, protected status
  contract, and interaction semantics. FT-016 owns the Svelte/PWA component,
  transient client state, and browser/first-demo composition.
- Farm-wide pressure is the authoritative sum of accepted original
  photo `size_bytes`, counted once and compared strictly as
  `> 209715200`; all other storage categories are excluded.
- Prompt interaction state is transient and per Account;
  acknowledge and dismiss both close only the current rendered instance and
  persist nothing. This intentionally gives them no separate lifecycle.
- Feature-local design is complete: the registered data, HTTP, redaction, and
  verification specs define the exact backend handoff; AD-009 and FT-016
  frontend ownership remain unchanged.

## SDD Design Gate

- Global Backbone is `complete` at Planning Revision 4 and Foundation final
  gate `TASK-004-T2-FT-000-W0` is terminal `done`.
- Feature-local design is complete through the registered Foundation data,
  Photo Artifacts, Photo Intake HTTP, Product Surface Redaction, Boundary Map,
  and Local Privacy verification specs.
- [IMPL-FT-015](../tasks/plans/IMPL-FT-015.md) and indexed TASK-062 through
  TASK-079 are reconciled to Planning Revision 4. TASK-062 through TASK-070
  preserve their existing identities and `planned` lifecycle; the corrected
  execution-cohesive owner boundaries are ready for fresh task-plan review.

## Semantic Verification

Feature-completion semantic gate `/red-verify --feature FT-015` (2026-08-17).
All 18 cards implemented (TASK-062 through TASK-079); every T3 card holds
per-task `semantic-pass` and both T2 cards hold functional `PASS`. Feature-wide
adversarial probe covered redaction uniformity (shared `redact_text` applied
unconditionally on every surface, no `if secret_values` composition-dependent
skip; default compositions still redact env/auth material), source-of-truth
(PostgreSQL projection authority preserved, no filesystem fallback, no
sanitizer-gained authority), boundary/contract integrity (exact
`PhotoStorageStatus` 5-field no-store shape, manifest/Timeline registry,
Bus/UI consumability flags, `ProviderRequestV1` allowlists, typed governance
subset, advisory-only Dataset agents), AC-001..019 owner coverage with no
orphan/duplicate claims, AC-011 browser-capture handoff documented to FT-016,
and Constitution fit (privacy by default, security boundaries, low
maintenance, no speculation). Documented non-admissions are the shared
`_redactable_value` length<3 filter and bare non-env literal values under the
default composition (uniform shared baseline, accepted in TASK-070/075/076),
and the TASK-067 operator-restricted corpus reading for bare DSN substrings in
`X-Request-ID`. No material break of an accepted outcome and no operator
question required.

Report: `.tasks/FT-015/FT-015-S-RED-VERIFY-final-report-docs-01.md`.

SEMANTIC_VERDICT: semantic-pass
