# 04. Реализованная модель данных Access and Session

Таблицы, созданные миграцией FT-001.

```mermaid
erDiagram
    ACCOUNT ||--o{ FARM_MEMBERSHIP : has
    ACCOUNT ||--o{ LOCAL_SESSION : owns

    ACCOUNT {
        uuid account_id PK
        text login_name UK
        text display_name
        string account_status
        text password_hash
        datetime created_at
        datetime updated_at
        datetime disabled_at
    }

    FARM_MEMBERSHIP {
        uuid membership_id PK
        uuid account_id FK
        uuid farm_id
        string role_preset
        string membership_status
        datetime created_at
        datetime updated_at
        datetime disabled_at
    }

    LOCAL_SESSION {
        uuid session_id PK
        uuid account_id FK
        string token_hash UK
        datetime created_at
        datetime expires_at
        datetime revoked_at
        datetime last_seen_at
        string auth_method
        text client_label
    }
```

`farm_id` уже присутствует как identity boundary, но таблица Farm и FK появятся
в FT-002. Raw session token в базе не хранится — сохраняется только SHA-256
digest.

