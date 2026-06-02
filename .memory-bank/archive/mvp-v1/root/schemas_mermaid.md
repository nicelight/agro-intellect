---
description: Archived MVP v1 overview architecture diagrams.
status: archived
---
# Agro Intellect Architecture Diagrams

Статус: обзорный onboarding-документ.

Источник: `project_dossier.md` + `potential_PRBLMS_to_avoid.md`. Диаграммы помогают быстро понять архитектуру, runtime workflow и зоны риска. Этот файл не является нормативным source of truth; нормативные решения должны жить в `.memory-bank/spec-index.md`, contracts, domains и states.

## 1. Карта проекта в целом

```mermaid
flowchart TD
  Tomato["Личный гидропонный томат"]
  MVP["Контролируемый MVP"]
  Product["Личный AI-помощник"]
  TrainingGround["Учебный полигон AI-first agentic systems"]
  FutureFarm["Будущая farm-scale agentic system"]

  Tomato --> MVP
  MVP --> Product
  MVP --> TrainingGround
  TrainingGround --> FutureFarm

  Product --> Daily["Daily check-in"]
  Product --> Photo["Фото и наблюдения"]
  Product --> Advice["Осторожные рекомендации"]
  Product --> Tasks["Задачи и follow-up"]
  Product --> Approval["Human approval"]

  TrainingGround --> SDD["Spec-driven development"]
  TrainingGround --> Agents["Single-competence agents"]
  TrainingGround --> Safety["Safety gates"]
  TrainingGround --> DataLoop["Dataset governance / learning loop"]
```

## 2. Система под капотом

```mermaid
flowchart TB
  User["Пользователь / владелец растения"]
  UI["Web App / PWA"]

  subgraph Backend["Backend: Python + FastAPI monolith"]
    API["API layer"]
    Workflow["Explicit workflow coordinator"]
    Bus["Agent Chat Bus"]
    UIFeed["UI Feed"]
    Adapter["Agno output adapter"]
    SafetyPolicy["Deterministic Safety Policy"]
    StateSvc["Plant State / Task services"]
    ExportSvc["Training export service"]

    subgraph Agno["Agno SDK boundary"]
      Agents["Agno Agents"]
      AgnoWorkflow["Agno Workflow"]
      OptionalTeam["Optional Agno Team without coordinate mode"]
    end
  end

  subgraph Storage["Storage"]
    PG["PostgreSQL runtime state"]
    Files["Photo files + JSON manifests"]
    Timeline["timeline.jsonl audit/export"]
    FutureInflux["Future InfluxDB sensor readings"]
  end

  User --> UI
  UI --> API
  API --> Workflow
  Workflow --> AgnoWorkflow
  AgnoWorkflow --> Agents
  OptionalTeam -. optional .-> Adapter
  Agents --> Adapter
  Adapter --> Bus
  Adapter --> UIFeed
  Bus --> StateSvc
  Bus --> SafetyPolicy
  SafetyPolicy --> Bus
  StateSvc --> PG
  Workflow --> Timeline
  API --> Files
  ExportSvc --> Files
  ExportSvc --> PG
  ExportSvc -. future .-> FutureInflux
  UIFeed --> UI
  Bus --> UI
```

## 3. Source of truth и authority map

```mermaid
flowchart LR
  subgraph Normative["Нормативная истина"]
    Specs["Design Specs / Memory Bank"]
    SpecIndex[".memory-bank/spec-index.md"]
    Contracts["contracts / domains / states"]
  end

  subgraph Runtime["Runtime authority"]
    PG["PostgreSQL read model / mutable state"]
    HumanReview["human_review / batch_review / expert_review"]
    Curator["curator_decision + evidence_refs"]
    Influx["Future InfluxDB sensor readings"]
  end

  subgraph Transport["Transport / audit / export"]
    Bus["Agent Chat Bus / MessageEnvelope"]
    Timeline["timeline.jsonl append-only audit/export"]
    PhotoJson["Photo JSON immutable snapshot"]
    PlantJson["plant.json dataset snapshot"]
  end

  SpecIndex --> Specs
  Specs --> Contracts

  Contracts --> Bus
  Contracts --> PG
  Contracts --> HumanReview
  Contracts --> Curator

  PG --> Timeline
  PG --> PhotoJson
  Influx -. sensor window .-> PhotoJson
  HumanReview --> PG
  Curator --> PG

  Bus --> Timeline
  Bus -. not authority .-> PG
  PhotoJson -. not runtime authority .-> PG
  PlantJson -. not runtime authority .-> PG
```

