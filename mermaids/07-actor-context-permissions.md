# 07. ActorContext и вычисление Plant permissions

```mermaid
flowchart TD
    Session[ValidatedSession]
    Actor[ActorContext]
    Request[Plant operation request]
    Provider[PlantAccessSnapshotProvider]
    Snapshot{Plant snapshot valid?}
    Membership{Membership active?}
    Role{Role preset}
    Grant{Active matching grant?}
    Plant{Plant active or allowed retained history?}
    Boss[Boss policy]
    Engineer[Engineer policy]
    Consultant[Consultant policy]
    Allow[PlantPermissionContext]
    Deny[Denied context all flags false]

    Session --> Actor
    Request --> Actor
    Actor --> Membership
    Membership -- no --> Deny
    Membership -- yes --> Provider
    Provider --> Snapshot
    Snapshot -- no --> Deny
    Snapshot -- yes --> Role
    Role -- boss --> Boss
    Role -- engineer --> Grant
    Role -- consultant --> Grant
    Grant -- no --> Deny
    Grant -- engineer --> Engineer
    Grant -- consultant --> Consultant
    Boss --> Plant
    Engineer --> Plant
    Consultant --> Plant
    Plant -- denied operation --> Deny
    Plant -- allowed operation --> Allow

    Allow --> Flags[read comment operate tasks manage approve]
    Flags --> Safety[can_approve_actions is actor authority only]

    classDef allow fill:#d9f7df,stroke:#238636,color:#111;
    classDef deny fill:#ffebe9,stroke:#cf222e,color:#111;
    classDef seam fill:#fff3cd,stroke:#9a6700,color:#333;
    class Allow,Flags allow;
    class Deny deny;
    class Provider seam;
```

Engineer и Consultant требуют активный PlantAccessGrant. Consultant никогда не
получает operate/task/action authority. Safety Gate остаётся отдельной будущей
границей.

