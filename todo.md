# TODO

## Add Foundation Critical Path Contract

Status: completed 2026-06-23. Contract added at `.memory-bank/contracts/foundation-critical-path.md`; routing docs updated. Next route remains `/foundation-to-tasks`.

Context:
- `/spec-design` has recorded `Foundation Required: true` in `.memory-bank/foundation.md`.
- Foundation must prove this critical path before product feature tasking:
  `Photo/User input -> BusEventEnvelope -> Agent invocation -> Adapter -> MessageEnvelope/UIFeedEvent split -> Safety/State/Task transitions -> PostgreSQL + timeline.jsonl -> photo JSON export`.
- `/spec-design` must not guess the number of foundation tasks or the final gate task id.
- Current marker is `Foundation Gate Task: pending_/foundation-to-tasks`; `/foundation-to-tasks` must replace it with the concrete final gate task id after task slicing.

Task:
- Create `.memory-bank/contracts/foundation-critical-path.md` as a compact, executable, foundation-scoped contract.

Contract should define:
- `FoundationInput` for user observation/manual measurement plus optional photo fixture.
- Foundation BusEventEnvelope event type and minimal payload.
- `AgentInvocationRecord`: what counts as agent invocation, where test doubles are allowed, and why runtime/demo fake output is forbidden.
- `MessageEnvelope -> UIFeedEvent` split, including refs and `consumable_by_agents=false` for UI projection.
- `SafetyRouteResult` and minimal state/task transitions: safe clarification vs physical-action block.
- PostgreSQL/read-model evidence expectations.
- `timeline.jsonl` smoke event shape.
- Photo JSON export snapshot shape and refs.
- Redaction/context-hygiene assertions.

Also update:
- `.memory-bank/contracts/index.md`
- `.memory-bank/spec-index.md`
- `.memory-bank/foundation.md`
- `.memory-bank/testing/index.md`
- `.memory-bank/changelog.md`

Do not create:
- `REQ-000`
- `FT-000`
- task records
- packets
- protocols
- implementation plans
- guessed final foundation gate task id

After docs update, run:
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

Expected next route after this TODO:
- `/foundation-to-tasks`
