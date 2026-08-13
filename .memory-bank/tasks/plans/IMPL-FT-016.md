---
description: Implementation plan for the FT-016 SvelteKit Operator PWA and first-demo composition.
status: active
last_updated: 2026-08-14
feature: FT-016
planning_revision: 4
---
# IMPL-FT-016 — Operator PWA And First Demo

## Goal

Deliver the first local Boss/Engineer SvelteKit PWA as a presentation consumer
over the registered backend boundaries. Consume FT-015 storage status,
transient prompt semantics, and capture redaction without transferring photo,
storage, sync, authorization, agent-context, Safety, governance, Dataset,
Timeline, or other mutable authority into the frontend.

## Scope

- one Svelte 5 Runes/TypeScript/SvelteKit PWA under `frontend/`;
- `/login`, `/admin`, and `/plants/[plant_id]` route families;
- fixed-loopback server-only backend transport through SvelteKit loads/actions;
- Boss, Engineer, Plant operations/photo/history/feed/state/task/Companion,
  read-only Dataset, and FT-015 prompt surfaces;
- literal text, UI-context isolation, browser-capture redaction, and one
  reproducible first-demo browser journey;
- one Dataset-Governance-owned protected read-only HTTP projection.

## Non-goals

- Consultant first-demo UI, additional route families, broad dashboard/design
  system, mobile wrapper, LAN/CORS mode, hosted/cloud deployment, server sync,
  offline mutation/background sync, protected-response caching, or production
  screenshot feature;
- backend authorization/domain rewrites, public generic agent invocation,
  external provider selection/live smoke, Dataset mutation/review/trainability
  control, raw HTML/Markdown execution, or automated physical actuation.

## Capability ownership

- **Operator PWA**, code root `frontend/`, owns SvelteKit presentation,
  component-local interaction state, safe server transport, and browser proof.
- **Dataset Governance**, code root `backend/app/dataset_governance/` with
  `backend/app/api/`, owns the read projection and all candidate authority.
