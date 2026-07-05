# 09. Безопасный authorization-scoped agent context

```mermaid
flowchart TD
    Input[ActorContext plus plant_id plus operation]
    Resolve[Resolve PlantPermissionContext]
    Allowed{Operation allowed?}
    NoData[Return no context without iterating candidates]
    Candidates[Candidate domain records]
    PlantMatch{Same Plant?}
    Kind{source_kind is domain_record?}
    Consumable{consumable_by_agents true?}
    Ref{Safe bounded source_ref?}
    Keys{No forbidden keys?}
    Values{No recognized auth material?}
    Copy[Copy JSON-safe payload]
    Output[AuthorizedPlantContext]
    Scope[authorization_scope]
    Records[SafePlantContextRecord list]
    Drop[Drop complete candidate]

    Input --> Resolve --> Allowed
    Allowed -- no --> NoData
    Allowed -- yes --> Candidates
    Candidates --> PlantMatch
    PlantMatch -- no --> Drop
    PlantMatch -- yes --> Kind
    Kind -- no --> Drop
    Kind -- yes --> Consumable
    Consumable -- no --> Drop
    Consumable -- yes --> Ref
    Ref -- no --> Drop
    Ref -- yes --> Keys
    Keys -- no --> Drop
    Keys -- yes --> Values
    Values -- no --> Drop
    Values -- yes --> Copy
    Copy --> Records
    Resolve --> Scope
    Scope --> Output
    Records --> Output

    classDef allow fill:#d9f7df,stroke:#238636,color:#111;
    classDef deny fill:#ffebe9,stroke:#cf222e,color:#111;
    class Output,Scope,Records allow;
    class Drop,NoData deny;
```

UI Feed, raw chat/reasoning/provider output, admin notices и unapproved
proposals исключаются. Текущая реализация предполагает trusted backend
candidates; typed payload contracts принадлежат будущим FT-007/FT-008.

