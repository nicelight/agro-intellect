---
description: Canonical product-agent roster and post-commit Plant bootstrap handoff contract.
status: active
type: integration_contract
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/product.md
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/glossary.md
  - .memory-bank/contracts/agent-runtime-adapter.md
---
# Agent Roster And Plant Bootstrap

## Scope

This contract fixes stable product-agent identities and the FT-007 side of
automatic activation after a Plant has been created and committed. It defines
the deterministic introduction handoff that a later chat/feed publisher
consumes without turning presentation text into model output or agent context.

"Start agents" means activate the canonical roster for the committed active
Plant so its members are eligible for future typed invocations. It does not
spawn eight long-lived processes and does not call eight models with an empty
Plant payload.

## Canonical roster version 1

Roster ordering, ids, display names, competence summaries, and introductions
are immutable within `roster_version=1`:

| Order | `agent_id` | Display name | Competence boundary | Deterministic introduction | Owning feature for detailed behavior |
|---:|---|---|---|---|---|
| 1 | `companion` | Companion Agent | dialogue and governance coordination without replacing specialists, backend rules, or Safety Gate | `Я Companion Agent. Помогаю вести диалог и координировать вопросы по растению, не подменяя специалистов и правила безопасности.` | FT-013 |
| 2 | `vision_observation` | Vision Observation Agent | photo quality and visual observation; no diagnosis or physical-action recommendation | `Я Vision Observation Agent. Проверяю фотографии и описываю только наблюдаемое, не ставя диагнозов и не назначая действий.` | FT-009 |
| 3 | `plant_state` | Plant State Agent | trends, uncertainty, and evidence conflicts; no self-confirmation of hypotheses | `Я Plant State Agent. Отслеживаю состояние растения во времени, отмечаю неопределённость и противоречия в данных.` | FT-009 |
| 4 | `hydroponics_advisor` | Hydroponics Advisor Agent | cautious hydroponic advice and missing-data requests; cannot bypass Safety Gate | `Я Hydroponics Advisor Agent. Даю осторожные рекомендации по гидропонике и запрашиваю недостающие данные перед выводами.` | FT-010 |
| 5 | `task_follow_up` | Task & Follow-up Agent | checks, measurements, approved human tasks, and 1-3 day follow-up | `Я Task & Follow-up Agent. Помогаю вести проверки, измерения, разрешённые задачи и последующее наблюдение за результатом.` | FT-012 |
| 6 | `safety_gate` | Safety Gate Agent | physical-action wording classification and approval routing; no actuation | `Я Safety Gate Agent. Проверяю рекомендации с физическими действиями и блокирую их до выполнения требований безопасности.` | FT-011 |
| 7 | `dataset_governance` | Dataset Governance Agent | dataset lifecycle, evidence, split, and trainability policy | `Я Dataset Governance Agent. Контролирую происхождение данных и правила их допустимого использования для обучения.` | FT-014 |
| 8 | `training_data_curator` | Training Data Curator Agent | delayed evidence-based training selection; silent by default | `Я Training Data Curator Agent. Отбираю обучающие примеры только при наличии разрешённых evidence refs и обычно остаюсь безмолвным.` | FT-014 |

FT-007 owns these stable identities, concise competence boundaries,
introduction metadata, output-schema version seam, and provider-binding seam.
The listed owning features define detailed prompts/instructions, triggers,
claim restrictions, tools, effects, and competence-specific acceptance before
those behaviors become operational. Roster activation alone does not claim
those later features are implemented.

## Runtime definition composition

`AgentDefinitionResolver` combines:

- immutable roster identity and competence metadata from this contract;
- the exact current owning-feature runtime policy, when that feature exists;
- one deployment binding resolved by the provider-profile contract;
- `output_schema_version=1`.

A roster member without an owning-feature runtime policy and an enabled model
binding may introduce itself but cannot be invoked. Any unconfigured product
invocation fails with `AGENT_RUNTIME_NOT_CONFIGURED`; it never widens another
agent's competence or uses a fallback agent.

FT-007 provider transport verification may inject one isolated test-only
`runtime_contract_smoke` definition through the explicit test seam. It is
absent from production definition resolution, cannot publish to Bus/UI, and
does not count as a canonical product-agent or REQ-011 competence acceptance.

## Derived Plant activation

Per-Plant roster membership is a derived view, not a mutable registry table:

- every existing active Plant resolves roster version 1 and its exact eight
  identities;
- an archived/missing/wrong-Farm Plant has no operationally invocable roster;
- restore makes the current roster eligible again, but never replays a prior
  model result or blocked introduction automatically;
