---
description: Feature-local SDD tech spec for FT-011 minimal Web App/PWA operator surface.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-011-minimal-web-app-pwa-operator-surface.md
  - .memory-bank/spec-index.md
---
# FT-011 Minimal Web App/PWA Operator Surface Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-011 before `/prd-to-tasks FT-011`.

FT-011 owns the smallest operator-facing React/Next.js/PWA surface for the local `tomato_001` MVP:

- minimal route/view set and daily operator workflow;
- chat/check-in, photo upload, manual pH/EC, plant card, task, history, recommendation, approval, spoiler, and sync prompt surfaces;
- frontend consumption of existing API/domain specs;
- UI Feed rendering as presentation only;
- user-visible safety display behavior;
- no-leak context hygiene from UI to agents;
- local auth/LAN UI behavior and PWA/offline boundaries;
- UI/e2e smoke targets for the first daily flow.

FT-011 does not own backend domain authority, agent output contracts, UI Feed schema, Safety Gate policy, approval lifecycle, task state machine, photo/storage validation, local security implementation, dataset governance, a full design system, SaaS/multi-user UI, native mobile wrapper, offline mutation queue, background sync/upload, or automated device execution.

## Normative Inputs

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): frontend/backend boundary, daily sequence, authority model, and sync boundary.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): HTTP API shape, error envelope, security baseline, and OpenAPI policy.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): UI Feed event types, presentation-only rule, spoiler refs, and display safety.
- [.memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md](FT-005-ui-feed-context-hygiene.md): UI Feed storage/read behavior, context filtering, controlled spoiler notes, and display safety tests.
- [.memory-bank/tech-specs/FT-010-local-security-privacy-lazy-sync.md](FT-010-local-security-privacy-lazy-sync.md): loopback/LAN auth, CORS, upload validation envelope, redaction, `local_only`, and 200 MiB prompt behavior.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): Safety Gate outcomes, pH/EC freshness windows, and approval semantics.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](FT-013-safety-gate-physical-action-advice.md): final display checks for Companion responses, spoiler notes, task wording, and approval prompts.
- [.memory-bank/tech-specs/FT-014-human-approval-action-unlock-semantics.md](FT-014-human-approval-action-unlock-semantics.md): human approval/rejection API and "human-performed task tracking" wording.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](FT-001-daily-check-in-observations-manual-measurements.md): daily prompt, observation/no-data state, manual pH/EC input, and freshness projection.
- [.memory-bank/tech-specs/FT-002-photo-intake-catalog-capture-manifests.md](FT-002-photo-intake-catalog-capture-manifests.md): photo upload/catalog API, accepted photo refs, and photo history source.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): PostgreSQL read model, current state API, and read-only timeline history.
- [.memory-bank/tech-specs/FT-006-vision-observation-plant-state-trust.md](FT-006-vision-observation-plant-state-trust.md): plant-state display source and vision observation workflow outputs.
- [.memory-bank/tech-specs/FT-007-hydroponics-advisor-missing-data-policy.md](FT-007-hydroponics-advisor-missing-data-policy.md): cautious recommendation, missing-data, and Safety Gate handoff behavior.
- [.memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md](FT-008-tasks-approvals-follow-up-outcomes.md): task list, transitions, follow-up outcome, and no direct action-task creation.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): concise agent output, `MessageEnvelope`, `ui_spoiler_note_ref`, and safety boundary.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): first-demo workflow, UI/e2e, anti-cheat, and MB validation gates.
- [.memory-bank/invariants.md](../invariants.md): one-plant scope, runtime authority, UI Feed isolation, safety, privacy, and MVP non-goals.

## Design Decisions

### Minimal Route And View Set

The first screen is the working operator surface, not a landing page.

FT-011 uses one plant scope, `tomato_001`. The frontend may implement the route set as pages, tabs, or router segments, but the MVP must provide these navigable views:

| View | Purpose | Required surfaces |
|---|---|---|
| Today / Daily | Run the daily operator loop | plant card, daily prompt/chat, observation/no-data input, photo upload, manual pH/EC input, latest recommendation/status, approval prompts, open task summary, sync prompt |
| History | Inspect past evidence | day history from timeline/read APIs, photo history from catalog, source refs where displayed |
| Tasks | Act on pending work | open/completed task list, task transitions, follow-up outcome capture, pending approval task visibility |

