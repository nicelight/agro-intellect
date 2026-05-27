
архитектура:
layered modular monolith + разработка вертикальными слайсами.
Слои существуют для порядка.
Vertical slices существуют для движения вперёд.
Не “разрабатываем слоями”. А “организуем код слоями, доставляем функциональность слайсами”.


# architecture.md
Agro Intellect MVP uses a layered modular monolith structure and vertical slice delivery.
The system is deployed as a simple monolith.
Code is organized into clear layers: UI/API, application workflows, domain policies, agents, infrastructure, and tests.
Development is performed only through vertical slices, where each slice delivers visible user value and a testable learning outcome.
The project must not introduce microservices, production-grade orchestration, complex databases, or generic agent frameworks during MVP.



 Главное узкое место реализации

  Я бы считал критическим path таким:
  
  Photo/User input → BusEventEnvelope → Agent invocation → Adapter → MessageEnvelope/
  UIFeedEvent split → Safety/State/Task transitions → PostgreSQL + timeline.jsonl → photo
  JSON export

  Если этот path будет формально закрыт схемами и тестами, остальная архитектура сможет
  расти. Если он будет рыхлым, система быстро станет набором агентов, которые “примерно
  договорились”, но не имеют надёжного state/provenance слоя.