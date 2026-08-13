---
description: Canonical presentation and interaction contract for the local SvelteKit Operator PWA first-demo surface.
status: active
type: presentation_contract
last_updated: 2026-08-13
source_of_truth:
  - .memory-bank/features/FT-016-web-app-pwa-operator-surface-first-demo.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/contracts/product-surface-redaction.md
---
# Operator PWA

## Scope

Defines the minimal Svelte 5/SvelteKit Web App/PWA routes, server-side backend
transport, role-aware presentation surfaces, FT-015 consumer behavior,
literal-text rules, browser-capture boundary, and first-demo composition owned
by the `Operator PWA` module under `frontend/`.

The PWA is a presentation and interaction consumer. Backend modules retain
authorization, mutable state, Safety approval, governance, dataset
trainability, photo accounting, audit, upload, and sync authority.

## Out of scope

- Consultant UI, a broad dashboard, arbitrary user-configurable layouts, and a
  mobile wrapper;
- LAN mode, CORS expansion, hosted deployment, server sync, background upload,
  offline mutation queues, and protected-response caching;
- raw provider output, Markdown/HTML execution, generic prompts, arbitrary
  Task creation, Dataset review/transition controls, and product screenshot
  functionality.

## SvelteKit PWA scaffold

The first executable frontend MUST use only Svelte 5 Runes, TypeScript, and
SvelteKit. It exposes exactly three application route families:

- `/login` — local Account login;
- `/admin` — Boss-only administration;
- `/plants/[plant_id]` — selected-Plant workspace containing the accepted
  operations, photo, history, feed, state, task, Companion, dataset, and
  storage-prompt sections.

The scaffold MUST provide `npm run check`, `npm run build`, and a Playwright
browser-test command. The installable manifest and service worker MAY cache
only versioned static application-shell assets. They MUST NOT cache protected
API/SSR responses, persist Account/Plant state, queue mutations, or implement
background sync. No competing frontend framework or legacy Svelte syntax is
allowed. Verification is dependency/config inspection, check/build success,
manifest/service-worker smoke, and absence of protected-response caching.

## Authorized session and Plant shell

Initial data loads use SvelteKit server `load`; form mutations use server
actions. One server-only backend client calls a fixed validated loopback origin
and forwards only the current request cookie plus required safe request
headers. The browser never receives the backend origin, session token, raw
cookie, authorization header, or provider credential. Login/logout forward the
backend's cookie set/clear result without copying a token into page data.

The shell obtains current identity from Session HTTP and authorized Plants from
Plant Management HTTP. It discards all transient selected-Plant and prompt
state on logout, Account/auth change, or invalid session. Boss sees admin
navigation; Engineer sees only granted active Plants. Frontend hide/show is
presentation only: every load/action trusts the backend result, maps stable
safe errors, and never converts a stale UI snapshot into authority.

The backend client MUST NOT accept a browser-selected target origin, log raw
cookies or request bodies, forward hop-by-hop headers, expose raw exceptions,
or introduce a generic external proxy. Protected responses remain `no-store`.
Verification covers login/logout, Account change, Plant switch, revoked grant,
disabled membership, archived Plant, safe error mapping, and source inspection
of server-only imports.

## Boss Admin surface

`/admin` composes only the registered Boss Admin and Plant Management HTTP
boundaries for personnel, direct Engineer creation, role assignment, Plant
list/lifecycle, access grants, approval flag, and admin audit. Password input is
write-only to the server action and is never returned, logged, stored in page
state after submission, or captured. Engineer and Consultant access fails
through backend authority. Verification uses a Boss browser journey and proves
the created Engineer can log in and see only the granted Plant.

## Plant Operations surface

The selected-Plant workspace composes Plant Operations HTTP for daily
check-in, observations, and manual pH/EC. Inputs contain only registered
fields; ActorContext, Farm, role, Plant status, attribution, freshness, and
audit data remain backend-derived. Disabled, unauthorized, revoked, or
archived results are shown as safe errors without optimistic authority.
Verification covers successful Engineer operations and rejected stale or
unauthorized attempts.

## Photo Intake surface

The selected-Plant workspace composes Photo Intake HTTP for multipart upload
and catalog reads. It shows safe catalog identity, photo type, checksum,
manifest/event refs, local-only state, and immutable source
`can_train_on=false`; it never shows filesystem paths or implies remote upload.
Browser validation is advisory only and backend validation remains decisive.
Verification covers a real local test file, returned refs, unsupported/large
input, unauthorized/archived denial, and no server/sync wording.

## Plant History surface

The workspace composes Plant History HTTP for the Plant card and paginated
history. Timeline/export evidence appears only through the safe history
projection; the PWA has no direct Timeline writer or replay edge. Active and
authorized retained-history modes follow backend results, including canonical
cursor failure. Verification covers current and archived retained history,
refs, pagination, and absence of raw paths/auth material.

## Plant Feed surface

