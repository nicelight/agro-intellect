---
description: Requirements (REQ IDs) and traceability matrix for Agro Intellect MVP v2.
status: active
owner: product
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/analysis/product-brief.md
  - .memory-bank/invariants.md
  - .memory-bank/spec-backbone.md
---
# Requirements

## Status Model

- Document `status`: `draft|active|deprecated|archived`
- RTM `Lifecycle`: `planned|implemented|verified`

## REQ List

- `REQ-001` Single local Farm workspace: MVP MUST support exactly one local Farm workspace.
- `REQ-002` Local Accounts and sessions: MVP MUST support local Accounts and a local login/session baseline sufficient for authorization and audit attribution.
- `REQ-003` Role presets and ActorContext: MVP MUST support Boss, Engineer, and Consultant role presets, FarmMembership, and ActorContext for every Farm/Plant read, mutation, context-builder path, task, approval, and audit record.
- `REQ-004` Plant lifecycle: MVP MUST support multiple Plants in the local Farm, `tomato_001` as the initial Plant, and Plant create/archive/restore with retained history/audit.
- `REQ-005` Per-Plant access: MVP MUST support PlantAccessGrant for per-Plant visibility and work authorization, with `plant_approve_actions` as the only MVP per-permission override.
- `REQ-006` Boss admin and audit: Boss Admin Surface MUST support personnel, local-only account add/invite, role assignment, Plant lifecycle, Plant access management, durable admin audit, and minimal admin audit view.
- `REQ-007` Authorized daily Plant operations: authorized users MUST be able to select only authorized Plants and perform check-in, observations, photo upload, manual pH/EC, Plant card/history, tasks, approvals, and follow-up.
- `REQ-008` Photo artifact integrity: photo intake MUST store local files, catalog metadata, `sha256`, initial capture manifest, export-ready refs, and timeline audit refs.
- `REQ-009` Runtime authority and timeline: PostgreSQL/read model MUST remain mutable runtime authority; timeline JSONL MUST remain append-only audit/export only.
- `REQ-010` Shared AgentHarness: product agents MUST share one project-owned provider-neutral AgentHarness/control plane with explicit AgentProfile definitions.
- `REQ-011` Harness loop and permissions: AgentHarness MUST own model calls, tool/action proposal validation, permission decisions, approval pauses, structured observations, context updates, traces, evals, and budgets.
- `REQ-012` Agent memory governance: each product agent MUST be designed for scoped long-term memory that is project-owned, durable, source-ref backed, permission-aware, auditable, retrievable only through the shared context builder, and non-authoritative by itself.
- `REQ-013` Real model-backed runtime: MVP runtime/demo product agents MUST use real LLM/model-backed flows over actual scoped Plant data; Vision Observation MUST process actual uploaded photo data through a real vision-capable model or real vision model integration.
- `REQ-014` Agent publication and UI isolation: agent-originated output MUST pass runtime decision, MessageEnvelope, Agent Chat Bus, and UI Feed boundaries; UI Feed and unapproved proposal content MUST NOT become agent working context.
- `REQ-015` Plant state and advisor behavior: Plant State and Hydroponics Advisor behavior MUST preserve trust statuses, ask for missing/stale data when needed, and avoid confirming hypotheses without human review or follow-up evidence.
- `REQ-016` Safety Gate: physical-action advice MUST fail closed unless fresh data, Safety Gate pass, authorized human approval, and task/action tracking exist.
- `REQ-017` Human approval and task loop: approved physical actions MUST create only human-performed `action_task` records, never automated execution; tasks, approvals, and follow-up outcomes MUST preserve evidence and audit.
- `REQ-018` Companion governance state: Companion governance MUST use explicit Plant-scoped typed state for IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord.
- `REQ-019` Companion proposal and DecisionRecord semantics: no parallel pending CompanionProposal may exist for the same Plant issue; DecisionRecord may direct allowed workflow effects but MUST NOT mutate Plant state, create `action_task`, authorize physical action, replace Safety Gate approval, or turn raw chat into fact.
- `REQ-020` Approved governance summary: agents MAY consume only compact approved governance summary facts derived from a valid DecisionRecord, never raw proposal text, rationale, chat, UI markdown, or unapproved discussion.
- `REQ-021` Dataset governance: dataset candidates MUST remain non-trainable by default and require evidence refs before any future trainability change.
- `REQ-022` Local privacy, deployment, and sync: MVP MUST remain local-first/private by default, use loopback by default, require controls for explicit LAN mode, and keep sync status `local_only`.
- `REQ-023` Secret redaction: sessions, tokens, credentials, `.env` values, API keys, and auth material MUST NOT enter logs, timeline, manifests, Bus, UI Feed, screenshots, exports, or agent context.
- `REQ-024` Local storage prompt: local storage prompt MUST appear when local dataset/photo storage exceeds 200 MB and MUST NOT imply upload or server availability.

