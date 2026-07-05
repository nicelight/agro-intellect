# 05. Session API: login, me и logout

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI Session API
    participant Cred as CredentialService
    participant Sess as SessionService
    participant Repo as AccessSessionRepository
    participant DB as PostgreSQL
    participant Actor as ActorContextResolver

    User->>API: POST /api/session/login
    API->>Cred: authenticate(login, password)
    Cred->>Repo: find Account and Membership
    Repo->>DB: SELECT identity
    DB-->>Repo: Account and Membership
    Cred-->>Sess: authenticated identity
    Sess->>Sess: generate opaque token
    Sess->>Repo: persist token_hash only
    Repo->>DB: INSERT LocalSession
    API-->>User: 200 plus HttpOnly cookie and safe summary

    User->>API: GET /api/session/me plus cookie
    API->>Sess: require_valid_session(raw token)
    Sess->>Repo: lookup by SHA-256 digest
    Repo->>DB: SELECT session and identity
    DB-->>Repo: current records
    Sess-->>API: ValidatedSession
    API->>Actor: resolve ActorContext
    Actor-->>API: safe actor and permission resolver
    API-->>User: 200 safe current-session summary

    User->>API: POST /api/session/logout plus cookie
    API->>Sess: revoke_session(raw token)
    Sess->>Repo: set revoked_at
    Repo->>DB: UPDATE LocalSession
    API-->>User: 204 and expired clear-cookie
```

Invalid credentials use generic errors. Browser JSON responses never contain
the raw session token.

