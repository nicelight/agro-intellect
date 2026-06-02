---
description: Plant state confidence and confirmation lifecycle.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Plant State

## State Status Values

Important plant/system fields carry value plus status:

- `confirmed_updated`: value explicitly updated now by human input, measurement, review, or follow-up evidence;
- `confirmed_unchanged`: human confirms the value did not change;
- `assumed_unchanged`: system carried the previous value forward without fresh confirmation;
- `probable`: agent/system hypothesis with incomplete evidence;
- `unknown`: value is not known;
- `conflict`: evidence contradicts other evidence.

## Promotion Rules

- Agent-labeled conclusions may update `probable`, `unknown`, or `conflict`.
- Agent-labeled conclusions must not promote state to `confirmed_updated` or `confirmed_unchanged` without human review or follow-up evidence.
- Conflicting evidence must preserve `conflict` rather than selecting a convenient value silently.
- Manual pH/EC measurements can confirm measurement values only when timestamp and provenance exist.

## Safety Interaction

- A confirmed or fresh value is still not permission to perform physical action.
- Physical-action advice still requires Safety Gate pass and human approval.
- pH/EC freshness windows are defined in [.memory-bank/states/safety-approval.md](safety-approval.md).
