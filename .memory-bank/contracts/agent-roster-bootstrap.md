---
description: Canonical product-agent roster and deterministic introduction metadata contract.
status: active
type: integration_contract
last_updated: 2026-07-28
source_of_truth:
  - .memory-bank/product.md
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/glossary.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/plant-feed-http.md
---
# Agent Roster And Introduction Metadata

## Scope

This contract fixes stable product-agent identities, competence boundaries,
ordering, and deterministic presentation metadata. It does not define a Plant
creation hook, introduction batch, sink, durable pending state, startup scan,
or reconciliation lifecycle.

"Start agents" means that the canonical roster is eligible for future typed
invocations for a currently active Plant. It does not spawn eight long-lived
processes, call models with an empty Plant payload, or write introduction rows.

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
those behaviors become operational. Roster eligibility or presentation does
not claim those later features are implemented.

## Runtime definition composition

`AgentDefinitionResolver` combines:

- immutable roster identity and competence metadata from this contract;
- the exact current owning-feature runtime policy, when that feature exists;
- one deployment binding resolved by the provider-profile contract;
- `output_schema_version=1`.

A roster member without an owning-feature runtime policy and an enabled model
binding cannot be invoked. Any unconfigured product invocation fails with
`AGENT_RUNTIME_NOT_CONFIGURED`; it never widens another agent's competence or
uses a fallback agent.

FT-007 provider transport verification may inject one isolated test-only
`runtime_contract_smoke` definition through the explicit test seam. It is
absent from production definition resolution, cannot publish to Bus/UI, and
does not count as a canonical product-agent or REQ-011 competence acceptance.

## Derived Plant eligibility

Per-Plant roster membership is a derived view, not a mutable registry table:

- every existing active Plant resolves roster version 1 and its exact eight
  identities;
- an archived, missing, or wrong-Farm Plant has no operationally invocable
  roster;
- restore makes the current roster eligible again, but never replays a prior
  model result or materializes an introduction;
- provider/model bindings remain deployment configuration and do not create
  per-Plant rows.

Plant creation, its committed `201` response, process startup, and restore do no
roster-introduction persistence work. No provider call is made merely because a
Plant exists or a Feed is opened.

## Deterministic introduction metadata

The immutable UUIDv5 namespace for version-1 introduction identities is
`ddbb4fc1-7253-5953-a427-9693caeafd80`. The UUID name is the UTF-8 encoding of
the exact ASCII string below, using lowercase canonical UUID text and base-10
roster version without padding:

`introduction:v1:<plant_id>:<agent_id>:<roster_version>`

No platform-native tuple formatting, JSON serialization, whitespace, braces,
or locale-dependent text may enter the UUID name.

For each canonical roster member, the presentation metadata contains:

- `schema_version=1`;
- `introduction_id`: deterministic UUIDv5 from the item name and namespace;
- `farm_id`, `plant_id`, `roster_version`, and canonical `agent_id`;
- exact `display_name`, `competence_summary`, and `introduction_text` from the
  roster table;
- `visible_to_agents=false`;
- `consumable_by_agents=false`.

The identity plus `(plant_id, agent_id, roster_version)` support idempotent
`UIFeedEvent` insertion. `created_at` is assigned only when a missing row is
first persisted and is not roster metadata. There is no batch identity,
content digest, requested timestamp, creator/session attribution,
authorization snapshot, provider metadata, or extension map.

An introduction is deterministic system presentation metadata:

- it is not produced by a model;
- it is not a MessageEnvelope and does not count as REQ-011 real-model
  evidence;
- it is never an Agent Chat Bus context event and cannot be consumed by an
  agent;
- it cannot carry Plant observations, measurements, recommendations, hidden
  reasoning, provider metadata, credentials, or authorization snapshots.

## Ownership and materialization boundary

FT-007 owns only the roster definition, resolver inputs, and deterministic
introduction metadata builder. It owns no introduction write, sink, result
matrix, retry state, or startup behavior.

FT-008 owns introduction persistence inside the protected
`GET /api/plants/{plant_id}/feed` application boundary:

- only a currently authorized read of an active Plant may insert missing
  introduction rows;
- current Account, FarmMembership, applicable PlantAccessGrant, and
  `Plant.status=active` are locked/rechecked in the same transaction as the
  inserts;
- the operation inserts only missing canonical rows and never updates or
  deletes an existing introduction row;
- repeated, concurrent, and client-retried Feed opens converge through the
  deterministic ids and existing database uniqueness constraints;
- an archived retained-history read, Plant create, startup, archive/restore,
  Agent Chat Bus, and every agent-context path write no introduction row.

The exact transaction, migration, pagination, and error behavior live in the
registered storage and Plant Feed contracts.

## Failure and verification

If lazy persistence fails, the Feed boundary returns
`FEED_PERSISTENCE_FAILED`; a later authorized active-Plant Feed retry is the
only recovery path. There is no background repair or reconciliation lifecycle.

Tests must prove:

- the roster contains exactly the eight ordered unique ids and exact immutable
  metadata above;
- introduction ids and content are deterministic across retries and isolated
  by Plant;
- introduction flags always prevent agent consumption and no introduction is
  parsed as MessageEnvelope;
- Plant create, startup, restore, and archived retained-history reads perform
  no introduction work;
- only an authorized active-Plant Feed open may materialize missing rows, and
  repeat/concurrent/retry paths do not duplicate or replace existing rows;
- no provider call or Agent Chat Bus/context event is caused by roster
  eligibility or introduction materialization.
