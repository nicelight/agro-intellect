
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
  +1. FT-003 Runtime State and Timeline Audit 
  +2. FT-009 Dataset Governance and Trainability
  3. FT-010 Local Security, Privacy, and Lazy Sync
  4. FT-002 Photo Intake, Catalog, and Capture Manifests
  5. FT-001 Daily Check-in, Observations, and Manual Measurements
  6. FT-004 Agent Chat Bus Event Stream
  7. FT-012 Agent Runtime Decisions and MessageEnvelope
  8. FT-005 UI Feed and Context Hygiene
  9. FT-013 Safety Gate for Physical-Action Advice
  10. FT-014 Human Approval and Action Unlock Semantics
  11. FT-008 Tasks, Approvals, and Follow-up Outcomes
  12. FT-006 Vision Observation and Plant State Trust
  13. FT-007 Hydroponics Advisor and Missing Data Policy
  14. FT-011 Minimal Web App/PWA Operator Surface

  порядок /prd-to-tasks:
    1. /prd-to-tasks FT-003
  2. /prd-to-tasks FT-009
  3. /prd-to-tasks FT-010
  4. /prd-to-tasks FT-002
  5. /prd-to-tasks FT-001
  6. /prd-to-tasks FT-004
  7. /prd-to-tasks FT-012
  8. /prd-to-tasks FT-005
  9. /prd-to-tasks FT-013
  10. /prd-to-tasks FT-014
  11. /prd-to-tasks FT-008
  12. /prd-to-tasks FT-006
  13. /prd-to-tasks FT-007
  14. /prd-to-tasks FT-011.


---

Schemantic drift в Memory Bank:

  P1

  1. .memory-bank/architecture/system-architecture.md:237 действительно конфликтует с FT-004: диаграмма ведёт
     timeline.jsonl -> Bus. Однозначное решение: заменить flow на публикацию из domain/application workflow в обе     стороны: отдельно timeline append, отдельно Bus publication; timeline может быть только source_ref, не     authority/replay source.
  2. .memory-bank/runbooks/local-security.md:41 расходится с FT-010. Однозначное решение: убрать “upload later    when Wi-Fi is available” и заменить на локальный storage prompt: “storage exceeds 200 MiB; user may acknowledge/dismiss local prompt; no upload/server availability implied”.
  3. .memory-bank/analysis/index.md:17 stale. Однозначное решение: заменить на “global /spec-design backbone     complete; feature-local /spec-improve remains per feature”. Также .memory-bank/analysis/index.md:27 стоит     обновить с “pre-/spec-design” на текущий post-backbone статус.

  P2
  4. .memory-bank/contracts/timeline-event.md:29 двусмысленен. Однозначное решение: явно записать, что
  timeline.consumable_by_agents=true только eligibility marker для validated Bus publication через FT-004  service; agent context builders всё равно читают только Bus events.

  
  Я бы делал это одной docs-sync правкой без новых specs: system-architecture.md, runbooks/local-security.md,
  contracts/timeline-event.md, requirements.md, analysis/index.md, spec-index.md, и короткие coordination notes в
  FT-004/FT-012 tech specs.


---


  Сделать позже:

  1. FT-004/FT-012 имеют зависимость, но не критичный блокер. Рекомендую зафиксировать порядок decomposition:
     FT-004 foundation BusPublicationService + BusEventEnvelope stub → FT-012 MessageEnvelope/AgentRuntimeResult
     validation + adapter mapping → FT-004/FT-012 integration tests for agent-originated publication.
     Это лучше записать в spec-index.md как cross-feature task ordering, и коротко продублировать в FT-004/FT-012
     tech specs.


  2. .memory-bank/requirements.md:95 RTM неполный. Рекомендую добавить к REQ-013: FT-011 primary, плюс FT-005,     FT-013, FT-014; Epic cell: EP-004 + EP-002. Тесты дополнить workflow:approval-prompt-human-action.
