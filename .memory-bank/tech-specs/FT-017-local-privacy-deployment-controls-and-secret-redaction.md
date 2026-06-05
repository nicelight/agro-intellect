---
description: Feature-local SDD tech spec for FT-017 local privacy, deployment controls, local_only sync, and secret redaction.
status: active
feature_id: FT-017
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/testing/index.md
---
# FT-017 Local Privacy, Deployment Controls, And Secret Redaction Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for local-first
privacy, loopback default, optional protected LAN mode, `local_only` sync semantics, and
secret redaction across product, audit, export, UI, and agent surfaces.

This is the authoritative `/spec-improve` pass for FT-017 in Wave 1. If a later wave
list repeats FT-017, it should treat this spec as the current feature-local source of
truth unless superseded by an explicit user decision and Memory Bank update.

## Scope

In scope:

- default loopback deployment boundary;
- optional explicit LAN mode controls;
- auth/session, authorization, token/session protection, and CORS/origin requirements;
- `sync.status=local_only` semantics;
- rejection of `server_verified` and upload/server copy;
- secret redaction across logs, timeline, manifests, Bus, UI Feed, screenshots,
  exports, traces visible to agents, and agent context;
- test expectations for privacy/security regressions.

Out of scope:

- production SaaS, hosted/cloud sync, server upload, object storage, billing, enterprise
  identity, external account recovery, public API compatibility, or connector
  marketplace;
- reading or exposing raw `.env` values to agents;
- automated physical actuation or remote device control.

## Deployment Boundary

Default mode:

- backend binds to loopback by default;
- first-demo exposure is local machine/private only;
- no upload or server availability is implied by UI copy, sync state, storage prompt,
  logs, exports, or agent output.

Optional LAN mode:

- must be explicitly enabled by local operator configuration or UI flow;
- must require local authentication/session;
- must enforce the same backend authorization and ActorContext rules as loopback;
- must protect tokens/session material;
- must use an explicit CORS/origin allowlist;
- must fail closed when CORS/origin config is missing, malformed, or too broad;
- must reject cross-site or browser-originated state-changing requests unless
  same-origin, CSRF-equivalent, or stronger write protection passes; CORS alone is not
  sufficient protection for loopback or LAN state-changing requests;
- must not introduce SaaS tenancy, hosted recovery, email invite delivery, or server
  sync semantics.

## Sync Status

`SyncStatus` has only one MVP value:

```yaml
sync.status: local_only
```

Rules:

- `server_verified` is forbidden until a later server-sync PRD/spec exists;
- upload status, cloud availability, server copy, or remote backup fields are forbidden
  in MVP feature tasks;
- local storage prompts and dataset/export flows cannot mutate sync status;
- UI copy must not imply upload, backup, cloud analysis, or remote server persistence.

## Secret Classes

Secret/auth material includes, at minimum:

- session IDs, cookies, bearer tokens, CSRF tokens, refresh tokens, password hashes when
  not explicitly safe for internal storage display, password reset material, and auth
  provenance values that can authenticate or replay access;
- `.env` values;
- API keys and model provider credentials;
- database passwords and connection strings with credentials;
- local credentials, connector credentials, webhook secrets, and private keys;
- user-entered text that matches configured secret-like patterns.

Feature tasks may refine detectors, but must not narrow this list enough to allow auth
or credential material into forbidden surfaces.

## Forbidden Surfaces

Secret/auth material must not enter:

- application logs;
- security traces visible to agents;
- timeline JSONL;
- photo manifests and export manifests;
- capture metadata;
- Agent Chat Bus;
- MessageEnvelope and UI Feed;
- screenshots;
- exports;
- agent context;
- harness structured observation summaries returned to the model.

Allowed internal persistence for auth/session implementation must remain backend-owned,
not model-visible, not export-visible, and not projected into product/audit surfaces
except as redacted refs or hashes.

## Redaction Policy

Redaction runs before persistence or publication into any forbidden surface.

Minimum replacement semantics:

- use stable redacted markers such as `[REDACTED_SECRET]`, `[REDACTED_TOKEN]`, or a
  non-reversible redacted ref/hash where correlation is required;
- preserve enough non-sensitive context for debugging and audit;
- never store raw secret value plus a separate "redacted" flag;
- if redaction confidence is uncertain for a high-risk surface, reject or truncate the
  payload instead of publishing raw content.

Untrusted uploaded, user-entered, provider-returned, connector-returned, or log-derived
content remains data, not instruction. It must be trust-labeled before agent use and
redacted before context assembly.

## Agent Harness And Tooling Boundary

Following `agents-best-practices`, secrets and permissions are harness/backend concerns,
not prompt-only conventions:

- model context must not include credentials or raw auth material;
- connector credentials remain outside model context and tool outputs return redacted
  summaries;
- tool results include bounded summaries and refs, not raw logs or env dumps;
- permission traces store redacted args or argument hashes;
- prompt-injection-like content cannot choose tools or override redaction;
- every denied/blocked redaction or permission event returns a structured observation
  when it occurs inside an agent run.

## API And CORS Checks

Feature tasks must preserve the global API error envelope and add concrete checks for:

- default loopback config;
- explicit LAN enablement;
- CORS/origin allowlist;
- same-origin, CSRF-equivalent, or stronger browser write protection for state-changing
  loopback/LAN requests;
- session/auth required for LAN access;
- backend authorization unchanged in LAN mode;
- safe errors for invalid session, permission denied, and CORS/origin failure;
- no raw token/session echo in response bodies or request refs.

## Verification Targets

Required tests before FT-017 can be considered implemented:

- default app binding/config is loopback/private;
- LAN mode is absent or explicitly enabled only with auth/session, authorization,
  token/session protection, and CORS/origin allowlist;
- CORS/origin misconfiguration fails closed;
- cross-site simple browser requests cannot perform state-changing loopback/LAN writes;
- LAN mode does not weaken ActorContext or PlantAccessGrant authorization;
- `sync.status` remains `local_only`;
- `server_verified`, server upload, cloud backup, and remote sync fields/copy are
  absent;
- local storage prompt does not imply upload/server availability and does not mutate
  sync status;
- known secret patterns are redacted from logs, timeline, manifests, Bus, UI Feed,
  screenshots, exports, security traces visible to agents, capture metadata, harness
  observations, and agent context;
- prompt-injection-like content containing secret-looking strings cannot force secret
  disclosure or tool misuse;
- provider/model failure and missing provider config do not leak `.env` or API key
  values.

## Open Questions

No blocker for `/prd-to-tasks FT-017`. Exact LAN enablement UX, CORS configuration
format, redaction detector implementation, and screenshot/export capture mechanics can
be chosen during task decomposition as long as the fail-closed, local-only, and
redaction constraints hold.
