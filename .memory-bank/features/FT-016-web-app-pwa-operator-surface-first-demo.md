---
description: FT-016 Web App PWA Operator Surface And First Demo.
status: draft
type: feature
feature_id: FT-016
epic: EP-006
lifecycle: planned
last_updated: 2026-08-14
spec_design_status: complete
spec_design_links:
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/contracts/operator-pwa.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/auth/session-http.md
  - .memory-bank/contracts/admin/boss-admin-http.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/contracts/plant-operations-http.md
  - .memory-bank/contracts/photo-intake-http.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/plant-state-http.md
  - .memory-bank/contracts/task-approval-http.md
  - .memory-bank/contracts/companion-governance-http.md
  - .memory-bank/contracts/dataset-governance-http.md
  - .memory-bank/contracts/product-surface-redaction.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/task-follow-up-lifecycle.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/testing/local-privacy-storage.md
  - .memory-bank/testing/operator-pwa-first-demo.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
---
# FT-016 Web App PWA Operator Surface And First Demo

## Use Cases

- Boss uses a role-aware local Web App/PWA surface to set up or use the Farm workspace, create/manage Engineer access, and see admin audit.
- Engineer uses the PWA to select authorized Plant, run daily check-in, upload photo, record pH/EC, see agent outputs, handle tasks/approvals, and record follow-up.
- User sees Safety Gate blocks/prompts, Companion HumanAttentionNeeded/proposal/decision path, dataset/local storage status, the FT-015 storage prompt, and Plant history.
- Consultant UI/path may be deferred from first demo while Consultant remains in product scope.

## Acceptance Criteria

### FT-016-AC-001 — Required frontend stack

- REQ: REQ-021
- Frontend implementation uses Svelte 5 Runes with TypeScript and SvelteKit;
  alternative or mixed-framework implementations do not satisfy FT-016.
- Verification: frontend dependency/configuration inspection plus applicable
  check/build commands prove one Svelte 5/SvelteKit stack.

### FT-016-AC-002 — Boss and Engineer first-demo paths

- REQ: REQ-021
- First demo includes Boss and at least one Engineer path on `tomato_001`.
- Verification: browser journey covers both actors and the authorized initial
  Plant path.

### FT-016-AC-003 — Required first-demo composition

- REQ: REQ-021
- First demo includes Plant selector access checks, daily check-in, photo
  upload with file/catalog/sha256/manifest refs, manual pH/EC,
  provider-neutral product-agent and Vision Observation boundaries over actual
  scoped photo/measurement/observation data, Plant State trust statuses,
  Hydroponics Advisor missing-data behavior, Task & Follow-up behavior, Safety
  Gate behavior, Companion HumanAttentionNeeded/proposal/decision path,
  dataset fields, timeline audit/export, and the FT-015 local storage prompt.
  Deterministic fake/spy executors remain test-only; unbound production fails
  closed without fake/canned output, and real endpoint behavior is not claimed
  by this feature. FT-016 renders and composes the prompt but does not own photo
  accounting, status, or sync authority.
- Verification: first-demo browser/integration composition exercises every
  named surface over authorized backend projections, consumes the FT-015
  status/interaction contract, and proves no production fake/fallback path.

### FT-016-AC-004 — Role-aware presentation

- REQ: REQ-003, REQ-004, REQ-021
- UI remains role-aware and presentation-only; frontend visibility never
  replaces backend authorization.
- Verification: authorized, unauthorized, and archived-Plant browser paths
  agree with backend access results.

### FT-016-AC-005 — No UI authority or agent-context promotion

- REQ: REQ-013, REQ-021
- UI does not become backend authority or agent working context.
- Verification: request/context inspection proves rendered UI content and
  transient prompt state are absent from authority and agent-input channels.

### FT-016-AC-006 — Literal inert model text

- REQ: REQ-013, REQ-021
- Authorized/classified model text is shown literally through escaped/text-node
  rendering; markup-, prompt-, command-, and URL-looking sequences remain inert
  text with no HTML/Markdown interpretation or action activation.
- Verification: representative browser cases create no active element, link,
  command, or action side effect.

### FT-016-AC-007 — FT-015 storage-prompt consumer

- REQ: REQ-021
- The PWA consumes the exact protected FT-015 storage status and shows the
  prompt only from `prompt_eligible=true`. `acknowledge` and `dismiss` close
  only the current component instance, persist nothing, reset on fresh
  page/status load or Account/auth change, and cannot change photo accounting,
  upload, server availability, or `local_only` sync authority.
- Verification: browser checks cover both actions, fresh-load reappearance,
  Account switching, exact returned status use, no browser/backend persistence
  or mutation request, and no server/upload implication.

### FT-016-AC-008 — Browser-capture redaction

