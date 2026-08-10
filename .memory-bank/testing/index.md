---
description: Router for active testing strategy and subject verification specifications.
status: active
last_updated: 2026-07-28
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/testing/strategy.md
---
# Testing Index

## Global strategy

- [Testing Strategy](strategy.md): risk-based test levels, quality gates,
  anti-cheat rules, and cross-cutting verification areas.
- [Memory Bank workflow regression](../../tests/memory-bank/mb-workflow.test.mjs):
  structural lint, gate-schema alignment, latest-attempt evidence selection,
  and `in_progress` recovery hints.

## Subject verification

- [Foundation Test Harness](foundation-test-harness.md): executable substrate,
  smoke targets, fixtures, and Foundation evidence.
- [Session And Access Verification](auth/session-and-access.md): identity,
  sessions, ActorContext, and authorization.
- [Boss Admin And Audit Verification](admin/boss-admin-and-audit.md): Boss
  administration, audit, isolation, and end-to-end evidence.
- [Plant Lifecycle And Access Verification](farm/plant-lifecycle-and-access.md):
  Farm bootstrap, Plant lifecycle/grants, ActorContext, audit, migration, and
  HTTP evidence.
- [Plant Operations Verification](plant-operations.md): check-in, manual pH/EC,
  freshness, and authorized operations evidence.
- [Photo Intake Verification](photo-intake.md): photo file/catalog/manifest,
  upload, checksum, and timeline-ref evidence.
- [Plant History Verification](plant-history.md): Plant card/history
  projection, retained-history, timeline-ref, and redaction evidence.
- [Agent Runtime Verification](agent-runtime.md): runtime decisions,
  MessageEnvelope, static roster metadata, provider binding, real-model
  anti-cheat, audit, and archive-race evidence.
- [Agent Chat Bus And UI Feed Verification](agent-chat-ui-feed.md): lazy
  active-Feed introductions, guarded publication, context hygiene, migration,
  and Plant Feed API.
- [Vision Observation And Plant State Verification](vision-observation-plant-state.md):
  real image input, provider anti-cheat, trust persistence, conflict, review,
  and Plant state HTTP evidence.
- [Hydroponics Advisor Verification](hydroponics-advisor.md): pH/EC freshness,
  missing-data policy, provider-neutral deterministic execution, and pending
  Safety/task handoff.
- [Safety Gate Verification](safety-gate.md): provider-neutral deterministic
  classification, immutable Safety decisions, 2-hour approval input, UI
  projection, migration-head compatibility, and concurrency/archive guards.
- [Task And Follow-Up Verification](task-follow-up.md): W1 Approval/task/outcome
  transactions, HTTP, concurrency/archive, migration-head, and semantic
  evidence are complete; real Task and Follow-Up Agent evidence remains W2.
- [Companion Governance Verification](companion-governance.md): IssueStack,
  proposal/attention lifecycle, atomic DecisionRecord effects, projections,
  HTTP, explicit runtime trigger, and real Companion evidence.
- [Dataset Governance Verification](dataset-governance.md): Dataset Candidate
  aggregate, transition policy, evidence-flow wiring, and provider-neutral
  dataset-agents runtime with the curator gate.

## Archive

- [MVP v1 Testing](../archive/mvp-v1/testing/): historical testing documents.
