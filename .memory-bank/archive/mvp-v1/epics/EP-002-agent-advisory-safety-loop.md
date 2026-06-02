---
description: EP-002 - Agent advisory and safety loop for tomato_001.
status: draft
lifecycle: planned
---
# EP-002 Agent Advisory and Safety Loop

## Value

Let single-competence agents turn daily evidence into concise, useful advice while preserving domain communication boundaries, keeping UI-only content out of agent context, maintaining observation trust, and preventing physical plant-system actions without Safety Gate review and human approval.

## Success metrics

- Domain Bus events use `BusEventEnvelope` and enter the Agent Chat Bus only through the project-owned publication boundary.
- Agent outputs use explicit runtime decisions and `MessageEnvelope` before any agent-originated work output is eligible for Bus publication.
- UI Feed and spoiler notes remain presentation-only and never become agent working context.
- Vision and Plant State outputs preserve uncertainty instead of turning observations into confirmed facts.
- Hydroponics advice requests missing critical data and fails closed through Safety Gate for physical-action wording.
- Safety Gate detects physical-action wording, fails closed, and requires fresh data plus human approval before action unlock.
- Approved action tasks and follow-up outcomes are traceable after 1-3 days.

## Acceptance criteria

- Agno invocation is not treated as Agent Chat Bus publication.
- Agent Chat Bus events pass through `BusEventEnvelope` and include `consumable_by_agents`.
- Each invoked agent returns one runtime decision: `speak`, `silent`, `clarify`, or `escalate`, and published agent work outputs pass through `MessageEnvelope`.
- UI Feed is separate from Agent Chat Bus and is not passed to agents as working context.
- Vision Observation distinguishes observation from diagnosis and does not recommend pH/EC correction, dosing, or physical plant-system actions.
- Plant State does not promote agent-labeled conclusions to confirmed state without human review or follow-up evidence.
- Hydroponics advice is cautious, asks for missing critical data, and does not bypass Safety Gate.
- Physical-action advice fails closed unless fresh data, Safety Gate pass, and human approval are satisfied.
- Approval unlocks human-performed action task tracking only and never automated device execution.
- Task & Follow-up creates check or measurement tasks without approval, creates action tasks only from approved action proposals, and records 1-3 day follow-up outcomes.

## Source artifacts

- [.memory-bank/prd.md](../prd.md): FR-007 through FR-015, agent communication, UI Feed, Safety Gate, task/follow-up, acceptance criteria, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 7 through 13, 22, 23, 28, and 31 for compressed agent/safety context.
- [.memory-bank/requirements.md](../requirements.md): REQ-006 through REQ-010 and RTM links.
- [.memory-bank/features/FT-004-agent-chat-bus-event-stream-publication-boundary.md](../features/FT-004-agent-chat-bus-event-stream-publication-boundary.md): Agent Chat Bus event stream and publication boundary.
- [.memory-bank/features/FT-005-ui-feed-context-hygiene.md](../features/FT-005-ui-feed-context-hygiene.md): UI Feed and context hygiene.
- [.memory-bank/features/FT-006-vision-observation-plant-state-trust.md](../features/FT-006-vision-observation-plant-state-trust.md): Vision Observation and plant state trust.
- [.memory-bank/features/FT-007-hydroponics-advisor-missing-data-policy.md](../features/FT-007-hydroponics-advisor-missing-data-policy.md): Hydroponics Advisor and missing data policy.
- [.memory-bank/features/FT-008-tasks-approvals-follow-up-outcomes.md](../features/FT-008-tasks-approvals-follow-up-outcomes.md): tasks, approvals, and follow-up outcomes.
- [.memory-bank/features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](../features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): Agent runtime decisions and `MessageEnvelope` output contracts.
- [.memory-bank/features/FT-013-safety-gate-physical-action-advice.md](../features/FT-013-safety-gate-physical-action-advice.md): Safety Gate for physical-action advice.
- [.memory-bank/features/FT-014-human-approval-action-unlock-semantics.md](../features/FT-014-human-approval-action-unlock-semantics.md): human approval and action unlock semantics.

## Normative inputs

- [.memory-bank/constitution.md](../constitution.md): bounded agent autonomy, human gate for physical actions, KISS, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): SDD route map for planned Agent Chat Bus, MessageEnvelope, UI Feed, Agno boundary, plant state, advisor, safety approval, and task follow-up specs.
- [.memory-bank/testing/index.md](../testing/index.md): risk-surface verification and baseline quality gates.

## Constraints / invariants

- Scope remains one plant: `tomato_001`.
- Agent Chat Bus is the domain working stream; UI Feed is presentation only.
- Agno is an execution SDK, not source of truth and not the Agent Chat Bus.
- Agents have one competence boundary and do not directly command each other.
- Agent hypotheses are not confirmed facts and are not trainable labels by default.
- Physical plant-system changes require fresh data, Safety Gate pass, and human approval.
- MVP action tasks are human-performed checklist/task records, not automated device commands.
- No automated device command or physical actuation is in MVP scope.

## Features included

- [FT-004 Agent Chat Bus Event Stream and Publication Boundary](../features/FT-004-agent-chat-bus-event-stream-publication-boundary.md): domain Bus events, `BusEventEnvelope`, event types, `consumable_by_agents`, and Agno publication boundary.
- [FT-005 UI Feed and Context Hygiene](../features/FT-005-ui-feed-context-hygiene.md): UI Feed separation, spoiler notes, concise display content, and context filtering.
- [FT-006 Vision Observation and Plant State Trust](../features/FT-006-vision-observation-plant-state-trust.md): photo observation, confidence, plant state statuses, conflict handling, and confirmation gates.
- [FT-007 Hydroponics Advisor and Missing Data Policy](../features/FT-007-hydroponics-advisor-missing-data-policy.md): advisor reasoning inputs, cautious recommendations, missing/stale pH/EC requests, and Safety Gate handoff.
- [FT-008 Tasks, Approvals, and Follow-up Outcomes](../features/FT-008-tasks-approvals-follow-up-outcomes.md): check/measurement tasks, approved action tasks, pending approvals, follow-up, and outcomes.
- [FT-012 Agent Runtime Decisions and MessageEnvelope Output Contracts](../features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): `speak|silent|clarify|escalate`, `MessageEnvelope`, concise output, silent audit, Team Signal/Safety Block output routing, and `ui_spoiler_note_ref` pointer rule.
- [FT-013 Safety Gate for Physical-Action Advice](../features/FT-013-safety-gate-physical-action-advice.md): physical-action detection, fail-closed behavior, 2-hour pH/EC approval freshness, high-risk manual interventions, user-visible action wording checks, and no direct action commands.
- [FT-014 Human Approval and Action Unlock Semantics](../features/FT-014-human-approval-action-unlock-semantics.md): approval/rejection records, pending action proposals/tasks, human-performed action task unlocks, and no automated device execution.
