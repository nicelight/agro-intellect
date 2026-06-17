

 Главное с чего начинать реализацию проекта

  Я бы считал критическим path таким:
  
  Photo/User input → BusEventEnvelope → Agent invocation → Adapter → MessageEnvelope/
  UIFeedEvent split → Safety/State/Task transitions → PostgreSQL + timeline.jsonl → photo
  JSON export

  Если этот path будет формально закрыт схемами и тестами, остальная архитектура сможет
  расти. Если он будет рыхлым, система быстро станет набором агентов, которые “примерно
  договорились”, но не имеют надёжного state/provenance слоя.


---------------------------------------

  порядок /spec-improve а потом /prd-to-tasks:

---
запусти 6 сабагентов на проверку : 
- консистентности spec-layer,
- отсутствие логических ошибок
- Schemantic drift в Memory Bank 
- any other gaps, troubles, problems, misunderstandings

---

 дай промпт ( без воды и без указания очевидных для агента вещей) к агенту для запуска /prd чтобы он учитывал
  скилл `/agents-best-practices`

---

──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Самые сложные и опасные таски 

   - TASK-070 PhysicalActionProposal schema/taxonomy
  - TASK-072 SafetyGateDecision persistence
  - TASK-073 approver eligibility
  - TASK-078 action_task unlock from exact approved proposal
  - TASK-080 публикация task/approval/outcome refs в Bus/UI/timeline/history
  - TASK-081 regression/eval/no-actuation suite

  Agent harnes TASK-041..TASK-058

----

  Рекомендованный старт для ручного выполнения:

model = 5.4 mini,  model_reasoning_effort = high.

   TASK-001
   TASK-011
   TASK-013
2, 3, 4, 14, 12, 15, 5, 16.
6, 7, 17, 18, 8, 23, 9, 19, 20, 21, 10, 24, 22, 25
Группа A — FT-002 Farm/Plant Lifecycle (критический путь):
  6.  TASK-006  T2  Farm workspace + tomato_001 seed             (deps: 001, 002 ✓)
  7.  TASK-007  T2  Plant create/archive/restore service+routes   (deps: 006)
  8.  TASK-008  T3  PlantAccessGrant + authorized selector        (deps: 006, 007)
  9.  TASK-009  T3  Archived retention + history filters          (deps: 007, 008)
  10. TASK-010  T3  Plant lifecycle integration + OpenAPI coverage (deps: 008, 009)

Группа B — FT-003 Boss Admin (параллельно с A, до A.8):
  11. TASK-017  T3  Boss-only admin API boundary + schemas        (deps: 002, 003, 011 ✓)
  12. TASK-018  T3  AdminAuditRecord + redacted writer            (deps: 003, 011 ✓)
  13. TASK-019  T3  Personnel / account add+invite / membership   (deps: 017, 018)
  14. TASK-020  T3  Plant lifecycle admin -> audit                (deps: 007, 017, 018)
  15. TASK-021  T3  PlantAccessGrant admin + audit                (deps: 008, 017, 018)

Группа C — старт FT-004 (как только готов фундамент A):
  16. TASK-023  T2  CheckIn persistence + lifecycle + schemas      (deps: 002, 006, 007)

--------

2. Проработать органичное внедреное БД в проект, переработать уже написанный функционал под базу данных. 
Начать с backbone SDD 

1. Очередь полностью построена на сломанном паттерне «новый пустой репозиторий на каждый запрос».
3.  Укажи в карточке TASK-008, что нужно будет реализовать PlantAccessGrant, фильтрация растений по правам, если это не указано в таске. 
4. Farm overwrite  это баг TASK-006.  Должно быть или игнорирование (если уже есть), или ошибка. Запусти воркера на фикс. 
5. Механизмы _TEST_REPO как глобальные переменные — техдолг. 

--
Минимальное KISS-решение (без ORM, без новых зависимостей):

1. FastAPI lifespan — создать backend/app/main.py, который при старте создаёт один InMemoryAccessRepository и один InMemoryPlantRepository, заполняет их (Boss-аккаунт, Farm, tomato_001) и кладёт в app.state.
2. Роуты берут репозиторий из request.app.state — вместо создания нового на каждый запрос.
3. Убрать _TEST_REPO/_ACCESS_REPO/_PLANT_REPO глобалы — заменить на pytest fixtures с чистыми репозиториями.
4. Исправить add_farm — чтобы при повторном создании той же Farm кидал ошибку, а не молча перезаписывал.