The workspace consumes Plant Feed HTTP and the exact `UIFeedEventV1` union. It
renders every registered introduction, agent, block, Safety, and Companion
text field only with Svelte interpolation/text-node semantics. It MUST NOT use
raw HTML, a Markdown renderer, URL activation, action parsing, or copy display
payloads into action bodies or agent context. Safety and Advisor presentation
is read-only; Feed rows cannot approve, execute, refresh, or create work.

Verification covers every union variant, pagination/retry, representative
HTML/Markdown/prompt/command/URL-looking text, no active element or action
side effect, and unchanged non-consumability.

## Plant State surface

The workspace consumes Plant State HTTP for trust-record list and explicit
confirm/reject review. The client may send only `decision` and
`expected_version`; trust status, evidence, agent/provider identity, summary,
and confirmation attribution remain backend-owned. Verification covers list,
review, version/conflict errors, Consultant/read-only/archived denial, and
retained-history presentation.

## Task and Follow-Up surface

The workspace consumes Task And Approval HTTP for lists, human Safety approval
decisions, Task completion, and follow-up Outcome recording. It never exposes
arbitrary Task creation, action text editing, approval expiry extension,
device execution, or a bypass around current permission/freshness/version
checks. Verification covers safe check/measurement/action/follow-up views,
authorized and denied approval, completion, Outcome evidence, conflict/retry,
and archived denial.

## Companion Governance surface

The workspace consumes Companion Governance HTTP for IssueStack/detail,
explicit provider-neutral invocation, current-proposal decision, and resolved
issue close. Displayed proposal/rationale/summary text remains presentation
data. The PWA cannot create DecisionRecord effects locally, treat governance
approval as Safety approval, approve a superseded proposal, or post raw UI
content as provider input. Verification covers attention, proposal,
approve/reject, supersede, decision summary, close, denied role/archive, and
unbound-production failure without fake fallback.

## Dataset Governance surface

The workspace consumes only the read boundary in Dataset Governance HTTP. It
shows candidate source identity, status, split, confirmation source, evidence
refs, curator decision, and derived `can_train_on`. It provides no review,
transition, split, evidence, curator, or trainability mutation control and
never infers trainability from photo, manifest, Timeline, Feed, or UI state.
Verification compares rendered values with the protected response and proves
that the frontend emits no Dataset mutation request.

## Storage prompt consumer

The PWA loads `GET /api/photos/storage-status` and shows the warning only when
`prompt_eligible=true`. It uses the returned exact bytes and literal
`local_only`; it neither recalculates the threshold nor scans files.
`acknowledge` and `dismiss` both close only the current component instance via
component-local `$state`. No cookie, localStorage, sessionStorage, IndexedDB,
backend action, Timeline event, cooldown, upload approval, or sync mutation is
created. Fresh page/status load may show the prompt again, and every auth or
Account change discards the state.

Verification covers absent/below/exact/above behavior supplied by the backend,
both actions, fresh-load reappearance, Account switch, no mutation request,
and wording without server/upload implication.

## UI context isolation

Page data, display text, admin notices, Feed payloads, storage-prompt state,
DOM state, and browser history MUST NOT enter generic or competence-specific
provider requests, MessageEnvelope, Agent Chat Bus, Dataset evidence, Safety
classification, or backend authority fields. Server actions accept only the
registered backend request shapes and reject or omit UI-only fields.
Verification instruments all browser requests and the existing provider spies
to prove no UI-origin value crosses an agent/authority boundary.

## Browser-capture redaction

FT-016 adds no user-facing screenshot feature. Any Playwright screenshot,
trace, video, DOM snapshot, or other browser artifact MUST be created only by
the registered test capture helper after the configured test secret/auth
corpus is sanitized or omitted. Raw cookies, tokens, headers, passwords,
private environment values, backend origin, and provider credentials MUST
never be rendered as capture input. Capture failure emits only a stable safe
test error and no rejected value; the source fixture values remain unchanged.

Verification injects the canonical configured corpus through actual allowed
UI text/error paths, proves every capture artifact contains none of it, and
proves direct Playwright capture APIs are absent outside the helper.

## First-demo composition

One isolated browser scenario starts from a local Boss and `tomato_001`, creates
and grants an Engineer, then exercises the accepted Boss and Engineer surfaces
through the PWA. Deterministic fake/spy executors are test-only setup for
provider-dependent records; a separate production-composition probe remains
unbound and fails closed with no fake/canned fallback. The scenario proves the
PWA composes backend results but does not adopt their authority or proof.

## Related contracts

- [Boundary Map](boundary-map.md)
- [Session HTTP](auth/session-http.md)
- [Boss Admin HTTP](admin/boss-admin-http.md)
- [Plant Management HTTP](farm/plant-management-http.md)
- [Plant Operations HTTP](plant-operations-http.md)
- [Photo Intake HTTP](photo-intake-http.md)
- [Plant History HTTP](plant-history-http.md)
- [Plant Feed HTTP](plant-feed-http.md)
- [Plant State HTTP](plant-state-http.md)
- [Task And Approval HTTP](task-approval-http.md)
- [Companion Governance HTTP](companion-governance-http.md)
- [Dataset Governance HTTP](dataset-governance-http.md)
- [Product Surface Redaction](product-surface-redaction.md)