- Crossed public boundaries are exactly the Operator PWA edges registered in
  [Boundary Map](../../contracts/boundary-map.md#dependency-graph) and their
  subject HTTP contracts.
- The PWA MUST NOT directly access PostgreSQL, photo paths, Timeline writer,
  provider credentials/history, Agent Chat Bus, MessageEnvelope, Safety
  authority, or Dataset mutation services. Business orchestration never moves
  into a SvelteKit transport helper or backend composition root.

## Canonical strategy

1. Establish one checkable/buildable PWA scaffold before feature routes.
2. Establish the server-only authenticated shell before provider surfaces.
3. In parallel dependency terms, add the Dataset read provider while the shell
   is prepared; canonical execution remains sequential.
4. Add one task per independently completable accepted provider result. Keep
   read and mutation outcomes separate when either can reach useful completion
   and decisive failure/retry proof without the other; do not split by files or
   controls alone.
5. Add FT-015 prompt consumption as its own result because its status and
   transient Account state are a distinct accepted contract.
6. After all surfaces exist, prove UI-context isolation and browser-capture
   redaction independently.
7. Prove the Boss/Engineer `tomato_001` actor journey independently, then close
   the complete named-surface composition and no-fallback result in W6.

## Sequential queue

| Task | Tier / wave | Independent result | Direct dependency reason |
|---|---|---|---|
| TASK-080-T2-FT-016-W1 | T2 / W1 | SvelteKit/PWA scaffold | verified Foundation |
| TASK-081-T3-FT-016-W2 | T3 / W2 | authorized session/Plant shell and server-only transport privacy | scaffold, session/Plant APIs, FT-015 loopback/error redaction, REQ-020 |
| TASK-082-T3-FT-016-W3 | T3 / W3 | direct Engineer provisioning | shell and terminal Boss admin provider |
| TASK-083-T3-FT-016-W3 | T3 / W3 | daily check-in and observation | shell and terminal operations provider |
| TASK-084-T3-FT-016-W3 | T3 / W3 | local photo upload | shell, terminal photo API, FT-015 manifest redaction |
| TASK-085-T3-FT-016-W3 | T3 / W3 | authoritative Plant card | shell, terminal history provider, FT-015 history redaction |
| TASK-086-T3-FT-016-W3 | T3 / W3 | strict literal Plant Feed surface | shell, Advisor/Safety/Companion/Feed providers, FT-015 Feed redaction |
| TASK-087-T3-FT-016-W3 | T3 / W3 | Plant State trust-record list | shell and terminal Plant State provider |
| TASK-088-T3-FT-016-W3 | T3 / W3 | Task/Approval reads | shell and terminal lifecycle provider |
| TASK-089-T3-FT-016-W3 | T3 / W3 | Companion IssueStack/detail reads | shell, terminal Companion provider, FT-015 request redaction |
| TASK-090-T3-FT-016-W2 | T3 / W2 | protected Dataset read API | Foundation, ActorContext, terminal Dataset aggregate |
| TASK-091-T2-FT-016-W3 | T2 / W3 | read-only Dataset PWA consumer | shell and Dataset read API |
| TASK-092-T3-FT-016-W3 | T3 / W3 | FT-015 storage-prompt consumer | shell, local-only/status/handoff provider outcomes |
| TASK-096-T3-FT-016-W3 | T3 / W3 | membership role assignment | shell and terminal Boss admin provider |
| TASK-097-T3-FT-016-W3 | T3 / W3 | Plant lifecycle administration | shell and terminal Plant management provider |
| TASK-098-T3-FT-016-W3 | T3 / W3 | Plant access-grant administration | shell and terminal Plant management provider |
| TASK-099-T3-FT-016-W3 | T3 / W3 | admin audit presentation | shell and terminal Boss/Plant audit providers |
| TASK-100-T3-FT-016-W3 | T3 / W3 | standalone manual pH/EC | shell and terminal measurement provider |
| TASK-101-T3-FT-016-W3 | T3 / W3 | paginated photo catalog | shell, terminal photo provider, FT-015 redaction |
| TASK-102-T3-FT-016-W3 | T3 / W3 | paginated retained Plant history | shell, terminal history provider, FT-015 redaction |
| TASK-103-T3-FT-016-W3 | T3 / W3 | Plant State human review | shell and terminal Plant State provider |
| TASK-104-T3-FT-016-W3 | T3 / W3 | human Safety approval | shell and terminal Task/Approval provider |
| TASK-105-T3-FT-016-W3 | T3 / W3 | Task completion | shell and terminal Task provider |
| TASK-106-T3-FT-016-W3 | T3 / W3 | follow-up Outcome recording | shell and terminal Outcome provider |
| TASK-107-T3-FT-016-W3 | T3 / W3 | explicit Companion invocation | shell, terminal Companion provider, FT-015 request redaction |
| TASK-108-T3-FT-016-W3 | T3 / W3 | Companion proposal decision | shell, terminal Companion provider, FT-015 request redaction |
| TASK-109-T3-FT-016-W3 | T3 / W3 | Companion issue close | shell, terminal Companion provider, FT-015 request redaction |
| TASK-093-T3-FT-016-W4 | T3 / W4 | UI/agent-context isolation | all UI surfaces plus FT-015 request-owner redaction |
| TASK-094-T3-FT-016-W4 | T3 / W4 | REQ-020 browser-capture redaction | all captured surfaces plus FT-015 output redaction |
| TASK-095-T3-FT-016-W5 | T3 / W5 | Boss/Engineer `tomato_001` actor journey | shell, provisioning, and access-grant consumers |
| TASK-110-T3-FT-016-W6 | T3 / W6 | complete surface composition and production-unbound no fallback | actor journey, all provider surfaces, and both cross-cutting security results |

Tasks sharing W2 or W3 are readiness peers only; execution remains sequential.
Dependency tasks retain their own implementation and proof claims.

## Expected advisory change surface

- Scaffold/runtime: `frontend/package.json`, lock/config files,
  `frontend/src/routes/`, `frontend/src/service-worker.ts`, and PWA assets.
- Server transport/shell: `frontend/src/lib/server/`, session/Plant route loads
  and actions, plus focused Playwright files.
- Provider views: subject folders under `frontend/src/lib/` and the accepted
  Plant/Admin routes; exact filenames remain executor-local choices.
- Dataset provider: `backend/app/dataset_governance/`, one router under
  `backend/app/api/`, backend composition registration, and focused API tests.
- Browser proof: `frontend/tests/e2e/`, one safe capture helper, Playwright
  configuration, and task-owned evidence directories.
- `touched_files` is advisory. No task receives a hard `write_boundary`; its
  semantic scope, forbidden scope, and stop conditions remain binding.

## Verification and UAT

- Every T2/T3 task records honest claim-linked RED followed by equivalent
  GREEN, or preserves exact pre-implementation GREEN without an unnecessary
  production change.
- Frontend tasks run `npm run check`, applicable focused Playwright files, and
  `npm run build` when config/routing/server/service-worker behavior changes.
- The Dataset provider task runs focused API/OpenAPI/auth/pagination/failure
  tests and applicable Dataset regressions.
- Browser security uses one configured secret/auth corpus and one registered
  capture helper; context-isolation and capture-redaction remain independently
  decisive.
- The actor journey uses isolated Account/grant/browser state without adopting
  surface claims. The W6 composition uses isolated PostgreSQL/photo/timeline/
  browser state, test-only deterministic provider fakes/spies, safe
  rerun/cleanup, and a separate unbound-production no-fallback probe.
- Every card runs `node scripts/mb-lint.mjs` and `git diff --check`. T3 cards
  require `/verify` and per-task `/red-verify`; after all tasks, the queue uses
  the feature-level T2 completion gate required by tier policy because the
  queue contains T2 work.

## Governing sources and invariants

- Governing feature requirement: REQ-021. REQ-020 additionally governs exact
  server-only transport and browser-capture claims; REQ-003/004/013/022 apply
  only to the exact role/context/authority ACs owned by their mapped tasks.
- Constitution KISS, local-first, low-maintenance, no-SaaS, bounded autonomy,
  no-actuation, and Spec Before Code rules remain binding.
- [Operator PWA](../../contracts/operator-pwa.md),
  [Dataset Governance HTTP](../../contracts/dataset-governance-http.md),
  [Product Surface Redaction](../../contracts/product-surface-redaction.md),
  [Photo Intake status](../../contracts/photo-intake-http.md#storage-status-behavior),
  and [Operator PWA Verification](../../testing/operator-pwa-first-demo.md)
  are direct design/proof owners.
- Backend authorization and mutable state remain authoritative. Frontend
  visibility, cached data, DOM state, Feed content, prompt state, and browser
  artifacts grant no authority.
- `local_only` is immutable; prompt actions persist nothing; Dataset display
  never mutates or infers trainability; candidate text remains inert; product
  capture functionality is absent.

## Handoff

Queue action: `rebuild_required`. The rejected broad boundaries were rebuilt
as TASK-080 through TASK-110, all `planned`, for Global Planning Revision 4.
No task was implemented, promoted, executed, or closed. Immediate route:
`/review-tasks-plan FT-016`.
