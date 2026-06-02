---
description: Task, approval handoff, and follow-up outcome lifecycle.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Task Follow-up

## Task Types

- `check_task`: low-risk observation/check request.
- `measurement_task`: request for missing or stale pH/EC or other measurements.
- `pending_approval_task`: human decision needed before a risky action can proceed.
- `action_task`: approved human-performed action tracking only.
- `follow_up_task`: check outcome after 1-3 days.

## Creation Rules

- Check and measurement tasks may be created without approval when more data is needed.
- Pending approval tasks may be created from Safety Gate output.
- Action tasks may be created only from approved action proposals.
- No task may represent automated device execution in the MVP.

## Outcomes

Follow-up outcome values:

- `improved`
- `worsened`
- `unchanged`
- `no_data`

Follow-up records outcome evidence; they do not retroactively approve actions or promote agent hypotheses to confirmed state without the applicable review/evidence rules.

## Traceability

Tasks should reference relevant plant, observation, photo, measurement, safety block, approval, and timeline event IDs where those refs exist.