## 4. Product agents и границы компетенции

```mermaid
flowchart TD
  Bus["Agent Chat Bus"]

  Companion["Companion Agent<br/>диалог и user-facing synthesis"]
  Vision["Vision Observation Agent<br/>наблюдение по фото"]
  PlantState["Plant State Agent<br/>состояние растения во времени"]
  Hydro["Hydroponics Advisor Agent<br/>pH / EC / агрономические риски"]
  TaskAgent["Task & Follow-up Agent<br/>задачи, outcome, follow-up"]
  Safety["Safety Gate Agent / Policy<br/>approval и блокировки"]
  Governance["Dataset Governance Agent<br/>dataset status rules"]
  Curator["Training Data Curator Agent<br/>delayed dataset decisions"]

  Bus --> Companion
  Bus --> Vision
  Bus --> PlantState
  Bus --> Hydro
  Bus --> TaskAgent
  Bus --> Safety
  Bus --> Governance
  Bus --> Curator

  Vision -->|agent_conclusion| Bus
  PlantState -->|state conclusion| Bus
  Hydro -->|recommendation / clarify| Bus
  TaskAgent -->|task_created| Bus
  Safety -->|team_signal / safety_block| Bus
  Governance -->|dataset rule signal| Bus
  Curator -->|mostly silent| Bus
  Companion -->|primary user response| Bus

  Safety -. blocks risky actions .-> Hydro
  Safety -. requires approval .-> TaskAgent
  Governance -. controls can_train_on .-> Curator
```

## 5. Первый daily check-in flow

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant UI as Web App / PWA
  participant API as FastAPI
  participant WF as Workflow Coordinator
  participant Bus as Agent Chat Bus
  participant V as Vision Agent
  participant PS as Plant State Agent
  participant H as Hydro Advisor
  participant S as Safety Gate
  participant T as Task Agent
  participant C as Companion Agent
  participant DB as PostgreSQL
  participant FS as Files + timeline.jsonl

  U->>UI: Ответ на daily check-in + фото + pH/EC
  UI->>API: upload photo + measurements
  API->>DB: photo_catalog + measurements
  API->>FS: original photo + initial JSON snapshot
  API->>Bus: user_photo / user_message event
  API->>FS: append timeline event

  WF->>V: invoke with photo context
  V-->>WF: runtime_decision + structured output
  WF->>Bus: agent_conclusion via MessageEnvelope
  WF->>FS: append timeline event

  WF->>PS: invoke with consumable Bus context
  PS-->>WF: probable / unknown / conflict updates
  WF->>DB: update non-confirmed plant state

  WF->>H: invoke with pH/EC + state
  H-->>WF: cautious recommendation or clarification
  WF->>S: policy check for risky action

  alt Risky action without approval
    S-->>WF: safety_block
    WF->>Bus: safety_block
    WF->>T: create pending measurement / approval task
  else Safe check / info request
    WF->>T: create follow-up task
  end

  T->>DB: task records
  WF->>C: synthesize user-facing response
  C-->>UI: primary_user_response + UI Feed
```

## 6. Bus vs UI Feed: context hygiene

```mermaid
flowchart TD
  AgentOutput["Agent raw/structured output"]
  RuntimeDecision{"runtime_decision"}

  AgentOutput --> RuntimeDecision

  RuntimeDecision -->|silent| Audit["Audit record only"]
  RuntimeDecision -->|speak| BusEvent["BusEventEnvelope + MessageEnvelope"]
  RuntimeDecision -->|clarify| Clarify["agent_clarification_request"]
  RuntimeDecision -->|escalate| Signal["agent_team_signal / safety_block"]

  Audit --> OptionalUI["Optional UI Feed event"]
  BusEvent --> Bus["Agent Chat Bus<br/>consumable_by_agents=true"]
  Clarify --> Bus
  Signal --> Bus

  OptionalUI --> UIFeed["UI Feed<br/>visible_to_agents=false<br/>consumable_by_agents=false"]
  AgentOutput --> Spoiler["Controlled ui_spoiler_note"]
  Spoiler --> UIFeed

  Bus --> ContextBuilder["Agent context builder"]
  ContextBuilder --> NextAgents["Next agent inputs"]

  UIFeed -. forbidden .-> ContextBuilder
