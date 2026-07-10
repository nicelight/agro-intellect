---
description: Router for active testing strategy and subject verification specifications.
status: active
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/testing/strategy.md
---
# Testing Index

## Global strategy

- [Testing Strategy](strategy.md): risk-based test levels, quality gates,
  anti-cheat rules, and cross-cutting verification areas.

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

## Archive

- [MVP v1 Testing](../archive/mvp-v1/testing/): historical testing documents.
