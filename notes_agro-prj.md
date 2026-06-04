
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



 Главное с чего начинать реализацию проекта

  Я бы считал критическим path таким:
  
  Photo/User input → BusEventEnvelope → Agent invocation → Adapter → MessageEnvelope/
  UIFeedEvent split → Safety/State/Task transitions → PostgreSQL + timeline.jsonl → photo
  JSON export

  Если этот path будет формально закрыт схемами и тестами, остальная архитектура сможет
  расти. Если он будет рыхлым, система быстро станет набором агентов, которые “примерно
  договорились”, но не имеют надёжного state/provenance слоя.


---------------------------------------

улучшения 

ОПЦИОНАЛЬНО ПРОВЕСТИ /spec-improve для:
- FT-011 UI/PWA: если хочешь до дизайна явно выбрать стиль daily flow: chat-first, dashboard-first или hybrid.
- FT-006 Vision: если хочешь продуктово зафиксировать, первый demo строго mock или можно сразу real vision.
- FT-010 LAN/security: если хочешь заранее решить, будет ли LAN mode в первом demo видимым UI-настройкой или
  только config/env.
- FT-013 Safety Gate: если хочешь уточнить границу low-risk check vs high-risk physical intervention beyond уже
  указанных pruning/transplant/root trimming.

  ---

  порядок /spec-improve  и выполнения тасок
  



  порядок /prd-to-tasks:
  - Wave 1: FT-001..FT-004 — identity/access/admin foundation.
  - Wave 2: FT-005..FT-007 — Plant workflow and evidence.
  - Wave 3: FT-008, FT-010, FT-011 — agent boundary, safety, tasks.
  - Wave 4: FT-009, FT-012, FT-013 — agents, governance, dataset/privacy.
  - Wave 5: FT-014 — first end-to-end demo consolidation.


---
Schemantic drift в Memory Bank есть? 
---



С