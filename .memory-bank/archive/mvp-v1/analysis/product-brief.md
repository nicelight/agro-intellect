---
description: Product Brief input contract for PRD.
status: draft
type: product-brief
---
# Product Brief

## Metadata

- Status: draft
- Decision: proceed
- Source artifacts:
  - [project_dossier.md](../../project_dossier.md)
  - [.memory-bank/analysis/brainstorming/BR-001.md](brainstorming/BR-001.md)

## 1. One-liner

Agro Intellect MVP is a personal tomato-monitoring assistant and AI-first training ground for learning how to design, implement, test, and govern agentic agricultural monitoring systems.

## 2. Target Users

- Primary user: the project owner acting as Human Architect, Product Owner, Safety Owner, QA Gatekeeper, and Domain Learner.
- Near-term user role: one person caring for one hydroponic tomato and using the system for daily observation and decision support.
- Future reference user: operators/agronomists in a farm-scale agentic monitoring system, but not as MVP users.

## 3. Problem

The user wants practical experience building agentic systems without jumping directly into a complex commercial farm product. A small hydroponic tomato provides a controlled environment for learning agent boundaries, workflow orchestration, state over time, multimodal observation, safety gates, human approval, data governance, and future learning loops.

## 4. Current Alternatives

- Manual notes, photos, and reminders without structured state or traceability.
- Ad hoc use of a general LLM or vision model without durable plant history, safety gates, or dataset governance.
- Building a large farm-management system too early, before the architecture and agent workflow patterns are proven.

## 5. Value Proposition

The MVP turns one plant into a disciplined learning environment: every daily observation, photo, recommendation, approval, task, and outcome becomes traceable evidence. The user gets a useful tomato assistant now and reusable engineering patterns for future farm-scale agentic systems later.

## 6. Product Concept

The first product is a Web App/PWA where the user performs a daily check-in for `tomato_001`, uploads photos, enters manual pH/EC and observations, receives cautious agent conclusions, approves risky actions, and tracks follow-up tasks.

The product uses single-competence agents: Companion, Vision Observation, Plant State, Hydroponics Advisor, Task & Follow-up, Safety Gate, Dataset Governance, and Training Data Curator. Agno may execute agents and workflows, but domain truth flows through project-owned contracts such as Agent Chat Bus, `MessageEnvelope`, UI Feed, PostgreSQL state, and `timeline.jsonl`.

## 7. MVP Scope

- One plant: `tomato_001`.
- Daily check-in and user observation capture.
- Photo upload with required `plant_id`, filesystem storage, and JSON manifest snapshot.
- Manual pH/EC entry.
- PostgreSQL runtime state for plant, photo catalog, tasks, approvals, review/dataset/sync statuses, and event references.
- Append-only `timeline.jsonl` audit/export log.
- Mock or real Vision Observation Agent.
- Structured agent conclusions through domain envelopes.
- UI-only spoiler notes that are not consumable by agents.
- Hydroponics Advisor with cautious recommendations and no hard dosing commands without required context.
- Safety Gate and human approval for physical actions.
- Task/follow-up flow and dataset statuses.

## 8. Non-goals

- Production SaaS, multi-user support, or full commercial farm management.
- Autopilot control, pumps, dosing, pH/EC adjustment, light control, or other physical actions.
- Complex RAG, expert panel, full dataset registry, or real model fine-tuning.
- Storing photo binaries in PostgreSQL or InfluxDB.
- Making InfluxDB a runtime dependency before real sensors exist.
- Using Agno Team `coordinate` as a domain coordinator.
- Treating agent hypotheses as confirmed facts or training data.

## 9. Success Metrics

- A complete daily flow can be run for `tomato_001`: check-in, photo, pH/EC, agent conclusions, safety review, task/follow-up, and timeline entry.
- Every photo has `plant_id`, `photo_id`, file reference, JSON manifest, and traceable event references.
- Dangerous recommendations are blocked or converted into pending approval tasks.
- Agent outputs are structured, concise by default, and separated from UI-only explanation notes.
- Dataset items cannot become trainable unless status, split, confirmation source, and evidence rules are satisfied.
- Core schemas and boundary rules are covered by tests before feature decomposition is considered done.

## 10. Constraints

- `project_dossier.md` is upstream dossier context for the brief.
- After `/spec-init` and `/spec-design`, `.memory-bank/spec-index.md` and linked specs become normative.
- PostgreSQL/read model is runtime authority for mutable operational state.
- Photo files plus generated JSON snapshots are dataset/export artifacts, not mutable runtime authority.
- `timeline.jsonl` is append-only audit/export log.
- Agno is an execution SDK only; Agno invocation is not Agent Chat Bus publication.
- Physical state changes require fresh data, Safety Gate, and human approval.
- KISS applies: implement the smallest verifiable MVP slices.

## 11. Assumptions

- The first working demo can use mock Vision while preserving the same output contracts as a future real vision model.
- The learning platform value and personal tomato assistant value are both important, with learning value primary.
- Sensors, sync server, and InfluxDB come after the local MVP proves the core workflow.
- Open product details can be clarified in `/constitution` and `/write-prd` without blocking this brief.

## 12. Risks

- Overbuilding a farm-scale system before validating the tomato MVP workflow.
- Letting Agno capabilities replace explicit project contracts and domain authority.
- Mixing agent hypotheses, UI explanations, and confirmed data.
- Producing unsafe physical-action recommendations without fresh pH/EC, safety check, and human approval.
- Polluting future datasets with raw or agent-labeled examples.
- Creating too many abstractions before schema and boundary tests exist.

## 13. Open Questions

- What exact Definition of Done should apply to the first end-to-end workflow: schema tests, API tests, UI smoke, or all of them?
- Should the first demo default to mock Vision and make real vision a later switch?
- Should the first dataset governance implementation include the full lifecycle fields immediately or start with a minimal subset that preserves migration safety?
- Should safety approval cover only pH/EC/dosing/light/pumps in the first demo, or also manual interventions such as pruning or transplanting?

## 14. PRD Input Summary

Write a PRD for a greenfield AI-first MVP that turns one hydroponic tomato into a traceable agentic monitoring workflow. The PRD should preserve the dual purpose: practical personal assistant now, architecture and learning loop training ground for future farm-scale systems later. The MVP must prioritize source-of-truth discipline, single-competence agents, safe human-in-the-loop recommendations, structured outputs, photo/data traceability, schema validation, and dataset governance.

## Decision

proceed
