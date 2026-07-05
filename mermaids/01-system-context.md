# 01. Контекст системы

Показывает текущую runnable-часть и целевое окружение Agro Intellect MVP.

```mermaid
flowchart LR
    Boss[Boss]
    Engineer[Engineer]
    Consultant[Consultant]

    subgraph Product[Agro Intellect local-first MVP]
        PWA[Web App / PWA]
        API[FastAPI backend]
        Access[Access and Session FT-001]
        PG[(PostgreSQL runtime authority)]
        Files[(Local photos and artifacts)]
        Timeline[(timeline.jsonl audit/export)]
        Agents[Model-backed product agents]
        Safety[Safety Gate and human tasks]
    end

    Models[LLM and vision providers]
    Devices[Physical devices]

    Boss --> PWA
    Engineer --> PWA
    Consultant --> PWA
    PWA --> API
    API --> Access
    Access --> PG
    API --> Files
    PG --> Timeline
    Files --> Agents
    PG --> Agents
    Agents --> Models
    Agents --> Safety
    Safety -. human-only action .-> Devices

    classDef implemented fill:#d9f7df,stroke:#238636,color:#111;
    classDef planned fill:#eef1f4,stroke:#6e7781,color:#333,stroke-dasharray:5 5;
    classDef constrained fill:#fff3cd,stroke:#9a6700,color:#333;
    class API,Access,PG implemented;
    class PWA,Files,Timeline,Agents,Models,Safety planned;
    class Devices constrained;
```

Сейчас доступны backend, PostgreSQL substrate и FT-001. PWA, Plant operations,
agent runtime, artifacts и Safety Gate относятся к следующим features.