```

## 7. Agno boundary: SDK execution is not domain publication

```mermaid
flowchart LR
  Prompt["Workflow step input"]

  subgraph SDK["Agno SDK"]
    Agent["Agno Agent"]
    Workflow["Agno Workflow"]
    Team["Optional Team route/broadcast/tasks"]
    Memory["Agno memory/storage/events"]
  end

  Adapter["Domain adapter"]
  Decision{"speak / silent / clarify / escalate"}
  Envelope["MessageEnvelope or no Bus publication"]
  Bus["Agent Chat Bus"]
  UI["UI Feed"]
  Audit["Audit log"]

  Prompt --> Workflow
  Workflow --> Agent
  Workflow -. optional .-> Team
  Agent --> Adapter
  Team --> Adapter
  Memory -. not domain fact .-> Adapter

  Adapter --> Decision
  Decision --> Envelope
  Decision --> Audit
  Envelope --> Bus
  Decision --> UI

  Agent -. forbidden direct publish .-> Bus
  Workflow -. forbidden step_completed as fact .-> Bus
  Team -. coordinate mode forbidden .-> Bus
```

## 8. Data flow: photo, state, audit, export

```mermaid
flowchart TD
  Upload["Photo upload"]
  PhotoId["Generate photo_id + sha256"]
  PlantBinding["Require plant_id"]

  Upload --> PhotoId
  PhotoId --> PlantBinding

  PlantBinding --> PGPhoto["PostgreSQL photo_catalog<br/>photo_id unique<br/>plant_id not null"]
  PlantBinding --> PhotoFile["Filesystem original photo"]
  PlantBinding --> UserPhotoEvent["user_photo Bus event<br/>payload.plant_id required"]

  UserPhotoEvent --> Timeline["timeline.jsonl append-only"]
  PGPhoto --> RuntimeState["Mutable runtime state<br/>review / dataset / sync"]
  RuntimeState --> Export["Export snapshot builder"]
  PhotoFile --> Export
  FutureSensor["Future InfluxDB sensor_window"] -. later .-> Export

  Export --> Manifest["photo JSON manifest<br/>immutable snapshot<br/>authoritative=false"]
  Export --> DatasetPair["photo + JSON training artifact"]

  Manifest -. not primary state .-> RuntimeState
  Timeline -. audit/export only .-> RuntimeState
```

## 9. Safety approval flow

```mermaid
flowchart TD
  Proposal["Recommendation / action proposal"]
  IsPhysical{"Changes physical state?"}
  FreshData{"Fresh pH/EC and required data?"}
  SafetyCheck{"Safety check passed?"}
  HumanApproval{"Human approved?"}
  Block["Safety Block"]
  Pending["pending action proposal / approval task"]
  ActionTask["approved action_task"]
  Execute["User executes action manually"]
  Outcome["Follow-up outcome in 1-3 days"]

  Proposal --> IsPhysical
  IsPhysical -->|no| SafeInfo["Safe info / measurement request"]
  IsPhysical -->|yes| FreshData
  FreshData -->|no| Block
  FreshData -->|yes| SafetyCheck
  SafetyCheck -->|fail| Block
  SafetyCheck -->|pass| HumanApproval
  HumanApproval -->|no| Pending
  HumanApproval -->|yes| ActionTask
  ActionTask --> Execute
  Execute --> Outcome
  Block --> Pending
  SafeInfo --> Outcome
```

## 10. Dataset lifecycle и can_train_on

```mermaid
stateDiagram-v2
  [*] --> raw
  raw --> agent_labeled: agent hypothesis
  agent_labeled --> needs_review: conflict / low confidence / valuable item
  raw --> needs_review: selected for review
  needs_review --> rejected: review rejected
  needs_review --> confirmed: human / expert / batch review approved
  agent_labeled --> confirmed: curator_auto with strong evidence_refs
  confirmed --> gold: human / expert / batch approval
  confirmed --> excluded: data quality issue
  raw --> excluded: bad photo / invalid metadata
  agent_labeled --> excluded: unsafe or noisy label
  rejected --> [*]
  excluded --> [*]
  gold --> [*]

  note right of confirmed
    can_train_on=true only when:
    curator_decision=selected
    split=train
    evidence_refs not empty
    confirmation_source allowed
  end note

  note right of gold
    gold requires human/expert
    or batch review approval
  end note
