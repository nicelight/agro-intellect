# 08. Fail-closed protected-route authorization

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Dep as require_actor_context
    participant DB as PostgreSQL
    participant Sess as SessionService
    participant Actor as ActorContextResolver
    participant PlantDep as require_plant_permission
    participant Handler as Business handler

    Client->>Dep: Request with session cookie

    alt credential missing
        Dep-->>Client: 401 AUTH_SESSION_REQUIRED
    else bearer or malformed cookie
        Dep-->>Client: 401 AUTH_SESSION_INVALID
    else cookie present
        Dep->>Sess: require_valid_session
        Sess->>DB: session and identity lookup
        alt expired, revoked or disabled
            Sess-->>Dep: typed failure reason
            Dep-->>Client: stable 401 or 403 error
        else valid session
            Sess-->>Dep: ValidatedSession
            Dep->>Actor: resolve ActorContext
            Actor-->>Dep: ActorContext
            Dep->>PlantDep: resolve PlantPermissionContext
            alt Plant scope denied
                PlantDep-->>Client: 404 AUTH_PLANT_FORBIDDEN
            else operation allowed
                PlantDep->>Handler: AuthorizedPlantRequest
                Handler-->>Client: Product response
            end
        end
    end
```

Business handler не вызывается до успешной session и Plant authorization.
Generic Plant denial не раскрывает существование Plant.

