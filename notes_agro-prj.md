

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
