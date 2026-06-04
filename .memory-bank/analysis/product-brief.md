---
description: Product Brief input contract for MVP v2 PRD.
status: draft
type: product-brief
last_updated: 2026-06-04
---
# Product Brief

## Metadata

- Status: draft
- Decision: proceed
- Source artifacts:
  - [project_dossier_v2.md](../../project_dossier_v2.md): upstream MVP v2 dossier.
  - [.memory-bank/constitution.md](../constitution.md): amended governing policy for bounded local-first Farm workspace and Companion governance.
  - [.memory-bank/invariants.md](../invariants.md): cross-cutting guardrails.
  - [.memory-bank/glossary.md](../glossary.md): active MVP v2 vocabulary.
  - [.memory-bank/analysis/mvp-scope-expansion-integration-plan.md](mvp-scope-expansion-integration-plan.md): MVP v2 feature-scope input.
  - [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](accounts-farm-access-admin-analysis.md): Accounts/Farm/Admin analysis.
  - [.memory-bank/analysis/companion-issue-stack-decision-governance.md](companion-issue-stack-decision-governance.md): Companion governance analysis.
  - `agents-best-practices` skill: guiding doctrine for the project's shared provider-neutral agent harness direction and its relevant subskill/reference areas.

## 1. One-liner

Agro Intellect MVP v2 is a local-first Farm workspace and AI-first agentic development
training ground for role-scoped Plant operations, starting with `tomato_001` as the
initial Plant.

## 2. Target Users

- `Boss`: local Farm owner/admin who manages Accounts, roles, Plants, per-Plant access, and admin audit.
- `Engineer`: operational user for assigned Plants; performs check-ins, photos, measurements, tasks, and permitted approvals.
- `Consultant`: advisory/read/comment user for granted Plant context; no operational authority by default.
- Project owner / AI-first development operator: uses the product to learn and validate agentic architecture, Memory Bank workflow, source-of-truth boundaries, and safety governance.

## 3. Problem

The project needs a useful Plant operations tool and a realistic AI-first architecture
training ground. MVP v1 proved the single-user tomato direction, but it did not exercise
the harder boundaries that will matter for future farm-scale systems: local Accounts,
role-scoped access, Farm/Plant authority, permission-aware agent context, Companion
governance, admin audit, and strict safety separation.

## 4. Current Alternatives

- Manual notes, photos, and spreadsheets: simple but weak on traceability, safety, and dataset governance.
- Generic chat/LLM advice: useful for conversation but unsafe as source of truth and weak on role/access boundaries.
- Commercial farm-management software: too broad and SaaS-oriented for the current local AI-first learning goal.
- Single-user MVP v1 flow: too narrow to validate Accounts/Farm/Admin, role-scoped access, and governance decisions.

## 5. Value Proposition

MVP v2 gives a bounded local Farm workspace where humans and product agents can work
with Plants safely and traceably. The product stays small enough for MVP execution while
testing the important future-facing patterns: ActorContext, per-Plant access, one shared
agent harness/control plane, single-competence agent profiles, scoped long-term agent
memory for multi-cycle Plant analysis, Agent Chat Bus boundaries, UI Feed isolation,
Safety Gate enforcement, Companion `DecisionRecord` governance, task/follow-up loops,
and dataset evidence hygiene.

## 6. Product Concept

The first product surface is a Web App/PWA backed by a local modular monolith. A Boss
sets up one local Farm workspace, creates or migrates Plants, manages local Accounts,
assigns roles, grants per-Plant access, and sees durable admin audit. Authorized users
select a Plant, run daily check-ins, upload photos, enter observations and pH/EC
measurements, receive cautious agent-assisted outputs, handle Safety Gate prompts,
create or complete tasks, and record follow-up outcomes.

Companion helps coordinate discussion through explicit typed governance state:
`IssueStack`, `HumanAttentionNeeded`, `CompanionProposal`, `CompanionConclusion`, and
`DecisionRecord`. Companion does not become hidden authority. Governance decisions do
not authorize physical actions and do not replace Safety Gate approval.

All product agents run under one project-owned agent harness/control plane, guided by
the `agents-best-practices` skill and its relevant subskill/reference areas. The product
direction is not separate harnesses per agent. Each product agent is an explicit
single-competence profile with scoped tools, context, permissions, output contracts, and
eventually its own durable long-term memory for long-running agricultural analysis.

## 7. MVP Scope

