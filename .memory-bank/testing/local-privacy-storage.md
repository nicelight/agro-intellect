---
description: Verification specification for FT-015 local-only runtime policy, product redaction, photo storage pressure, and prompt-consumer semantics.
status: active
type: testing_spec
last_updated: 2026-08-12
source_of_truth:
  - .memory-bank/features/FT-015-local-security-privacy-storage-prompt.md
  - .memory-bank/contracts/product-surface-redaction.md
  - .memory-bank/contracts/photo-intake-http.md
  - .memory-bank/domains/photo-artifacts.md
---
# Local Privacy And Storage Verification

## Scope

Defines deterministic FT-015 proof for the supported loopback runtime,
`local_only` configuration, product-surface redaction, authoritative photo
storage pressure, the protected read contract, and the stateless consumer
handoff. It does not create the Svelte/PWA component owned by FT-016.

## Runtime policy matrix

- Default and explicit `SYNC_STATUS=local_only` settings load successfully.
- Any other configured sync status, including `server_verified`, fails settings
  validation before application startup.
- The supported local start path binds `127.0.0.1`; the current FT-015 scope
  exposes no LAN mode, host override, bearer-LAN transport, or CORS mode.
- A real local smoke checks `/health`, `/ready`, and one protected endpoint
  without exposing Farm/Plant or auth material through public routes.

The absence of LAN implementation is intentional: PRD makes it optional and
does not require it for the first demo. A future LAN capability requires an
explicit design route and the controls in API Guidelines and Session Security.

## Photo pressure matrix

Repository/service tests use accepted Photo Catalog rows as the only input:

| Accepted original total | Expected eligibility |
|---:|---|
| `209715199` | `false` |
| `209715200` | `false` |
| `209715201` | `true` |

Additional checks prove:

- empty Farm returns zero and `false`;
- each Photo Catalog row contributes its `size_bytes` exactly once;
- rows for another Farm do not contribute;
- retained photos for archived Plants still contribute because their local
  bytes and accepted catalog authority remain retained;
- manifests, PostgreSQL size, Timeline, logs, caches, temporary/failed/orphan
  files, screenshots, application assets, derived/export artifacts, and
  Dataset Candidate refs cannot contribute because the query reads only the
  accepted Photo Catalog column;
- database failure returns the registered safe failure and never falls back to
  a filesystem scan.

## Protected status and consumer matrix

- Active Boss, Engineer, and Consultant sessions may read the Farm-wide
  status; missing/invalid/expired/disabled session or membership fails through
  existing auth codes.
- Response and OpenAPI match the exact `PhotoStorageStatus` shape, use
  `Cache-Control: no-store`, and contain no upload/server/acknowledgment state.
- There is no prompt mutation endpoint, table, Timeline event, or status
  transition.
- Two authenticated Accounts independently load the same Farm pressure. A
  consumer model may locally close `acknowledge` or `dismiss`; a fresh request
  remains eligible while pressure is above threshold, Account change discards
  local state, and `sync_status` remains `local_only`.

## Redaction matrix

The same configured secret corpus is exercised through actual current output
paths for:

- settings/log and safe API error text;
- Timeline append;
- retained history/export serialization;
- photo manifest serialization;
- Agent Chat Bus and UI Feed serialization;
- generic Agent Runtime request assembly;
- Vision Observation, Plant State, Hydroponics Advisor, Safety Gate, Task and
  Follow-Up, and Companion request assembly;
- Dataset Governance and Training Data Curator requests through their shared
  Dataset Agent runtime flow.

Every raw secret must be absent. Tests also prove that source credentials were
not mutated and sanitizer failures expose only safe registered errors. Because
the brownfield tree has no frontend/screenshot path, FT-015 proves that absence;
FT-016 owns the later browser capture check.

Timeline and retained-history/export results are independently decisive.
Generic and competence-specific provider requests are likewise independent
owner results. Agent Bus and UI Feed remain one result because the current
guarded publication service derives both sanitized projections and commits
them atomically. The two Dataset Agent requests remain one result because
their thin adapters use the same post-TASK-060 shared runtime flow and provider
call site.

## Gates

- focused backend tests for each task-owned result;
- applicable auth/photo/history/agent regressions after redaction changes;
- full deterministic backend regression for the cross-surface redaction gate;
- `node scripts/mb-lint.mjs` and `git diff --check`;
- no external provider, network, upload/server, frontend scaffold, or live LAN
  smoke is required.
