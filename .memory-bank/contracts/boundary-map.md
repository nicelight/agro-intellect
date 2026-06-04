---
description: Preliminary boundary hints for MVP v2 PRD decomposition.
status: active
owner: architecture
last_updated: 2026-06-03
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/invariants.md
  - .memory-bank/glossary.md
---
# Boundary Map

This is a pre-PRD framing artifact only. It intentionally does not define endpoints,
schemas, auth policy details, OpenAPI shapes, database migrations, or error codes.

| Boundary | Purpose | Direction | Owner | Known Constraints | Questions |
|---|---|---|---|---|---|
| Local app session -> ActorContext | Resolve who acts in which Farm, with which role and Plant permissions. | UI/API request into backend application boundary. | /spec-design | Backend authorization is mandatory for every Farm/Plant route and context builder. Secrets/session material must be redacted. | Exact session/token lifecycle belongs to /spec-design. |
| Boss Admin Surface -> Farm/Account/Plant administration | Manage personnel, roles, Plant lifecycle, Plant access, and admin audit. | Human UI command into backend admin services. | /prd then /spec-design | One local Farm only; no SaaS tenancy, email delivery, hosted recovery, or enterprise identity. Admin changes create durable audit. | Minimal first-demo admin surface may be smaller than full MVP admin capability. |
| Plant operations UI -> runtime state | Record observations, pH/EC, photos, tasks, approvals, and outcomes. | Human UI command into backend Plant services. | /prd then /spec-design | All operations are Farm/Plant/Actor scoped. Archived Plants are removed from normal operations but retained for authorized history. | Exact route grouping and state transitions belong to /spec-design and feature specs. |
| Photo intake -> local artifacts and catalog | Store photo file, metadata, sha256, initial capture manifest, and audit/export refs. | Upload/capture into filesystem plus runtime catalog/audit. | /spec-design | Local artifacts are not mutable runtime authority. Photo details must be re-specified for MVP v2 before task decomposition. | Exact manifest fields and storage layout belong to later specs. |
| Runtime state -> timeline audit/export | Preserve append-only trace and export references. | Backend persistence into audit/export event stream. | /spec-design | Timeline is not primary mutable state. Runtime authority remains PostgreSQL/read model. | Exact event taxonomy belongs to /spec-design. |
| Runtime state -> Agent Chat Bus | Publish validated agent-consumable events. | Backend/domain adapters into Bus. | /spec-design | Bus is domain-owned working context; raw model output, UI Feed, raw chat, and unapproved proposals cannot bypass adapters. | Exact BusEventEnvelope contract belongs to /spec-design. |
| Agent execution -> MessageEnvelope | Convert real model-backed output into project-owned structured output. | Agno/model execution through domain adapter into publishable output. | /spec-design | Agno is execution layer only. MVP runtime/demo cannot use fake/stub product-agent outputs. Runtime decision is project-owned. | Exact adapter contract belongs to /spec-design. |
| MessageEnvelope -> UI Feed | Display human-facing agent messages, cards, prompts, and spoiler notes. | Publishable domain output into presentation stream. | /spec-design | UI Feed is presentation-only and unavailable as agent working context. | Exact UIFeedEvent projection belongs to /spec-design. |
| Physical-action advice -> Safety Gate | Block or route risky wording before display/action tracking. | Agent/advisor output into safety policy boundary. | /spec-design | Fresh data alone is insufficient. Requires Safety Gate pass, authorized approval, and human-performed task tracking. No automated actuation. | Exact freshness and action taxonomy belong to later specs. |
| Companion governance -> DecisionRecord | Turn human-approved Plant-scoped governance proposal into typed binding workflow direction. | Companion proposal plus valid human decision into backend governance record. | /spec-design | DecisionRecord is not Safety Gate approval, Plant-state evidence, or physical-action unlock. Raw proposal text/rationale/chat stay non-consumable. | Exact proposal/decision state machine belongs to /spec-design. |
| Runtime evidence -> dataset governance | Preserve evidence refs and trainability guardrails for future learning loop. | Photo/measurement/outcome/review evidence into dataset lifecycle fields. | /spec-design | Dataset items are non-trainable by default. UI Feed, timeline snapshots, manifests, and raw agent output never grant trainability by themselves. | Full dataset registry and fine-tuning are out of MVP. |