- provider/model bindings remain deployment configuration and do not create
  per-Plant rows.

This makes activation restart-safe without a worker or outbox. The post-commit
hook is needed to produce the one-time introduction handoff, not to keep agent
eligibility alive. No provider call is made during derivation.

## Post-commit bootstrap command

`PlantAgentBootstrapCommandV1` is created only by backend composition after the
Plant creation transaction has committed successfully. It contains exactly:

- `schema_version=1`;
- `farm_id` and `plant_id` from the committed Plant result;
- `roster_version=1`;
- `requested_at`, a timezone-aware UTC timestamp;
- the safe creator `account_id` for attribution, not authorization reuse.

The command is never accepted from HTTP request fields or model output. Before
building a handoff, the bootstrap service reloads the Plant and proves that it
exists in the same Farm and is active. It performs no provider/model I/O.

The existing Plant transaction must not be held open across bootstrap, chat,
feed, timeline, network, or provider work. A provider call inside Plant
creation is forbidden.

## Introduction handoff version 1

For a valid command, `PlantAgentBootstrapService` produces exactly eight
ordered `AgentIntroductionV1` items. Each strict item contains:

- `schema_version=1`;
- `introduction_id`: deterministic UUIDv5 derived from
  `(plant_id, agent_id, roster_version)` in the project namespace;
- `farm_id`, `plant_id`, `roster_version`, and canonical `agent_id`;
- exact `display_name`, `competence_summary`, and `introduction_text` from the
  roster table;
- `visible_to_agents=false`;
- `consumable_by_agents=false`.

Unknown fields are rejected. The same Plant/roster retry produces the same
eight ids and content. The downstream publisher must use
`(plant_id, agent_id, roster_version)` as the uniqueness key and treat a
duplicate as successful idempotent completion.

An introduction is deterministic system presentation metadata:

- it is not produced by a model;
- it is not a MessageEnvelope and does not count as REQ-011 real-model
  evidence;
- it is never an Agent Chat Bus context event and cannot be consumed by an
  agent;
- it cannot carry Plant observations, measurements, recommendations, hidden
  reasoning, provider metadata, credentials, or authorization snapshots.

## Ownership boundary without FT-008 tasking

FT-007 implements the roster, bootstrap command/service, deterministic ids,
post-commit hook, and a narrow `AgentIntroductionSink` handoff port. It does not
create BusEventEnvelope storage, chat history, UIFeedEvent persistence, a UI,
or a worker/outbox.

The concrete durable chat/feed projection and its transactional idempotency
remain downstream publication work. This FT-007 decomposition records that
boundary but intentionally creates no FT-008 task card.

Until a concrete sink is wired, FT-007 must not claim that an introduction is
visible in chat. Tests may inject a recording sink only to prove the exact
handoff contract; production must not replace a missing sink with fake chat
success.

## Failure and retry behavior

- Plant validation failure creates no handoff.
- A bootstrap/sink failure after Plant commit cannot roll back the Plant and
  cannot cause the API to report that the already committed Plant was not
  created.
- Safe diagnostics use `AGENT_BOOTSTRAP_HANDOFF_FAILED` plus Farm/Plant ids and
  never contain introductions with Plant data, auth material, provider
  payloads, or local paths.
- The command and handoff are explicitly replay-safe. A downstream publisher
  may retry or reconcile the same committed Plant; duplicate introduction keys
  cannot create duplicate visible messages.
- Archive before downstream publication makes the handoff non-publishable.
  Restore does not replay it automatically without a new current-authority
  reconciliation owned by the publisher.

Because FT-007 owns no durable delivery store, its successful handoff is not a
claim of eventual chat delivery. A later publisher that requires guaranteed
delivery must own persistence/reconciliation rather than smuggling an outbox
into Agent Runtime.

## Verification

Tests must prove:

- the roster contains exactly the eight ordered unique ids and exact immutable
  metadata above;
- every introduction id/content is deterministic across retries and isolated
  by Plant;
- introduction flags always prevent agent consumption and no introduction is
  parsed as MessageEnvelope;
- Plant creation commits before the bootstrap hook starts, and the hook makes
  no provider call;
- a failed post-commit handoff leaves the Plant committed and does not return a
  false rollback/500 result;
- inactive, missing, wrong-Farm, caller-forged, and unknown-roster commands
  fail closed;
- no Agent Runtime provider call is made merely because a Plant was created;
- process restart does not lose roster eligibility because it is derived from
  the current active Plant and immutable roster version rather than memory;
- tests do not claim visible chat publication without a concrete downstream
  sink.