Acceptable routes include `/`, `/plants/tomato_001/today`, `/plants/tomato_001/history`, and `/plants/tomato_001/tasks`. A single-route app with tabs is acceptable if each view is reachable and testable.

Optional detail panels for `photo_id`, `task_id`, or `approval_id` may be modal/drawer states inside those views. They are not a separate product scope.

Do not add marketing pages, admin dashboards, farm/multi-plant navigation, user management, data labeling workbenches, raw log viewers, or production SaaS shells in FT-011.

### Surface Behavior

| Surface | Required behavior |
|---|---|
| Plant card | Shows current `tomato_001` summary from PostgreSQL/read-model projections, not timeline replay, photo manifests, UI Feed, or Bus replay. It may include latest pH/EC freshness, plant-state status/confidence, recent photo refs, and open task/approval counts. |
| Chat / daily prompt | Starts with the FT-001 prompt, such as `Как томат сегодня?`, and guides the daily flow. It is a UI for user input and presentation, not direct access to Agent Chat Bus internals. |
| Daily check-in | Lets the user submit observation text or explicit no-observation state plus optional pH/EC values with timestamps/provenance. The UI must not invent observation text. |
| Photo upload | Uses FT-002 photo types and FT-010 upload validation behavior. Failed uploads must not look accepted and must show safe error messages from the shared error envelope. |
| Manual pH/EC | Accepts pH and EC independently, preserves measured-at/provenance inputs, and displays analysis/approval freshness without implying that fresh data alone authorizes action. |
| Recommendations | Displays concise user-safe conclusions, clarification requests, missing-data prompts, and Safety Gate results. Physical-action wording must use cleared or safe replacement text only. |
| Controlled spoiler notes | Render collapsed or secondary UI-only `ui_spoiler_note` content with title such as `поразмыслил`. Spoilers are controlled summaries, not raw reasoning, facts, labels, or agent context. |
| Task list | Shows check, measurement, pending approval, action, and follow-up tasks from the FT-008 read model. Direct client creation of `action_task` is forbidden. |
| Approval prompt | Represents human approval/rejection for a pending proposal and must state that approval unlocks human-performed task tracking only. It must not imply automated device execution. |
| History | Shows read-only day history and photo history with stable refs. Timeline data is audit/export history, not current mutable state authority. |
| Sync prompt | Shows the 200 MiB local storage prompt only from `local_only` sync state. Acknowledge/dismiss behavior must not imply server availability or mutate sync status. |

### Daily Operator Workflow

The UI drives a small, testable daily flow without becoming the owner of domain state:

1. Load the Today view using current plant/read-model state, latest pH/EC freshness, open tasks/approvals, recent UI Feed events, sync status, and recent photos.
2. Show the daily prompt for `tomato_001`.
3. Let the user submit observation text or an explicit no-observation state.
4. Let the user add zero or more photos with `photo_type` and optional `captured_at`.
5. Let the user add pH, EC, or both with `measured_at` and provenance.
6. Submit each write through the owning backend endpoint or workflow service and keep backend-generated IDs as source refs.
7. Refresh the presentation state after accepted writes and after agent/workflow completion, using read APIs and UI Feed refs.
8. Display recommendations, clarification/missing-data prompts, safety blocks, approval prompts, task updates, and spoiler notes from backend-owned projections.
9. Let the user approve/reject pending proposals, transition tasks, and record follow-up outcomes through FT-014/FT-008 routes.

The frontend may sequence uploads and check-in writes separately. It may also call an implementation-specific daily workflow endpoint if such an endpoint is added later, but that endpoint must only orchestrate owning services from FT-001/002/006/007/008/013/014 and must not bypass their contracts.

The UI must show partial progress honestly. Example: an accepted check-in with a failed photo upload remains a check-in with a failed upload, not a complete photo-backed analysis.

### API Dependency Map