- One local Farm workspace.
- Local Accounts and local login/session baseline.
- Role presets: Boss, Engineer, Consultant.
- FarmMembership and ActorContext for authorization, attribution, UI visibility, agent context filtering, tasks, approvals, and audit.
- Multiple Plants, with `tomato_001` as the initial migrated Plant.
- Plant lifecycle: create, archive, restore, and retain history.
- Per-Plant access grants.
- Minimal Boss Admin Surface: personnel list, local-only user add/invite, role assignment, Plant list, Plant lifecycle, access grants, durable audit records, and admin audit view.
- Daily Plant operations: check-in, observations, photo upload, manual pH/EC, plant card, history, recommendations, tasks, approvals, and follow-up.
- Photo catalog, local files, `sha256`, initial capture manifests, export-ready refs, and timeline audit.
- Product agents with single-competence boundaries and permission-aware context.
- One shared provider-neutral agent harness/control plane for all product agents, guided by `agents-best-practices`.
- Per-agent scoped long-term memory direction for long-running Plant processes; memory must be durable, auditable, source-ref backed, permission-aware, and retrieved through the shared harness context builder.
- Agent Chat Bus, MessageEnvelope, UI Feed isolation, concise outputs, and controlled spoiler notes.
- Safety Gate for physical-action wording and authorized human approval before human-performed action tasks.
- Companion governance state and decision path.
- Dataset lifecycle fields, evidence refs, trainability guardrails, and `can_train_on=false` by default.
- Local privacy, `local_only` sync status, 200 MB local storage prompt without implying server upload.

First-demo boundary:
- Must work: one local Farm, local login/session, Boss plus at least one Engineer path, `tomato_001`, Plant selector with access check, daily check-in, photo upload with `photo_id`/file/`sha256`/manifest/catalog row, manual pH/EC, Bus/UI Feed split, real LLM/model-backed product agents over actual scoped Plant data, Vision Observation over actual uploaded photo data, Plant State trust statuses, Hydroponics Advisor missing-data behavior, Safety Gate, tasks/follow-up, visible Companion `HumanAttentionNeeded` and proposal/decision path, dataset fields, timeline audit/export, and local storage prompt.
- May defer from first demo: advanced Boss Admin Surface, full role matrix, sync UI details, and sensor runtime.
- Deferred from first demo: Consultant UI/path, while Consultant remains in MVP v2 product scope.
- Runtime/demo boundary: fake, mock, hardcoded, or stubbed product-agent outputs do not satisfy MVP acceptance criteria. Test-only mocks may exist for automated tests, but not as the MVP runtime path.

## 8. Non-goals

- Production SaaS.
- Hosted/cloud sync as an MVP requirement.
- Billing or subscription boundaries.
- Enterprise identity provider.
- Email delivery, password recovery, hosted account recovery, enterprise IdP, or SaaS tenancy for local user add/invite.
- Multi-Farm tenancy unless a later PRD/spec stage adds it.
- Broad commercial farm-management scope.
- Microservices in place of the local modular monolith.
- Automated physical actuation, pumps, dosing, pH/EC correction, light-control commands, autowatering, or autodosing.
- Agno as a source of truth or replacement for the domain-owned Agent Chat Bus.
- Agno Team `coordinate` mode as domain coordinator.
- Separate ungoverned agent harnesses per product agent, hidden provider memory as source of truth, or memory/context paths that bypass project-owned authorization, audit, Safety Gate, or runtime authority.
- Complex RAG, mandatory expert panel, full dataset registry, real fine-tuning, or InfluxDB runtime dependency before real sensors exist.
- Fake, mock, hardcoded, or stubbed product-agent flows as the MVP runtime/demo path.

## 9. Success Metrics

- Boss and Engineer can complete the first authorized Plant workflow end to end on `tomato_001`.
- Every Farm/Plant route can identify who acts, in which Farm, with which role and permissions.
- Backend enforces every Farm/Plant read/mutate route and agent context builder; frontend hide/show is never sufficient.
- Users see only authorized Plants and Plant data.
- Daily check-in, photo, pH/EC, agent output, task, approval, outcome, and durable audit records remain traceable.
- UI Feed content, unapproved proposals, raw reasoning, and unauthorized Plant context never enter agent working context.
- Product agents share one harness/control-plane direction, and each agent's long-term memory remains scoped, source-ref backed, permission-aware, and non-authoritative unless promoted through the owning runtime/state rules.
- Physical-action advice fails closed unless fresh data, Safety Gate pass, and authorized human approval are present.
- Dataset candidates remain non-trainable until dataset governance rules allow them.
- First demo agent behavior is produced by real LLM/model-backed agents over actual scoped Plant data, not fake, mock, hardcoded, or stubbed outputs.

## 10. Constraints

