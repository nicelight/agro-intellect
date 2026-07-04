---
description: Project Constitution — governing principles for AI-first development.
status: active
version: 3
project_principles: ratified
ratified: 2026-05-27
last_updated: 2026-07-03
---
# Project Constitution

## Purpose

This Constitution defines the non-negotiable principles that guide AI agents when planning, implementing, verifying, and synchronizing project work for Agro Intellect MVP.

## Core Principles

### I. AI-First Spec-Driven Development

Agents MUST derive implementation work from explicit product, requirement, feature, task, and workflow artifacts. Agents MUST NOT invent product scope without evidence or user instruction.

### II. DO NOT Overengineering

Project level is `medium`: use risk-aware specs and checks for risky zones, but avoid enterprise overhead. Prefer KISS for ordinary MVP work and stability-first design for safety, data authority, account/farm access boundaries, Companion governance decisions, dataset governance, Agent Chat Bus, MessageEnvelope, UI Feed isolation, and other agent-contract boundaries.

### III. Memory Bank Is Durable Project Knowledge

`.memory-bank/` is the durable source of project knowledge. Chat context is temporary. Agents MUST update Memory Bank after meaningful changes.

### IV. Schema-Backed Task Execution

Tasks MUST use the current schema-backed JSON task record model. The `tier: T0|T1|T2|T3` field classifies risk and recommends an execution profile; it does not by itself create mandatory protocol, verification, semantic-review, checkpoint, doctor, or synchronization gates.

### V. Risk-Based Definition of Done

Every task SHOULD have evidence proportionate to its actual risk. Schema, contract, safety, data-integrity, UI/e2e, `/verify`, `/red-verify`, protocol, checkpoint, doctor, and synchronization checks are recommended tools, not automatic closure blockers for T2/T3. The explicit owner or scheduler may combine, reorder, skip, or accept residual risk based on the concrete change. Product safety rules, authorization boundaries, source-of-truth contracts, and explicit user decisions remain binding.

### VI. Bounded Agent Autonomy

Product agents may analyze observations, request missing data, publish structured conclusions, and create safe check/follow-up tasks within their competence. Plant state cannot be promoted to confirmed without human review or follow-up evidence. Companion governance may organize discussion and propose decisions only through explicit typed state and human-authorized `DecisionRecord` semantics. Training data curation may be mostly autonomous only when strong `evidence_refs` exist; `gold` status requires human, expert, or batch review.

### VII. Human Gate for Physical Actions

Any action that changes the physical plant system requires fresh data, safety check, and human approval before execution. Agents may create pending proposals or approval tasks, but MUST NOT issue immediate commands for pH, EC, solution, pumps, dosing, or light changes without the gate.

### VIII. Low Maintenance and Bounded MVP Scope

Low maintenance is a critical non-negotiable. Prefer simple local architecture, minimal infrastructure, clear source-of-truth boundaries, and reversible MVP slices. The MVP may include a bounded local-first Farm workspace with local Accounts, Boss/Engineer/Consultant roles, per-Plant access, multiple Plants, and Companion governance when explicitly specified by PRD/specs. Do not add production SaaS, hosted/cloud sync as an MVP requirement, billing/subscription boundaries, enterprise identity, microservices, complex sync, sensor runtime dependencies, full dataset registry, automated physical actuation, or broad farm-management scope before a later product stage explicitly requires them.

### IX. No Legacy Fallback and No Speculation

Agents MUST NOT rely on deprecated task formats, old risk models, or undocumented assumptions. Unknowns MUST be recorded as blockers or explicit assumptions.

### X. Context Discipline

Agents SHOULD read the smallest sufficient context for the task. Higher-tier or cross-cutting tasks SHOULD read relevant normative docs such as invariants, contracts, states, testing, and workflow policies.

### XI. Synchronization

After meaningful changes, agents SHOULD synchronize affected Memory Bank docs, task state, changelog, and routing files. Synchronization timing is owner-controlled and is not an automatic T2/T3 closure gate.

## Governance Decisions

- Project level: `medium`.
- Architecture priority: KISS by default, stability-first for safety, data, and agent-contract boundaries.
- Definition of Done: risk-informed and owner-controlled. T2/T3 workflow checks are recommendations; missing process artifacts produce warnings rather than automatic closure blockers.
- T2/T3 execution amendment on 2026-07-03: protocol depth, task gates, `/verify`, `/red-verify`, human checkpoint, strict doctor, and `/mb-sync` are advisory unless the explicit owner makes a specific check mandatory for a concrete task/run.
- Agent autonomy: plant state requires human/follow-up gate for confirmation; training data curation is mostly autonomous only with strong evidence.
- MVP scope amendment on 2026-06-01: bounded local-first Farm workspace, local Accounts, role-scoped access, multiple Plants, and Companion governance are allowed in MVP after PRD/spec promotion; production SaaS and broad farm-management scope remain excluded.
- Critical non-negotiable: low maintenance.

## Governance

- Constitution has precedence over workflow habits and generated plans.
- MBB, spec-index, invariants, contracts, states, testing, and workflow docs refine this Constitution; they must not contradict it.
- Amendments must include rationale and update affected docs if needed.
- Constitution should stay short. Put concrete project rules into `invariants.md`, `contracts/*`, `states/*`, or workflow policy docs.

**Version**: 3 | **Ratified**: 2026-05-27 | **Last updated**: 2026-07-03
