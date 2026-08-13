---
description: Deterministic browser and integration verification for the Operator PWA first demo.
status: active
type: testing_spec
last_updated: 2026-08-13
source_of_truth:
  - .memory-bank/features/FT-016-web-app-pwa-operator-surface-first-demo.md
  - .memory-bank/contracts/operator-pwa.md
  - .memory-bank/contracts/product-surface-redaction.md
  - .memory-bank/contracts/dataset-governance-http.md
---
# Operator PWA First-Demo Verification

## Scope

Defines deterministic check/build, focused Playwright, backend API, browser
security, and first-demo evidence for FT-016. It verifies PWA composition over
existing backend owners without re-proving their task-owned implementation
claims or using an external model endpoint.

## Reproducible test state

- Use an isolated PostgreSQL test database, temporary photo/timeline roots,
  fixed loopback backend/frontend ports, and a clean browser context per test.
- Bootstrap the single Farm, `tomato_001`, and first Boss through existing
  test/runbook seams. Create Engineer/grant and subsequent product records
  through the owning HTTP/service boundaries required by each scenario.
- Provider-dependent rows use explicit test-only deterministic fake/spy
  executors. Production composition is tested separately with no selected
  endpoint and MUST fail before network I/O without fallback.
- Every test is safe to rerun from a fresh isolated database/browser context.
  Cleanup removes temporary artifacts and browser traces after required
  evidence is copied under the owning `.tasks/<TASK-ID>/` directory.

## Scaffold and routing matrix

- `npm run check` and `npm run build` pass with one Svelte 5/SvelteKit stack.
- Manifest/service-worker smoke proves installability and static-shell-only
  caching; protected API/SSR data and mutations are never cached or queued.
- `/login`, `/admin`, and `/plants/[plant_id]` are the only application route
  families; invalid/unauthorized navigation fails safely.

## Role and provider-surface matrix

- Boss: login, Engineer creation, role, Plant/grant, audit, and admin denial for
  non-Boss roles.
- Engineer: authorized Plant selection, daily check-in, observation, pH/EC,
  photo upload/catalog refs, Plant card/history, Feed, Plant State, tasks,
  approvals/follow-up, Companion, Dataset projection, and storage prompt.
- Revoked, disabled, unauthorized, and archived paths agree with backend
  authority. Frontend visibility never converts a denied backend result into a
  successful state.
- Each focused browser file proves only its owning Operator PWA result; backend
  provider claims remain dependency evidence.

## FT-015 consumer matrix

- The browser displays status values returned by Photo Intake and never
  calculates the threshold or scans storage.
- `acknowledge` and `dismiss` close only the current component; fresh load may
  show it again, Account change clears state, and no prompt mutation request or
  browser persistence exists.
- Wording remains `local_only` and contains no upload/server implication.

## Context and literal-text matrix

- Representative HTML, Markdown, prompt, command, and URL-looking Feed/model
  strings remain visible inert text with no active element, link, HTML tree,
  command, navigation, or action side effect.
- Instrumented browser requests plus existing provider spies contain no page
  text, Feed payload, admin notice, prompt state, DOM/history data, raw cookie,
  or auth header outside the owning server transport.
- Dataset UI sends no transition/review/trainability request and shows the
  exact authority values from Dataset Governance HTTP.

## Browser-capture matrix

- One registered Playwright helper owns screenshot, trace, video, and DOM
  snapshot creation for FT-016 tests.
- The configured secret/auth corpus crosses allowed displayed text and safe
  error fixtures. Captures contain no raw corpus value; source fixtures remain
  unchanged; failure artifacts contain only a stable safe error.
- Static inspection rejects direct capture calls outside the helper. No
  product screenshot button or production capture endpoint is introduced.

## First-demo gate

The final isolated browser journey composes both actors and every FT-016 named
surface. It records route/request evidence, safe browser artifacts, and the
production-unbound anti-fallback probe. It does not claim a real provider call,
LAN mode, Consultant UI, backend provider implementation, or feature closure
before the required verification workflow.

## Gates

- focused `npm run check`, `npm run build`, and task-owned Playwright files;
- focused Dataset Governance HTTP pytest for the backend read task;
- final full FT-016 Playwright suite and applicable deterministic backend
  regressions;
- `node scripts/mb-lint.mjs` and `git diff --check`.

