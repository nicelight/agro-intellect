---
description: Product brief (C4 L1): что это, для кого, core value, ограничения.
status: draft
---
# Product

## What this is

Agro Intellect MVP is a local-first Web App/PWA for monitoring one hydroponic tomato, `tomato_001`, and a training ground for AI-first development of agentic agricultural monitoring systems.

The product turns daily observations, photos, manual pH/EC measurements, agent conclusions, safety decisions, human approvals, tasks, outcomes, and dataset metadata into traceable evidence. The immediate user value is a useful personal tomato assistant; the longer-term value is reusable architecture and governance practice for a future farm-scale agentic system.

## Core value

One small plant becomes a controlled environment for disciplined agentic product development:

- the user gets a daily monitoring assistant for `tomato_001`;
- every observation and recommendation is traceable through runtime state, event refs, photo artifacts, and audit logs;
- physical-action advice is constrained by fresh data, Safety Gate checks, and human approval;
- future training/evaluation data is protected from raw agent hypotheses and weak evidence.

## Audience

- Primary user: the project owner acting as Human Architect, Product Owner, Safety Owner, QA Gatekeeper, Domain Learner, and operator of one hydroponic tomato.
- Product user role: one person caring for `tomato_001` through daily observation, photo upload, pH/EC entry, cautious recommendations, approvals, tasks, and follow-up.
- Future reference user: farm operators or agronomists in a future farm-scale system; not an MVP user.

## Primary user flow

1. The system starts the daily ritual for `tomato_001` with a short check-in prompt.
2. The user records observations, uploads one or more photos, and enters pH/EC when measured.
3. The system stores photo files, photo catalog records, initial capture manifests, PostgreSQL/read-model state, and append-only timeline events.
4. Single-competence agents publish concise structured conclusions through project-owned envelopes and the Agent Chat Bus.
5. The Safety Gate blocks or converts risky physical-action advice into pending approval flows.
6. The Companion Agent presents a short user-facing response and safe next steps.
7. Task and follow-up records capture missing data, approved human actions, and outcomes after 1-3 days.
8. Dataset governance metadata preserves provenance, evidence refs, review state, split eligibility, and `can_train_on` restrictions.

## Constraints

- Tech stack: Python/FastAPI backend, React/Next.js/PWA frontend, Agno SDK as execution SDK inside the monolith, PostgreSQL/read model, local file storage, JSON photo manifests, and `timeline.jsonl`.
- Runtime authority: PostgreSQL/read model owns mutable operational state; `timeline.jsonl` is append-only audit/export; photo files and manifests are dataset/export artifacts; Agent Chat Bus is working domain context; UI Feed is presentation; Agno is not a source of truth.
- Safety: no physical plant-system change may proceed without fresh data where relevant, Safety Gate pass, and human approval. MVP action tasks are human-performed checklist/task records, not automated device commands.
- Dataset integrity: agent hypotheses are not confirmed facts and cannot become trainable without evidence, split, status, confirmation source, and curator decision rules.
- Low maintenance: keep the MVP local, small, reversible, and focused on one plant. Avoid production SaaS, multi-user tenancy, full dataset registry, complex sync, sensor runtime dependency, and farm-scale abstractions before the MVP proves the core workflow.
- Non-goals: autopilot control, pumps, dosing, pH/EC adjustment, light control, direct physical actuation, production SaaS, commercial farm management scope, storing photo binaries in PostgreSQL/InfluxDB, InfluxDB runtime dependency before sensors, Agno Team `coordinate`, raw reasoning as facts, and training on unreviewed agent labels.
