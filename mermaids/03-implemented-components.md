# 03. Реализованные компоненты FT-001

Фактические backend-компоненты, существующие в текущем worktree.

```mermaid
flowchart TB
    Main[backend.app.main create_app]
    SessionAPI[api.session router]
    Dependencies[access_admin.dependencies]
    ContextBuilder[access_admin.context_builders]
    Errors[access_admin.errors]
    Actor[access_admin.actor_context]
    Permissions[access_admin.permissions]
    SessionService[access_admin.session_service]
    CredentialService[access_admin.credential_service]
    Security[access_admin.security]
    Repository[access_admin.repository]
    Models[access_admin.models]
    Database[DatabaseHandle]
    Alembic[Alembic FT-001 migration]
    PG[(PostgreSQL)]

    Main --> SessionAPI
    Main --> Database
    SessionAPI --> SessionService
    SessionAPI --> Actor
    SessionAPI --> Errors
    Dependencies --> SessionService
    Dependencies --> Actor
    Dependencies --> ContextBuilder
    Dependencies --> Errors
    ContextBuilder --> Actor
    ContextBuilder --> Permissions
    Actor --> Permissions
    SessionService --> CredentialService
    SessionService --> Security
    SessionService --> Repository
    CredentialService --> Security
    CredentialService --> Repository
    Repository --> Models
    Repository --> Database
    Alembic --> PG
    Database --> PG

    Snapshot[PlantAccessSnapshotProvider]
    FT002[Future FT-002 persistence adapter]
    FT002 -. implements .-> Snapshot
    Snapshot --> Permissions

    classDef implemented fill:#d9f7df,stroke:#238636,color:#111;
    classDef seam fill:#fff3cd,stroke:#9a6700,color:#333;
    classDef planned fill:#eef1f4,stroke:#6e7781,color:#333,stroke-dasharray:5 5;
    class Main,SessionAPI,Dependencies,ContextBuilder,Errors,Actor,Permissions,SessionService,CredentialService,Security,Repository,Models,Database,Alembic,PG implemented;
    class Snapshot seam;
    class FT002 planned;
```

Protected-route dependencies и context builder реализованы как reusable seams,
но пока не смонтированы как отдельные product endpoints.

