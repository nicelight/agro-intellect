---
description: Стратегия тестирования и верификации (quality gates, anti-cheat, UI/e2e).
status: active
---
# Testing & Verification

## Detailed Plans
- [.memory-bank/testing/first-demo.md](first-demo.md): first demo verification plan for the global MVP backbone.

## Quality gates
- Memory Bank changes: run `node scripts/mb-lint.mjs` and `node scripts/mb-doctor.mjs`.
- Code changes: run affected lint, typecheck, and build gates.
- Schema validation tests for contract/data/event artifacts.
- Unit tests for pure policy and lifecycle rules.
- Integration tests for API/state transitions and source-of-truth boundaries.
- Workflow smoke tests for critical agent/user flows.
- E2E tests for critical UI flows once the UI exists.

## Unit / policy tests
- pH/EC freshness: 24-hour analysis window and 2-hour physical-action approval window.
- Dataset trainability: `can_train_on`, split restrictions, confirmation source, evidence refs, and `gold` rules.
- Agent communication: runtime decision, concise output, `silent` audit behavior, and envelope validation.
- Safety: physical-action and high-risk manual intervention advice fails closed without required gate inputs.
- Lazy sync: `local_only`, 200 MB prompt-only behavior, and no `server_verified` before server sync exists.

## Integration / workflow tests
- Photo intake: required `plant_id`, unique `photo_id`, file storage, `sha256`, manifest creation, and event refs.
- Runtime authority: PostgreSQL/read model owns mutable state; manifests and `timeline.jsonl` do not.
- Timeline: append-only behavior and mandatory `payload.plant_id` for `user_photo`.
- Agent adapter: Agno output cannot enter Agent Chat Bus without runtime decision and domain adapter.
- Daily flow smoke: check-in, photo upload, optional pH/EC, agent conclusions, safety review, task/follow-up, and timeline entry.

## UI / e2e tests
- UI/e2e smoke is required for the critical daily flow once the Web App/PWA flow exists.
- UI Feed and `ui_spoiler_note` rendering must not create agent-consumable context.
- Human approval prompts must represent human-performed task tracking, not automated device execution.
- Companion responses and UI notes must not display physical-action instructions without Safety Gate clearance.

## Anti-cheat / risk-surface gates
- Agent output must not enter Agent Chat Bus without runtime decision and domain adapter.
- UI Feed and `ui_spoiler_note` must not be passed to agents as working context.
- Raw chain-of-thought or spoiler notes must not become facts, labels, or trainable data.
- PostgreSQL/read model, not photo manifests or `timeline.jsonl`, must be used for mutable state.
- Safety Gate tests must cover pH/EC, solution, pumps, light, dosing, and high-risk manual interventions.
- Companion responses and UI notes must not display physical-action instructions without Safety Gate clearance.
- Dataset governance tests must cover provenance fields, `can_train_on`, split restrictions, confirmation sources, evidence refs, and `gold` restrictions.
- Local security tests must cover loopback default binding, explicit authenticated LAN mode, CORS allowlist, upload size/MIME/path validation, path traversal rejection, and secret redaction from logs, `timeline.jsonl`, photo manifests, UI, Agent Chat Bus, and screenshots.
- Privacy/lazy sync tests must prove local photos/manifests stay private by default, no upload or sync occurs without explicit user approval, and the 200 MB prompt does not imply server sync or mutate `sync.status`.

## UI verification
- Prefer Playwright / agent-browser / CDP for UI flows when available
- Store screenshots/videos/traces in .tasks/TASK-XXX/
- In Memory Bank keep only links + short conclusions

## Artifacts
- screenshots/logs/videos → .tasks/TASK-XXX/
- in Memory Bank store only links + conclusions