FT-011 introduces no new backend authority. It consumes and composes existing feature-owned endpoints and may use a thin read-only view-model endpoint only if implementation tasks prove it simpler than multiple reads.

| UI need | Owning spec | Endpoint or surface |
|---|---|---|
| Daily prompt and check-in write | FT-001 | `GET /api/plants/{plant_id}/daily-checkin/prompt`, `POST /api/plants/{plant_id}/daily-checkins` |
| Manual pH/EC outside check-in | FT-001 | `POST /api/plants/{plant_id}/measurements`, `GET /api/plants/{plant_id}/measurements/latest` |
| Photo upload/history/detail | FT-002 | `POST /api/plants/{plant_id}/photos`, `GET /api/plants/{plant_id}/photos`, `GET /api/plants/{plant_id}/photos/{photo_id}` |
| Current plant/runtime summary | FT-003 / FT-006 | `GET /api/plants/{plant_id}/state`, `GET /api/plants/{plant_id}/plant-state` |
| Day history | FT-003 | `GET /api/plants/{plant_id}/timeline` as read-only audit/export view |
| UI Feed, statuses, spoilers, prompts | FT-005 | `GET /api/ui-feed/events` |
| Vision observation flow | FT-006 | `POST /api/plants/{plant_id}/vision-observations`, report reads when exposed |
| Hydroponics recommendation/missing data | FT-007 | `POST /api/plants/{plant_id}/hydroponics-advice` when exposed, or internal daily workflow result |
| Tasks and follow-up | FT-008 | `GET /api/plants/{plant_id}/tasks`, task transition and follow-up outcome routes |
| Final display safety check | FT-013 | internal display check or `POST /api/safety/check-text` when exposed |
| Approval/rejection | FT-014 | `GET /api/approvals/{approval_id}`, `POST /api/approvals/{approval_id}/approve`, `POST /api/approvals/{approval_id}/reject` |
| Local readiness | FT-003 / FT-010 | `GET /api/runtime/health` with no secrets or absolute paths |
| Sync prompt | FT-010 | `GET /api/sync/status`, `POST /api/sync/prompt-ack` |

All frontend errors use the structured API error envelope. The UI may translate safe `message` text for the operator, but must preserve machine-readable `code` in logs/test assertions without exposing secrets.

### UI Feed Consumption And Context Hygiene

UI Feed is a read-only presentation input for FT-011:

- The PWA may render `agent_ui_status`, `system_ui_status`, `debug_lite_card`, `ui_spoiler_note`, `approval_prompt`, `agent_silent_decision`, and `sync_prompt`.
- The PWA must not pass UI Feed payload text, spoiler text, debug-lite content, screenshots, or rendered UI state into agent invocation requests.
- If the UI triggers a "quote/detail" interaction, it must send stable domain refs such as `message:<message_id>`, `bus:<bus_event_id>`, `photo:<photo_id>`, `task:<task_id>`, or `approval:<approval_id>`, not copied `ui_spoiler_note` text.
- `ui_spoiler_note_ref` remains a pointer. The frontend may dereference it for human display only.
- UI Feed content cannot update plant state, task state, approval state, dataset labels, `can_train_on`, or sync state.

Manual copy/paste by the human into a free text field is treated as new user text. The UI must not automate that copy or include hidden UI Feed content in requests.

### Safety Display Rules

Every user-visible FT-011 surface that can contain action wording must render one of these states:

- Safety Gate cleared display text with source refs and `safety_decision:<safety_decision_id>` when a Safety Gate decision is involved;
- safe pending-approval/check wording from FT-013/FT-014/FT-008;
- blocked/replaced text that avoids actionable parameters;
- missing-data prompt that requests pH/EC/photo/check evidence without prescribing intervention.

The UI must never display pH/EC correction, dosing, solution, pump, light, pruning, transplanting, root trimming, or similar intervention instructions as cleared action unless the backend has passed the relevant Safety Gate and human-approval path. If the display-safety result is missing, stale, malformed, or unavailable, the UI fails closed by hiding the unsafe text and showing safe replacement or pending-review wording.

Approval prompts and approved action tasks must still say the task is human-performed. Approval does not create device commands, automation targets, actuator dispatch statuses, or background plant-control jobs.