## Out Of Scope

- Production SaaS or hosted cloud sync as an MVP requirement.
- Billing, subscriptions, enterprise identity, hosted account recovery, SaaS tenancy, or email delivery.
- Multi-Farm tenancy or multi-Farm membership.
- Broad commercial farm-management scope.
- Microservices instead of local modular monolith.
- Automated physical actuation, pumps, dosing, pH/EC correction, light-control commands, autowatering, or autodosing.
- Agno as source of truth, Agent Chat Bus replacement, domain coordinator, or hidden provider memory authority.
- Separate ungoverned product-agent harnesses.
- Complex RAG, mandatory expert panels, full dataset registry, real fine-tuning, sensor runtime dependency before real sensors exist.
- Hard delete for Plant removal in MVP.
- Fake, mock, hardcoded, or stubbed product-agent runtime/demo flows.

## Traceability (RTM)

| REQ | Epic | Feature | Test | Lifecycle |
|---|---|---|---|---|
| REQ-001 | EP-001 | FT-001, FT-002 | test:farm.single-local-workspace | planned |
| REQ-002 | EP-001 | FT-001 | test:auth.local-session-attribution | planned |
| REQ-003 | EP-001 | FT-001, FT-002 | test:auth.actor-context-all-boundaries | planned |
| REQ-004 | EP-001 | FT-002 | test:plant.lifecycle-archive-restore-retention | planned |
| REQ-005 | EP-001 | FT-002 | test:auth.plant-access-grants | planned |
| REQ-006 | EP-001 | FT-003 | test:admin.audit-and-access-management | planned |
| REQ-007 | EP-002 | FT-004, FT-006, FT-013 | test:plant.authorized-daily-flow | planned |
| REQ-008 | EP-002 | FT-005 | test:photo.file-catalog-sha256-manifest | planned |
| REQ-009 | EP-002 | FT-006 | test:runtime.authority-vs-timeline | planned |
| REQ-010 | EP-003 | FT-007 | test:harness.shared-profile-control-plane | planned |
| REQ-011 | EP-003 | FT-007 | test:harness.loop-permission-observation-trace | planned |
| REQ-012 | EP-003 | FT-008 | test:harness.memory-scope-permission-non-authority | planned |
| REQ-013 | EP-003 | FT-010 | test:agents.real-model-runtime-and-vision | planned |
| REQ-014 | EP-003 | FT-009 | test:agent-output.bus-message-ui-isolation | planned |
| REQ-015 | EP-004 | FT-011 | test:plant-state.advisor-trust-missing-data | planned |
| REQ-016 | EP-004 | FT-012 | test:safety-gate.fail-closed-approval-boundary | planned |
| REQ-017 | EP-004 | FT-013 | test:tasks.approval-action-follow-up-no-actuation | planned |
| REQ-018 | EP-005 | FT-014 | test:companion.typed-plant-scoped-state | planned |
| REQ-019 | EP-005 | FT-014, FT-015 | test:companion.proposal-decision-authority | planned |
| REQ-020 | EP-005 | FT-015 | test:companion.approved-summary-context-filter | planned |
| REQ-021 | EP-006 | FT-016 | test:dataset.non-trainable-by-default | planned |
| REQ-022 | EP-006 | FT-017 | test:privacy.local-only-loopback-lan-controls | planned |
| REQ-023 | EP-006 | FT-017 | test:privacy.secret-redaction-surfaces | planned |
| REQ-024 | EP-006 | FT-016, FT-017 | test:storage.200mb-local-prompt-no-upload | planned |
