---
description: Preliminary boundary hints for MVP v2 PRD decomposition.
status: active
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/invariants.md
  - .memory-bank/glossary.md
---
# Boundary Map

This is a pre-PRD framing artifact only. It intentionally does not define
endpoints, schemas, auth policy details, OpenAPI shapes, database migrations, or
error codes. Global boundary rules are promoted into the active global specs;
feature-required detail belongs to discovered canonical subject specs created
or extended by `/prd-to-tasks FT-<NNN>` before task slicing.

| Boundary | Purpose | Direction | Change route | Known Constraints | Questions |
|---|---|---|---|---|---|
| Local app session -> ActorContext | Resolve who acts in which Farm, with which role and Plant permissions. | UI/API request into backend application boundary. | /spec-design | Backend authorization is mandatory for every Farm/Plant route and context builder. Secrets/session material must be redacted. | Exact session/token lifecycle belongs to `/prd-to-tasks FT-001`. |
| Boss Admin Surface -> Farm/Account/Plant administration | Manage personnel, roles, Plant archive/restore, Plant access, Plant list, and admin audit. Plant creation is also available to active Engineers through the Farm/Plant boundary, not this admin boundary. | Human UI command into backend admin services. | /prd then /spec-design | One local Farm only; no SaaS tenancy, email delivery, hosted recovery, or enterprise identity. Admin changes create durable audit. | Minimal first-demo admin surface may be smaller than full MVP admin capability. |
| Plant operations UI -> runtime state | Record observations, pH/EC, photos, tasks, approvals, and outcomes. | Human UI command into backend Plant services. | /prd then /spec-design | All operations are Farm/Plant/Actor scoped. Archived Plants are removed from normal operations but retained for authorized history. | Exact route grouping and state transitions belong to applicable canonical specs created or extended by `/prd-to-tasks FT-<NNN>`. |
| Photo intake -> local artifacts and catalog | Store photo file, metadata, sha256, initial capture manifest, and audit/export refs. | Upload/capture into filesystem plus runtime catalog/audit. | /spec-design | Local artifacts are not mutable runtime authority. Photo details must be re-specified for MVP v2 before task slicing. | Exact manifest fields and storage layout belong to `/prd-to-tasks FT-005`. |
| Runtime state -> timeline audit/export | Preserve append-only trace and export references. | Backend persistence into audit/export event stream. | /spec-design | Timeline is not primary mutable state. Runtime authority remains PostgreSQL/read model. | Exact event taxonomy belongs to `/prd-to-tasks FT-006`. |
| Runtime state -> Agent Chat Bus | Publish validated agent-consumable events. | Backend/domain adapters into Bus. | /spec-design | Bus is domain-owned working context; raw model output, UI Feed, raw chat, and unapproved proposals cannot bypass adapters. | Exact BusEventEnvelope refinements belong to applicable canonical specs created or extended by `/prd-to-tasks FT-<NNN>`. |
| Agent execution -> MessageEnvelope | Convert real model-backed output into project-owned structured output. | Agno/model execution through domain adapter into publishable output. | /spec-design | Agno is execution layer only. MVP runtime/demo cannot use fake/stub product-agent outputs. Runtime decision is project-owned. | Exact adapter contract belongs to `/prd-to-tasks FT-007`. |
| MessageEnvelope -> UI Feed | Display human-facing agent messages, cards, prompts, and spoiler notes. | Publishable domain output into presentation stream. | /spec-design | UI Feed is presentation-only and unavailable as agent working context. | Exact UIFeedEvent projection belongs to `/prd-to-tasks FT-008` and `/prd-to-tasks FT-016`. |
| Physical-action advice -> Safety Gate | Block or route risky wording before display/action tracking. | Agent/advisor output into safety policy boundary. | /spec-design | Fresh data alone is insufficient. Requires Safety Gate pass, authorized approval, and human-performed task tracking. No automated actuation. | Exact freshness and action taxonomy belong to `/prd-to-tasks FT-011`. |
| Companion governance -> DecisionRecord | Turn human-approved Plant-scoped governance proposal into typed binding workflow direction. | Companion proposal plus valid human decision into backend governance record. | /spec-design | DecisionRecord is not Safety Gate approval, Plant-state evidence, or physical-action unlock. Raw proposal text/rationale/chat stay non-consumable. | Exact proposal/decision state machine belongs to `/prd-to-tasks FT-013`. |
| Runtime evidence -> dataset governance | Preserve evidence refs and trainability guardrails for future learning loop. | Photo/measurement/outcome/review evidence into dataset lifecycle fields. | /spec-design | Dataset items are non-trainable by default. UI Feed, timeline snapshots, manifests, and raw agent output never grant trainability by themselves. | Full dataset registry and fine-tuning are out of MVP. |