- REQ: REQ-020, REQ-021
- FT-016 adds no product screenshot feature. Every Playwright screenshot,
  trace, video, DOM snapshot, or other browser artifact is created only through
  the registered safe capture helper after forbidden secret/auth values are
  sanitized or omitted; source credential fixtures remain unchanged.
- Verification: the configured corpus crosses actual allowed UI/error paths,
  no capture contains a raw value, safe failure exposes only a stable error,
  and direct capture calls outside the helper are absent.

### FT-016-AC-009 — Read-only Dataset Governance provider

- REQ: REQ-021
- Dataset Governance exposes one protected Plant-scoped paginated read
  projection for the PWA. It copies authoritative candidate/evidence/
  trainability fields, performs no mutation, and exposes no review,
  transition, split, evidence, curator, or `can_train_on` command.
- Verification: API/OpenAPI, authorization, active/retained-history,
  pagination, exact-field, safe-failure, and mutation-route absence checks.

### FT-016-AC-010 — Presentation-only Dataset consumer

- REQ: REQ-021
- The PWA renders Dataset Governance response values without setting,
  inferring, or promoting status, evidence, split, confirmation,
  `curator_decision`, or `can_train_on`; UI Feed, photo, manifest, Timeline,
  and local UI state never become trainability authority.
- Verification: browser/request inspection compares rendered authority values
  with the protected response and proves zero Dataset mutation request.

### FT-016-AC-011 — Server-only browser transport privacy

- REQ: REQ-020, REQ-021
- The fixed-loopback SvelteKit backend client keeps session tokens, raw
  cookies, authorization headers, backend origin, and provider credentials out
  of browser page data, logs, safe errors, and capture inputs.
- Verification: login/logout and safe-error browser probes plus source
  inspection prove server-only forwarding, `no-store`, and absence of every
  configured auth/secret value from browser-visible transport state.

### FT-016-AC-012 — Direct Engineer provisioning

- REQ: REQ-020, REQ-021
- A Boss can create the demo Engineer through Boss Admin HTTP; password input
  remains write-only and the created Engineer can authenticate without any
  password/auth material returning to browser state or evidence.
- Verification: isolated Boss creation and Engineer-login browser/API evidence
  proves exact safe response fields, non-Boss denial, and password exclusion.

### FT-016-AC-013 — Membership role assignment

- REQ: REQ-021
- A Boss can assign the accepted membership role through the registered role
  action; the PWA neither invents roles nor changes last-Boss protection.
- Verification: authorized role change, invalid/non-Boss/last-Boss rejection,
  and authoritative reread are independently exercised.

### FT-016-AC-014 — Plant lifecycle administration

- REQ: REQ-021
- A Boss can use the registered Plant list/create/rename/archive/restore
  lifecycle from `/admin`, with backend status and no-op/conflict results
  remaining authoritative.
- Verification: lifecycle browser/API evidence covers successful transitions,
  safe retry/conflict behavior, and non-Boss denial without grant mutation.

### FT-016-AC-015 — Plant access grants

- REQ: REQ-004, REQ-021
- A Boss can list, create/update, and revoke an Engineer Plant access grant and
  its approval flag only through Plant Management HTTP; the PWA derives no
  permission and grants no Consultant approval authority.
- Verification: grant lifecycle, role/approval constraints, archived-Plant
  administration, and resulting Engineer selector access are exercised.

### FT-016-AC-016 — Admin audit presentation

- REQ: REQ-021
- A Boss can read the safe paginated admin audit projection; non-Boss users
  cannot access it and browser presentation adds no audit record or authority.
- Verification: filtered/cursor continuation, safe fields, non-Boss denial,
  and no presentation-origin write are independently proved.

### FT-016-AC-017 — Daily check-in and observation

- REQ: REQ-021
- An authorized Boss or Engineer can load the check-in prompt and submit the
  exact daily check-in/observation shape for the selected active Plant.
- Verification: success plus empty/text-length/permission/archive failures
  prove backend validation and unchanged state on rejection.

### FT-016-AC-018 — Manual pH/EC measurement

- REQ: REQ-021
- An authorized Boss or Engineer can submit standalone manual pH/EC and view
  the authoritative normalized measurement/freshness result.
- Verification: pH/EC range, normalization, freshness, permission, and archive
  browser/API cases are independently exercised.

### FT-016-AC-019 — Local photo upload

- REQ: REQ-021
- An authorized Engineer can submit one accepted multipart local photo through
  Photo Intake HTTP and receive its safe checksum/manifest/event refs without
  a filesystem path or remote-upload implication.
- Verification: real test-file success and unsupported, oversized,
  unauthorized, and archived failures prove no partially accepted artifact.

### FT-016-AC-020 — Photo catalog presentation

