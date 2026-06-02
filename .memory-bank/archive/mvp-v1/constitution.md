---
description: Archived MVP v1 Project Constitution snapshot.
status: archived
version: 1
project_principles: ratified
ratified: 2026-05-27
last_updated: 2026-05-27
---
# Project Constitution

## Purpose

This archived snapshot defined the non-negotiable principles that guided AI agents
for MVP v1 planning, implementation, verification, and synchronization.

## Core Principles

### I. AI-First Spec-Driven Development

Agents MUST derive implementation work from explicit product, requirement, feature,
task, and workflow artifacts. Agents MUST NOT invent product scope without evidence
or user instruction.

### II. DO NOT Overengineering

Project level is `medium`: use strict specs and gates for risky zones, but avoid
enterprise overhead. Prefer KISS for ordinary MVP work; require stability-first design
for safety, data authority, dataset governance, Agent Chat Bus, MessageEnvelope,
UI Feed isolation, and other agent-contract boundaries.

### III. Memory Bank Is Durable Project Knowledge

`.memory-bank/` is the durable source of project knowledge. Chat context is temporary.
Agents MUST update Memory Bank after meaningful changes.

### IV. Schema-Backed Task Execution

Tasks MUST use the current schema-backed JSON task record model. If the framework uses
`tier: T0|T1|T2|T3`, agents MUST route execution and verification through that tier model.

### V. Risk-Based Definition of Done

Every completed task MUST have evidence appropriate to its risk and tier. Core boundary
zones require schema, contract, safety, and data integrity checks; user-facing workflows
require UI/e2e smoke when the flow exists. Small docs or local changes may use lighter
checks when they do not affect runtime, contracts, state, data, safety, or user flow.

### VI. Bounded Agent Autonomy

Product agents may analyze observations, request missing data, publish structured
conclusions, and create safe check/follow-up tasks within their competence. Plant state
cannot be promoted to confirmed without human review or follow-up evidence. Training data
curation may be mostly autonomous only when strong `evidence_refs` exist; `gold` status
requires human, expert, or batch review.

### VII. Human Gate for Physical Actions

Any action that changes the physical plant system requires fresh data, safety check,
and human approval before execution. Agents may create pending proposals or approval
tasks, but MUST NOT issue immediate commands for pH, EC, solution, pumps, dosing, or
light changes without the gate.

### VIII. Low Maintenance Non-Negotiable

Low maintenance is a critical non-negotiable. Prefer simple local architecture, minimal
infrastructure, clear source-of-truth boundaries, and reversible MVP slices. Do not add
production SaaS, multi-user architecture, complex sync, sensor runtime dependencies,
full dataset registry, or broad abstractions before the MVP needs them.

### IX. No Legacy Fallback and No Speculation

Agents MUST NOT rely on deprecated task formats, old risk models, or undocumented
assumptions. Unknowns MUST be recorded as blockers or explicit assumptions.

### X. Context Discipline

Agents SHOULD read the smallest sufficient context for the task. Higher-tier or
cross-cutting tasks MUST read relevant normative docs such as invariants, contracts,
states, testing, and workflow policies.

### XI. Synchronization

After meaningful changes, agents MUST synchronize affected Memory Bank docs, task state,
changelog, and routing files.

## Governance Decisions

- Project level: `medium`.
- Architecture priority: KISS by default, stability-first for safety, data, and agent-contract boundaries.
- Definition of Done: risk-based checks; schema/contract/safety gates are mandatory for core boundaries, UI/e2e checks for real user flows.
- Agent autonomy: plant state requires human/follow-up gate for confirmation; training data curation is mostly autonomous only with strong evidence.
- Critical non-negotiable: low maintenance.

## Governance

- Constitution has precedence over workflow habits and generated plans.
- MBB, spec-index, invariants, contracts, states, testing, and workflow docs refine this Constitution; they must not contradict it.
- Amendments must include rationale and update affected docs if needed.
- Constitution should stay short. Put concrete project rules into `invariants.md`, `contracts/*`, `states/*`, or workflow policy docs.

**Version**: 1 | **Ratified**: 2026-05-27 | **Last updated**: 2026-05-27
