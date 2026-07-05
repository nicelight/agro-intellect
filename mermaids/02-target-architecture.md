# 02. Целевая архитектура и authority boundaries

Целевой local modular monolith. Стрелки показывают основной поток данных, а не
владение каждым конкретным endpoint.

```mermaid
flowchart LR
    UI[Operator PWA]

    subgraph Monolith[Local modular monolith]
        Access[Access and Admin]
        Ops[Plant Operations]
        Photo[Photo and Artifact Intake]
        Runtime[Runtime State and Audit]
        AgentRuntime[Agent Runtime]
        Bus[Agent Chat Bus]
        Feed[UI Feed]
        Safety[Safety and Task Loop]
        Companion[Companion Governance]
        Dataset[Dataset Governance]
    end

    PG[(PostgreSQL read model)]
    FS[(Local filesystem)]
    JSONL[(Append-only timeline.jsonl)]
    Provider[LLM and vision provider]

    UI --> Access
    Access --> Ops
    Access --> Photo
    Access --> Companion
    Ops --> PG
    Photo --> FS
    Photo --> PG
    PG --> Runtime
    FS --> Runtime
    Runtime --> Bus
    Bus --> AgentRuntime
    AgentRuntime --> Provider
    Provider --> AgentRuntime
    AgentRuntime --> Bus
    Bus --> Safety
    Bus --> Feed
    Safety --> PG
    Companion --> PG
    Dataset --> PG
    Runtime --> JSONL
    Feed --> UI

    Feed -. never agent context .-> Bus
    JSONL -. never mutable authority .-> PG
    Companion -. never Safety approval .-> Safety

    classDef implemented fill:#d9f7df,stroke:#238636,color:#111;
    classDef planned fill:#eef1f4,stroke:#6e7781,color:#333,stroke-dasharray:5 5;
    classDef authority fill:#dbeafe,stroke:#0969da,color:#111;
    class Access implemented;
    class Ops,Photo,Runtime,AgentRuntime,Bus,Feed,Safety,Companion,Dataset,UI,FS,JSONL,Provider planned;
    class PG authority;
```

Ключевой принцип: UI Feed и timeline являются projection/audit слоями и не
могут становиться runtime authority или agent working context.