- REQ: REQ-021
- An authorized active-Plant user can read the stable paginated photo catalog
  and see exact safe local-only fields without filesystem scanning or Dataset
  trainability inference.
- Verification: catalog/detail response comparison, continuation, wrong-Plant
  and malformed-cursor denial, and zero mutation request are exercised.

### FT-016-AC-021 — Plant card presentation

- REQ: REQ-021
- The selected-Plant workspace renders the authoritative Plant history card,
  including current refs, measurement freshness, counts, permissions, and
  retained-history mode, without direct Timeline or storage access.
- Verification: active and archived-authorized card responses match the DOM;
  unauthorized and inconsistent-source cases fail safely.

### FT-016-AC-022 — Paginated retained Plant history

- REQ: REQ-021
- Authorized users can traverse the complete stable Plant history projection,
  including archived retained history and safe audit/export refs, without a
  Timeline replay or write edge.
- Verification: multi-page continuation, source filtering, retained-history
  authorization, cursor failures, and mutation absence are exercised.

### FT-016-AC-023 — Plant State trust-record list

- REQ: REQ-021
- Authorized users can read the paginated Plant State trust-record projection
  with exact public fields and retained-history behavior but no provider,
  confirmation-actor, or internal-classification leakage.
- Verification: list continuation, active/retained access, wrong-Plant cursor,
  safe-field, and denial cases are independently exercised.

### FT-016-AC-024 — Plant State human review

- REQ: REQ-021, REQ-022
- An authorized Boss or Engineer can submit only `decision` and
  `expected_version` for explicit confirm/reject review; Consultant,
  read-only, archived, stale, and unresolved-conflict paths do not mutate trust.
- Verification: successful review plus version/conflict/role/archive denial
  compares the post-request authoritative record.

### FT-016-AC-025 — Task and Approval reads

- REQ: REQ-021
- Authorized users can read the exact Task and Approval projections for the
  selected Plant; retained/read-only presentation exposes no mutation or
  arbitrary Task-creation capability.
- Verification: task/approval filters and fields, role/archive behavior,
  canonical request paths, and zero write request are exercised.

### FT-016-AC-026 — Human Safety approval

- REQ: REQ-021, REQ-022
- An authorized current approver can submit the exact human Safety decision;
  the PWA cannot infer clearance, extend expiry, or approve for Consultant,
  denied, stale, or archived scope.
- Verification: authorized approve/reject and permission/freshness/version/
  archive failures prove unchanged backend state on rejection.

### FT-016-AC-027 — Task completion

- REQ: REQ-021, REQ-022
- An authorized Boss or Engineer can complete only an existing eligible Task
  through the registered command; the PWA cannot edit its kind/text, create
  arbitrary work, or execute a device.
- Verification: successful completion, duplicate/conflict/permission/archive
  behavior, and absence of arbitrary Task/device requests are exercised.

### FT-016-AC-028 — Follow-up Outcome recording

- REQ: REQ-021, REQ-022
- An authorized Boss or Engineer can record the exact follow-up Outcome and
  evidence refs for an eligible completed Task without deriving attribution,
  Dataset state, or follow-up authority in the PWA.
- Verification: success, evidence/transition/version/permission/archive
  failures, authoritative reread, and retry behavior are exercised.

### FT-016-AC-029 — Companion IssueStack and detail reads

- REQ: REQ-021
- Authorized users can read exact Companion IssueStack/detail, attention,
  proposals, DecisionRecords, and conclusion projections; retained archived
  reads expose no command capability and all text remains presentation data.
- Verification: list/detail ordering, continuation, retained access, strict
  shapes, safe text, and denial cases are independently exercised.

### FT-016-AC-030 — Explicit Companion invocation

- REQ: REQ-021, REQ-022
- An authorized Boss or Engineer can invoke Companion only through the exact
  provider-neutral run command; refresh/GET/UI text never triggers it and an
  unbound production runtime fails without fake fallback.
- Verification: explicit success/duplicate/non-governable paths, zero-call
  GET/refresh, role/archive denial, and unbound no-network failure are proved.

### FT-016-AC-031 — Companion proposal decision

- REQ: REQ-021, REQ-022
- An authorized Boss or Engineer can approve/reject only the current proposal
  through its versioned command; the PWA cannot replace the effect, convert
  governance approval into Safety approval, or accept superseded state.
- Verification: approve/reject, duplicate, superseded/version/role/archive
  failures, and authoritative DecisionRecord/Task effects are exercised.

### FT-016-AC-032 — Companion issue close

- REQ: REQ-021, REQ-022
- An authorized Boss or Engineer can close only a current resolved Companion
  issue through the versioned close command; no reopen or client-derived
  resolution path is introduced.
- Verification: close/duplicate plus open/version/permission/archive failures
  prove the exact issue state and absence of unauthorized effects.

