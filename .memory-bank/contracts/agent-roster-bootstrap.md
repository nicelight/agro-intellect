---
description: Canonical product-agent roster and post-commit Plant bootstrap handoff contract.
status: active
type: integration_contract
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/product.md
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/glossary.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/domains/farm/farm-plant-access-storage.md
---
# Agent Roster And Plant Bootstrap

## Scope

This contract fixes stable product-agent identities and the FT-007 side of
automatic activation after a Plant has been created and committed. It defines
the deterministic introduction handoff consumed by the FT-008 UI Feed
publisher without turning presentation text into model output or agent context.

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

### Plant-create compatibility

The hook does not extend the public Plant request or response. The canonical
`POST /api/plants` behavior remains active Boss/Engineer authorization,
same-transaction Plant/grant/audit atomicity, and `201 PlantSummary` from
`plant-management-http.md`. Only after that transaction commits may backend
composition invoke bootstrap. Bootstrap/sink rejection, timeout, or failure
cannot change the already selected 201 response into rollback/500, mutate the
returned Plant/grant snapshot, or reuse any public request field. Existing
Plant-create error codes remain owned by the HTTP/storage contracts.

## Introduction handoff version 1

The immutable UUIDv5 namespace for version-1 introduction identities is
`ddbb4fc1-7253-5953-a427-9693caeafd80`. UUID names are UTF-8 encodings of the
exact ASCII strings below, using lowercase canonical UUID text and base-10
roster version without padding:

- batch: `batch:v1:<plant_id>:<roster_version>`;
- item: `introduction:v1:<plant_id>:<agent_id>:<roster_version>`.

No platform-native tuple formatting, JSON serialization, whitespace, braces,
or locale-dependent text may enter the UUID name.

For a valid command, `PlantAgentBootstrapService` produces exactly eight
ordered `AgentIntroductionV1` items. Each strict item contains:

- `schema_version=1`;
- `introduction_id`: deterministic UUIDv5 from the item name and immutable
  namespace above;
- `farm_id`, `plant_id`, `roster_version`, and canonical `agent_id`;
- exact `display_name`, `competence_summary`, and `introduction_text` from the
  roster table;
- `visible_to_agents=false`;
- `consumable_by_agents=false`.

Unknown fields are rejected. The same Plant/roster retry produces the same
eight ids and content. The downstream publisher must use
`(plant_id, agent_id, roster_version)` as the uniqueness key and treat a
duplicate as successful idempotent completion.

FT-007 passes the items in exactly one strict `AgentIntroductionBatchV1`, never
as eight independent sink calls. The batch contains only:

- `schema_version=1`;
- `batch_id`: deterministic UUIDv5 from the batch name above;
- `farm_id`, `plant_id`, and `roster_version=1`;
- `source_type=system`, `source_id=agent_roster_v1`;
- `introductions`: the exact ordered tuple of eight strict items.

The batch contains no request timestamp, creator/session identity, auth scope,
provider metadata, or arbitrary extension map, so retries and reconciliation
produce identical canonical field values; equality never depends on JSON object
field order.

An introduction is deterministic system presentation metadata:

- it is not produced by a model;
- it is not a MessageEnvelope and does not count as REQ-011 real-model
  evidence;
- it is never an Agent Chat Bus context event and cannot be consumed by an
  agent;
- it cannot carry Plant observations, measurements, recommendations, hidden
  reasoning, provider metadata, credentials, or authorization snapshots.

## Ownership boundary

FT-007 implements the roster, bootstrap command/service, deterministic ids,
post-commit hook, and a narrow `AgentIntroductionSink.store_batch(batch)`
handoff port. It does not
create BusEventEnvelope storage, chat history, UIFeedEvent persistence, a UI,
or a worker/outbox.

The sink returns one strict `AgentIntroductionBatchResultV1` containing exactly
`{schema_version, batch_id, status, durable, accepted_count, reason_code}`.
`schema_version=1`, `batch_id` must equal the submitted batch, and unknown
fields are rejected. Its closed matrix is:

| Status | `durable` | `accepted_count` | `reason_code` | Meaning |
|---|---:|---:|---|---|
| `accepted` | `true` | `8` | `null` | the whole eight-item intent was durably committed |
| `duplicate` | `true` | `8` | `null` | the existing batch and all eight uniqueness keys have identical canonical content |
| `rejected` | `false` | `0` | `plant_not_publishable|batch_invalid|content_conflict` | no item was accepted; invalid/conflicting content is permanent, while Plant state requires a new current-state reconciliation |
| `failed` | `false` | `0` | `persistence_failed` | no item was accepted; retryable downstream persistence/runtime failure |

No other status/field combination is valid. Per-item results and partial
success are forbidden: downstream commits all eight durable intents atomically
or none.

FT-008 owns durable batch storage/reconciliation and the exactly-once
`UIFeedEvent` projection. The Plant chat/feed UI renders that event; an
introduction never becomes an Agent Chat Bus event.

Until a concrete durable sink is wired, FT-007 must not claim durable acceptance
or visibility. A recording sink may test the port but is not production
delivery evidence.

## Failure and retry behavior

- Plant validation failure creates no handoff.
- A bootstrap/sink failure after Plant commit cannot roll back the Plant and
  cannot cause the API to report that the already committed Plant was not
  created.
- Safe diagnostics use `AGENT_BOOTSTRAP_HANDOFF_FAILED` plus Farm/Plant ids and
  never contain introductions with Plant data, auth material, provider
  payloads, or local paths.
- The command and handoff are replay-safe. FT-008 reconciles the deterministic
  batch for each active Plant; duplicate keys cannot create duplicate
  `UIFeedEvent` records.
- Archive before downstream publication makes the handoff non-publishable.
  Pending intent remains retained. Restore does not blindly replay it: the next
  FT-008 reconciliation must reload the Plant, prove it is currently active,
  and only then resume idempotent delivery.

Only `accepted|duplicate` from the concrete FT-008 sink proves durable
acceptance. FT-008 scans active Plants and pending batches, recreates a missing
deterministic batch after handoff failure/restart, and retries until all eight
`UIFeedEvent` records exist. This is current-state reconciliation, not replay;
Agent Runtime owns no outbox.

## Verification

Tests must prove:

- the roster contains exactly the eight ordered unique ids and exact immutable
  metadata above;
- every introduction id/content is deterministic across retries and isolated
  by Plant;
- the namespace, exact UUID name strings, batch id, and one-call ordered batch
  snapshot are stable across process/language-independent retries;
- introduction flags always prevent agent consumption and no introduction is
  parsed as MessageEnvelope;
- Plant creation commits before the bootstrap hook starts, and the hook makes
  no provider call;
- a failed post-commit handoff leaves the Plant committed and does not return a
  false rollback/500 result;
- sink contract tests cover `accepted`, identical `duplicate`, `rejected`, and
  `failed`; prove accepted counts are only 8 or 0 and partial persistence/result
  is impossible;
- inactive, missing, wrong-Farm, caller-forged, and unknown-roster commands
  fail closed;
- no Agent Runtime provider call is made merely because a Plant was created;
- process restart does not lose roster eligibility because it is derived from
  the current active Plant and immutable roster version rather than memory;
- FT-007 tests do not claim durable acceptance or visible projection without a
  concrete FT-008 sink.