```

## 11. Memory Bank development workflow

```mermaid
flowchart TD
  Idea["Идея / feature intent"]
  Analysis["/analysis"]
  Brainstorm{"Идея сырая?"}
  Brief["/brief"]
  Constitution{"project_principles ratified/partial?"}
  WritePRD["/write-prd"]
  SpecInit["/spec-init"]
  PRD["/prd"]
  SpecDesign["/spec-design FT-XXX"]
  Tasks["/prd-to-tasks FT-XXX"]
  Execute["/execute TASK-XXX"]
  Verify["/verify TASK-XXX"]
  Tier{"T2/T3?"}
  RedVerify["/red-verify TASK-XXX"]
  Sync["/mb-sync"]
  Done["Done with evidence"]

  Idea --> Analysis
  Analysis --> Brainstorm
  Brainstorm -->|yes| BrainstormStep["/brainstorm"]
  Brainstorm -->|no| Brief
  BrainstormStep --> Brief
  Brief --> Constitution
  Constitution -->|no| ConstitutionStep["/constitution"]
  Constitution -->|yes| WritePRD
  ConstitutionStep --> WritePRD
  WritePRD --> SpecInit
  SpecInit --> PRD
  PRD --> SpecDesign
  SpecDesign --> Tasks
  Tasks --> Execute
  Execute --> Verify
  Verify --> Tier
  Tier -->|yes| RedVerify
  Tier -->|no| Sync
  RedVerify --> Sync
  Sync --> Done
```

## 12. MVP scope staging

```mermaid
flowchart LR
  S1["Stage 1<br/>Project foundation"]
  S2["Stage 2<br/>Data model + schemas"]
  S3["Stage 3<br/>Agent Chat Bus"]
  S4["Stage 4<br/>First workflow"]
  S5["Stage 5<br/>Learning loop"]
  S6["Stage 6<br/>Sync + server"]
  S7["Stage 7<br/>Sensors"]

  S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7

  S1 --> MB["Memory Bank routing<br/>product / requirements<br/>architecture specs"]
  S2 --> Schemas["plant / timeline / photo manifest<br/>agent report schemas<br/>schema tests"]
  S3 --> Bus["Message types<br/>UI split<br/>context filtering<br/>Safety Block"]
  S4 --> Flow["daily check-in<br/>photo<br/>pH/EC<br/>mock Vision<br/>tasks + approval"]
  S5 --> Loop["curator decisions<br/>evidence refs<br/>dataset split<br/>outcomes"]
  S6 --> Sync["lazy upload<br/>sha256<br/>idempotency<br/>server_verified"]
  S7 --> Sensors["pH / EC / temp / humidity<br/>telemetry<br/>InfluxDB or TimescaleDB"]
```

## 13. Самый важный implementation path

```mermaid
flowchart TD
  A["1. Normalize specs from dossier"]
  B["2. Implement schemas"]
  C["3. Build vertical slice with mock agents"]
  D["4. Add deterministic Safety Gate"]
  E["5. Keep can_train_on=false until evidence"]
  F["6. Add Agno behind adapter boundary"]
  G["7. Expand learning loop / sync / sensors later"]

  A --> B --> C --> D --> E --> F --> G

  C --> Slice["user_photo -> mock Vision -> MessageEnvelope -> UI spoiler split -> timeline.jsonl -> schema tests"]
  D --> Gate["No physical action without fresh data + safety check + human approval"]
  F --> Boundary["Agno invocation != Agent Chat Bus publication"]
```

## 14. Главные рисковые зоны на одной карте

```mermaid
flowchart TD
  Dossier["project_dossier.md"]
  Specs["Memory Bank specs"]
  Scope["MVP scope"]
  Bus["Agent Chat Bus"]
  Safety["Safety Gate"]
  Data["Data authority split"]
  UILeak["UI Feed leakage"]
  Agno["Agno boundary"]
  Dataset["Dataset governance"]
  Tests["Boundary tests"]

  Dossier -->|must be normalized| Specs
  Scope -->|avoid platform too early| Bus
  Bus -->|adapter bottleneck| Agno
  Bus -->|context builder| UILeak
  Safety -->|must be deterministic| Tests
  Data -->|PG vs JSONL vs manifests| Tests
  Dataset -->|delay can_train_on| Tests
  Agno -->|SDK only, not authority| Tests
  Specs -->|contracts drive code| Tests
```