- Constitution v2 allows bounded local-first Farm workspace scope, but keeps low maintenance non-negotiable.
- PostgreSQL/read model remains runtime authority unless a later architecture spec changes it.
- `timeline.jsonl` is audit/export only.
- Photo files and manifests are local artifacts, not mutable state authority.
- UI Feed is presentation only.
- `agents-best-practices` is the guiding doctrine for the agent harness direction; `/spec-design` must translate it into project-specific harness architecture, and `/spec-improve` must apply it feature by feature.
- Agent long-term memory is a project-owned harness concern. It cannot be hidden provider memory, raw chat replay, UI Feed replay, unapproved proposal content, or a shortcut around ActorContext, PlantAccessGrant, Safety Gate, Plant State trust, or dataset governance.
- Companion `DecisionRecord` is governance authority only within backend rules; it is not Safety Gate approval.
- Backend authorization must enforce every Farm/Plant read/mutate route and every context builder; frontend visibility controls are presentation only.
- Account, role, Plant lifecycle, and Plant access changes must create durable admin audit records, not only appear in an admin audit view.
- Local user add/invite means minimal local-only account creation/invite; no email delivery, password recovery, hosted account recovery, enterprise IdP, or SaaS tenancy.
- Local data and artifacts are private by default.
- Sessions, tokens, credentials, `.env` values, API keys, and auth material must never enter logs, timeline, manifests, Bus, UI Feed, screenshots, exports, or agent context.

## 11. Assumptions

- MVP v2 starts with exactly one local Farm workspace.
- `tomato_001` migrates into the Farm/Plant model as the initial Plant.
- Boss is the first local Account and initial Farm admin.
- Local auth/session can be minimal but must support authorization and audit attribution.
- Consultant remains in product scope, but the first demo may defer a full Consultant UI path.
- MVP product agents must run as real LLM/model-backed flows over actual user-entered or uploaded Plant data. Sensor runtime remains future-only until real sensors exist.
- The first harness implementation should be the smallest reliable shared loop; per-agent long-term memory can be introduced incrementally but must be anticipated in `/spec-design` so later growing-cycle analysis is not bolted on as hidden prompt state.
- Server sync remains future-only; MVP sync status is `local_only`.

## 12. Risks

- Scope growth from Accounts/Farm/Admin could recreate broad farm-management or SaaS complexity.
- Role and permission semantics could become too detailed before the first demo proves the workflow.
- Governance approval could be confused with Safety Gate physical-action approval.
- Unapproved Companion proposals or UI markdown could leak into agent context as facts.
- ActorContext and authorization could be enforced in UI only instead of backend routes and context builders.
- Long-term agent memory could become stale, unauthorized, overbroad, or confused with runtime authority if not scoped and retrieved through explicit harness rules.
- Dataset/export evidence could mix unauthorized Farm/Plant context if isolation is not specified early.
- The PRD may overfit to the 3000-line dossier unless `/write-prd` keeps product scope separate from design details.
- Requiring real LLM/model-backed MVP agents increases integration risk, so specs must keep adapters simple while forbidding fake runtime/demo outputs.

## 13. Closed Clarifications

The active PRD at [.memory-bank/prd.md](../prd.md) resolves the high-impact `/write-prd`
questions for MVP v2:

- Loopback is the first-demo default; LAN is optional only when explicitly enabled with auth/session/CORS controls.
- MVP uses Boss/Engineer/Consultant role presets plus PlantAccessGrant; the only MVP permission override is `plant_approve_actions`.
- Boss may approve Safety Gate physical-action proposals; Engineer may approve only with per-Plant `plant_approve_actions`; Consultant never approves.
- Consultant is read/comment/advice only and does not create domain task/recommendation records or approvals.
- Plant removal is archive/restore only; no hard delete in MVP.
- `IssueStack` is Plant-scoped in MVP.
- `DecisionRecord` may route Plant-scoped workflow and safe check/measurement/follow-up task requests, but cannot mutate Plant state or unlock physical actions.
- A new CompanionProposal for the same Plant issue supersedes the previous pending proposal; no parallel proposals.
- Agent-consumable governance summary is compact typed facts from a valid DecisionRecord only.
- MVP runtime/demo agents must be real LLM/model-backed flows over actual scoped Plant data; fake/mock/stub outputs are not acceptable as the MVP runtime path.

## 14. PRD Input Summary

Write a PRD for MVP v2 as a bounded local-first Farm workspace with local Accounts,
Boss/Engineer/Consultant roles, one local Farm, multiple Plants starting with
`tomato_001`, per-Plant access, daily Plant operations, safety-gated agent assistance,
Companion governance, task/follow-up tracking, local evidence/audit, and dataset
governance. Preserve KISS and local modular monolith architecture. Use
`agents-best-practices` as the guiding doctrine for one shared provider-neutral agent
harness/control plane, with explicit single-competence agent profiles and a scoped
long-term memory direction for each agent. Keep production SaaS, hosted sync, billing,
enterprise identity, automated actuation, broad farm management, and real fine-tuning
outside MVP.

The PRD must clarify role permissions, ActorContext, Plant lifecycle, physical-action
approval roles, Companion governance scope, `DecisionRecord` authority, first demo
scope, backend authz/audit constraints, local-only account invite limits, and migration
of `tomato_001` into the Farm/Plant model.

## 15. Decision

### Decision

proceed