### Local Auth, LAN, And Privacy UI

- The default local UI expects loopback backend access.
- In protected LAN mode, the UI may ask for a bearer token or receive it through explicit local configuration. The token must be sent only in the `Authorization` header for protected API calls.
- Tokens, `.env` values, provider keys, database URLs, and credentials must never appear in route query strings, UI Feed, screenshots/e2e artifacts, local logs, error displays, or debug-lite cards.
- The UI must not display local absolute file paths for photos/manifests. It should use safe artifact refs or backend-served media URLs that preserve FT-010 path rules.
- CORS and auth failures are shown as local connection/authentication problems, not as sync/server account problems.

### PWA And Offline Boundaries

FT-011 may implement a PWA shell and static asset caching, but MVP offline behavior is intentionally narrow:

- No offline mutation queue for check-ins, photos, measurements, approvals, tasks, or follow-up outcomes.
- No background upload, background sync, service-worker sync, or server upload prompt.
- No offline accepted-photo IDs or fake successful submissions.
- No caching of protected API responses, local photos, manifests, tokens, or UI Feed payloads in a way that can leak private data.
- If the backend is unreachable, the UI may preserve unsent form drafts in memory or explicit local draft state, but it must show them as unsent and must not append timeline/state/task/approval refs.
- When connectivity returns, the user must explicitly submit again.

Installability, icons, responsive layout, and reload resilience are acceptable PWA tasks. Native mobile wrappers such as Capacitor are future scope.

## Verification Targets

Required before FT-011 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- UI/e2e smoke `e2e:daily-ui-smoke` proving the Today view can run the critical daily flow for `tomato_001`: prompt, observation/no-observation, photo upload, optional pH/EC, state refresh, recommendation/status display, task/approval visibility, and history/photo visibility.
- UI Feed integration test proving `GET /api/ui-feed/events` renders statuses, controlled spoiler notes, approval prompts, and sync prompts while preserving `visible_to_agents=false` and `consumable_by_agents=false`.
- Context-hygiene test proving UI Feed payloads, spoiler text, debug-lite cards, screenshots, and rendered presentation state are not sent in agent/workflow request bodies.
- Safety display tests proving Companion output, recommendation cards, spoiler notes, approval prompts, task wording, and debug-lite cards fail closed when physical-action wording lacks Safety Gate clearance.
- Approval workflow smoke proving approve/reject uses FT-014 routes, pending approval text describes human-performed task tracking only, and no device-execution fields are produced or displayed.
- Task workflow smoke proving the UI lists check/measurement/pending-approval/action/follow-up tasks, rejects direct `action_task` client creation, transitions allowed statuses, and records follow-up outcomes through FT-008.
- Photo UI tests proving upload progress/error states match FT-002/FT-010 results, accepted photos show backend refs, and failed uploads do not appear accepted.
- pH/EC UI tests proving independent pH/EC input validation, measured-at/provenance capture, and analysis/approval freshness display without treating freshness as action authorization.
- History tests proving day history comes from read-only timeline/audit API and current plant card state comes from PostgreSQL/read-model projections.
- Lazy-sync prompt test proving the 200 MiB prompt appears only from `local_only` sync state and acknowledge/dismiss does not imply server sync or mutate status away from `local_only`.
- Local auth/privacy UI tests proving LAN bearer token handling, auth/CORS failure messaging, no token/query leak, no absolute path display, and redacted screenshot/e2e artifacts.
- PWA/offline boundary test proving static shell reload works while offline mutations, background sync, and fake accepted submissions are unavailable.

## Gaps And Non-Goals

- No FT-011 blocker remains for `/prd-to-tasks FT-011`.
- Exact React component names, CSS/design tokens, state-management library, route implementation style, Playwright fixture names, and screenshot storage paths belong to implementation tasks.
- A read-only operator summary endpoint is optional, not required; if added, it must compose authoritative read models and must not become a new source of truth.
- Full frontend design system, data-labeling UI, admin/debug dashboards, native mobile wrappers, user accounts, SaaS sync, offline upload queue, sensor dashboards, and automated device control are outside FT-011 MVP scope.