## Edge Cases & Failure Modes

- Unauthorized UI state cannot reveal or mutate Plant data. Covered by
  FT-016-AC-004.
- Frontend hide/show cannot replace backend authorization. Covered by
  FT-016-AC-004.
- UI markdown/cards/spoiler notes/admin notices cannot become agent facts.
  Covered by FT-016-AC-005.
- Candidate text cannot create active markup/links/actions or be copied into
  agent instruction/runtime-authority channels. Covered by FT-016-AC-005 and
  FT-016-AC-006.
- Prompt actions cannot survive a fresh load or Account/auth change and cannot
  create storage/sync authority. Covered by FT-016-AC-007.
- Browser evidence cannot capture forbidden auth/secret material. Covered by
  FT-016-AC-008 and FT-016-AC-011.
- Dataset display cannot become review or trainability authority. Covered by
  FT-016-AC-009 and FT-016-AC-010.
- Independently failing provider reads and commands retain separate acceptance
  and proof ownership. Covered by FT-016-AC-012 through FT-016-AC-032.
- Advanced Boss Admin Surface, full role matrix, sync UI beyond the required
  FT-015 prompt, sensor runtime, and Consultant UI/path are out of FT-016's
  first-demo acceptance where allowed by the PRD.
  Disposition: out_of_scope. Source: `.memory-bank/prd.md`. Change route:
  `/write-prd`.

## Verification Targets

- E2E: Boss setup plus Engineer authorized Plant workflow.
- E2E: Safety Gate and Companion governance visible without unsafe authority mixing.
- E2E: unauthorized/archived Plant visibility checks.
- UI smoke: FT-015 storage prompt consumption, transient per-Account
  acknowledge/dismiss behavior, fresh-load reappearance, and role-aware
  navigation without frontend storage/sync authority.
- UI security smoke: representative HTML/Markdown/prompt-/URL-looking candidate
  text renders literally and triggers no link, command, or action behavior.
- Browser security: configured secret/auth corpus is absent from registered
  screenshots, traces, videos, and DOM snapshots.
- API/browser integration: protected Dataset Candidate read is exact and the
  UI emits no Dataset mutation.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Operator PWA module and first-demo data flow.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): frontend/backend authorization boundary.
- [.memory-bank/contracts/product-surface-redaction.md](../contracts/product-surface-redaction.md): mandatory pre-capture redaction for future browser/screenshot artifacts.
- [.memory-bank/contracts/operator-pwa.md](../contracts/operator-pwa.md): exact route/view, server transport, provider-surface, transient prompt, context-isolation, and capture behavior.
- [.memory-bank/contracts/photo-intake-http.md](../contracts/photo-intake-http.md#storage-status-behavior): protected FT-015 storage-status response consumed without frontend storage or sync authority.
- [.memory-bank/contracts/dataset-governance-http.md](../contracts/dataset-governance-http.md): protected read-only Dataset Candidate projection.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md) and [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): UI Feed projection and context hygiene boundaries.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): human-facing presentation boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs shown in history.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md), [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md), [.memory-bank/states/companion-governance.md](../states/companion-governance.md), and [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): first-demo state surfaces.
- [.memory-bank/testing/operator-pwa-first-demo.md](../testing/operator-pwa-first-demo.md): deterministic browser, capture, and first-demo verification matrix.

## Feature-Local Design Pressure

- The route set is fixed to `/login`, `/admin`, and
  `/plants/[plant_id]`; the Plant workspace composes provider-owned sections
  without route-per-component expansion.
- Initial loads use SvelteKit server `load`, mutations use server actions, and
  one fixed loopback server-only client keeps cookies/tokens/backend origin out
  of browser page data without adding CORS or LAN mode.
- FT-016 consumes the FT-015 protected storage-status and interaction contract;
  it owns only the Svelte component, transient Account-isolated client state,
  and browser/first-demo composition.
- Dataset Governance owns the new read projection and all mutable Dataset
  authority; Operator PWA owns only its presentation consumer.

## SDD Design Gate

- Global/shared status: complete; AD-004, AD-009, AD-012, MessageEnvelope, UI Feed,
  Agent Chat Bus, Safety Action Lifecycle, and the Svelte 5 project rules define
  the SvelteKit/PWA stack, opaque candidate data, literal presentation, no
  instruction-channel promotion, and unchanged authority boundaries.
- Feature-local status: complete through Operator PWA, Dataset Governance HTTP,
  Boundary Map, Product Surface Redaction, backend provider contracts, and
  Operator PWA First-Demo Verification. The rebuilt atomic queue is recorded
  in [IMPL-FT-016](../tasks/plans/IMPL-FT-016.md) for Planning Revision 4 and
  awaits fresh `/review-tasks-plan FT-016`.
