---
description: "ADR-001: Local modular monolith and authority boundaries for the MVP."
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# ADR-001: Local Modular Monolith and Authority Boundaries

## ADR Status
accepted

## Context

Agro Intellect MVP must be useful for one local hydroponic tomato while acting as a training ground for AI-first agentic agricultural systems. The PRD requires low maintenance, local-first operation, explicit Safety Gate behavior, dataset governance, traceable artifacts, and source-of-truth discipline.

The project does not need production SaaS, multi-user tenancy, microservices, server sync, automated physical actuation, a full dataset registry, or sensor runtime dependencies in the MVP.

## Decision

Use a local layered modular monolith:

- Python/FastAPI backend for API, domain workflows, persistence, artifacts, timeline, agent adapters, and Safety Gate orchestration.
- React/Next.js/PWA for the operator surface.
- PostgreSQL/read model as mutable runtime authority.
- Local files for photos and immutable JSON manifests.
- `timeline.jsonl` as append-only audit/export.
- Domain-owned Agent Chat Bus and `MessageEnvelope` for agent-consumable working context.
- UI Feed as presentation only.
- Agno as execution SDK only, never as source of truth or Bus publication authority.
- Future InfluxDB/time-series store only after real sensors exist.

## Consequences

- Feature work can proceed as vertical slices without service orchestration overhead.
- Authority boundaries are testable: runtime state, audit/export, artifacts, Bus, UI, and Agno each have distinct roles.
- Safety and dataset governance remain explicit instead of implicit model behavior.
- Future farm-scale architecture remains possible, but the MVP avoids premature scale abstractions.

## Alternatives

- Split services: rejected for MVP because it adds operational overhead without PRD need.
- Agno as domain coordinator/source of truth: rejected because it violates project-owned contracts and source-of-truth discipline.
- File-only runtime state: rejected because mutable state, approvals, dataset fields, and refs need PostgreSQL authority.
- Production SaaS architecture: rejected as out of MVP scope.
