# Mermaid-диаграммы Agro Intellect

Набор из 10 диаграмм по текущей реализации и целевой архитектуре MVP.

| № | Диаграмма | Назначение |
|---:|---|---|
| 1 | [Контекст системы](01-system-context.md) | Пользователи, текущий backend и будущие интеграции |
| 2 | [Целевая архитектура](02-target-architecture.md) | Bounded contexts и границы authority |
| 3 | [Реализованные компоненты FT-001](03-implemented-components.md) | Модули Python и их зависимости |
| 4 | [Реализованная модель данных](04-access-session-data-model.md) | Account, FarmMembership и LocalSession |
| 5 | [Session API](05-session-api-sequence.md) | Login, `/me` и logout |
| 6 | [Жизненный цикл сессии](06-session-lifecycle.md) | Issuance, expiry, revoke и identity invalidation |
| 7 | [ActorContext и Plant permissions](07-actor-context-permissions.md) | Role policy, grant и Plant status |
| 8 | [Protected-route authorization](08-protected-route-flow.md) | Fail-closed FastAPI dependency chain |
| 9 | [Безопасный agent context](09-agent-context-builder.md) | Authz-before-data и context hygiene |
| 10 | [Roadmap features](10-feature-roadmap.md) | Выполненный фундамент и план FT-002…FT-016 |

Обозначения:

- зелёный — реализовано;
- жёлтый — интерфейс/контракт реализован, данные или adapter появятся позже;
- серый — запланировано;
- красный — запрещённый или fail-closed путь.

