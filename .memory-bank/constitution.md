---
description: Project Constitution — governing principles for AI-first development.
status: active
version: 4
project_principles: ratified
ratified: 2026-05-27
last_updated: 2026-07-23
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

Tasks MUST use the current schema-backed JSON task record model. The
`tier: T0|T1|T2|T3` field classifies risk and selects the required execution,
protocol, verification, checkpoint, doctor, and synchronization route defined
by the current DevRails workflow contracts.

### V. Risk-Based Definition of Done

Every non-terminal task MUST satisfy the current tier route before closure.
Required schema, contract, safety, data-integrity, `/verify`, `/red-verify`,
protocol, checkpoint, doctor, and synchronization gates cannot be waived merely
to close the task. Additional checks remain risk-proportionate and must not be
invented solely to fill a category. Product safety rules, authorization
boundaries, source-of-truth contracts, and explicit user decisions remain
binding.

### VI. Bounded Agent Autonomy

Product agents may analyze observations, request missing data, publish structured conclusions, and create safe check/follow-up tasks within their competence. Plant state cannot be promoted to confirmed without human review or follow-up evidence. Companion governance may organize discussion and propose decisions only through explicit typed state and human-authorized `DecisionRecord` semantics. Training data curation may be mostly autonomous only when strong `evidence_refs` exist; `gold` status requires human, expert, or batch review.

### VII. Human Gate for Physical Actions

Any action that changes the physical plant system requires fresh data, safety check, and human approval before execution. Agents may create pending proposals or approval tasks, but MUST NOT issue immediate commands for pH, EC, solution, pumps, dosing, or light changes without the gate.

### VIII. Low Maintenance and Bounded MVP Scope

Low maintenance is a critical non-negotiable. Prefer simple local architecture, minimal infrastructure, clear source-of-truth boundaries, and reversible MVP slices. The MVP may include a bounded local-first Farm workspace with local Accounts, Boss/Engineer/Consultant roles, per-Plant access, multiple Plants, and Companion governance when explicitly specified by PRD/specs. Do not add production SaaS, hosted/cloud sync as an MVP requirement, billing/subscription boundaries, enterprise identity, microservices, complex sync, sensor runtime dependencies, full dataset registry, automated physical actuation, or broad farm-management scope before a later product stage explicitly requires them.

### IX. No Legacy Fallback and No Speculation

Agents MUST NOT use deprecated task formats, old risk models, or undocumented
assumptions for new or unfinished work. Terminal records created under the
superseded workflow may be read only through the explicit validator
compatibility rule; they are immutable history, not templates or acceptance
evidence for current tasks. Unknowns MUST be recorded as blockers or explicit
assumptions.

### X. Context Discipline

Agents SHOULD read the smallest sufficient context for the task. Higher-tier or cross-cutting tasks SHOULD read relevant normative docs such as invariants, contracts, states, testing, and workflow policies.

### XI. Synchronization

After meaningful changes, agents MUST synchronize affected Memory Bank docs,
task state, changelog, and routing files at the boundary required by the current
workflow. Status and evidence are written immediately; full `/mb-sync` follows
the current wave/boundary contract.

## Governance Decisions

- Project level: `medium`.
- Architecture priority: KISS by default, stability-first for safety, data, and agent-contract boundaries.
- Definition of Done: current non-terminal tasks follow the required tier route;
  additional evidence remains risk-informed and KISS.
- Workflow migration amendment on 2026-07-23: the 2026-07-03 advisory T2/T3
  policy is superseded for new and unfinished work. Existing `done|failed`
  records that retain deprecated `runtime_context.allowed_write_scope` remain
  accepted historical terminal records. Their missing historical PASS,
  semantic-pass, or human-checkpoint markers MUST NOT be synthesized
  retroactively and do not waive current gates for other tasks.
- Agent autonomy: plant state requires human/follow-up gate for confirmation; training data curation is mostly autonomous only with strong evidence.
- MVP scope amendment on 2026-06-01: bounded local-first Farm workspace, local Accounts, role-scoped access, multiple Plants, and Companion governance are allowed in MVP after PRD/spec promotion; production SaaS and broad farm-management scope remain excluded.
- Critical non-negotiable: low maintenance.

## Governance

- Constitution has precedence over workflow habits and generated plans.
- MBB, spec-index, invariants, contracts, states, testing, and workflow docs refine this Constitution; they must not contradict it.
- Amendments must include rationale and update affected docs if needed.
- Constitution should stay short. Put concrete project rules into `invariants.md`, `contracts/*`, `states/*`, or workflow policy docs.

**Version**: 4 | **Ratified**: 2026-05-27 | **Last updated**: 2026-07-23
