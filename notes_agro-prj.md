

 Главное с чего начинать реализацию проекта

  Я бы считал критическим path таким:
  
  Photo/User input → BusEventEnvelope → Agent invocation → Adapter → MessageEnvelope/
  UIFeedEvent split → Safety/State/Task transitions → PostgreSQL + timeline.jsonl → photo
  JSON export

  Если этот path будет формально закрыт схемами и тестами, остальная архитектура сможет
  расти. Если он будет рыхлым, система быстро станет набором агентов, которые “примерно
  договорились”, но не имеют надёжного state/provenance слоя.


---------------------------------------

----------
Промпт ревью
----------
Запусти 6 сабагентов на review всего проекта. Надо убедиться что workflow будет консистентным, нету явных и грубых gaps или troubles, логических противоречий и т.п.

----------------------
----------------------

запуск отложенной задачи по промпту

sleep 240m && codex -c model_reasoning_effort=xhigh resume 019ec059-2934-7a40-8bc2-eee1e029098b "Задача прервалась, скорее всего твои воркеры не завершили ее. Проверь в каком состоянии задача и аккуратно продолжи ее выполнение через новых воркеров"

sleep 120m && codex -c model_reasoning_effort=xhigh resume 019eebb6-9237-7263-8309-57bb787d4eef "$(< prompt.md)" 
 
----------------------
----------------------


1. убрать из воркфлоу для T3 - ROLLBACK_RECOVERY_NOTE:

#tags  
ESP32, API, MQTT, HomeAssistant, Python, TypeScript, JavaScript, web,





----------------------------------------------------------------------------------
----------------------------------------------------------------------------------
фикс мемобинка тут:
019f04f0-1f9b-7eb3-b046-cb4f269b8197



  --1. /clarify-feature
     Только doc-spec правка в skills/_shared/references/commands/clarify-feature.md: добавить чтение spec_design_*, design-impact note, routing в /spec-improve//
     spec-design, behavior-spec stale note. Без scripts.

  --2. /mb-sync
     Тоже почти чистая документационная правка: commands/mb-sync.md + references/workflows/mb-sync.md. Добавить SDD checklist: spec-backbone, spec-index,
     spec_design_links, behavior specs, packet freshness handoff.

  --3. /execute
     Небольшая правка в commands/execute.md: explicit stop на missing required packet для T2/T3, guide-only caveat, concrete contract minimum block. Низкий риск.

  Средняя сложность:

  4. /mb-garden
     Правки в основном doc-only, но надо аккуратно синхронизировать canonical runtime commands/mb-garden.md с skills/mb-garden/SKILL.md, потому что сейчас они
     расходятся. По объему больше, чем первые три.

  5. /mb-verify
     Легко, если просто сделать skills/mb-verify thin/deprecated wrapper на /verify. Сложнее, если чистить legacy alias/install migration.

  6. /mb-packet
     Самый небыстрый: правильный фикс затрагивает mb-packet.md, packet-template.json, и mb-doctor.mjs shape validation, плюс нужно аккуратно решить behavior spec
     refs и packet freshness.

  Я бы начал с /clarify-feature, /mb-sync, /execute: это быстрые текстовые фиксы с минимальным blast radius и сразу закрывают часть SDD drift.



Правка FT-001 глобальная
----------------------------------------------------------------------------------
----------------------------------------------------------------------------------

 

**********************************************************************************


**********************************************************************************
**********************************************************************************
**********************************************************************************

  -----------------

основные SDD спеки.

- Architecture Specification
- Interface Specification — API, события, протоколы, контракты.
   - Component Contract - Что гарантирует каждый модуль
   - API Contract - REST/gRPC/GraphQL, входы, выходы, ошибки
   - Event Contract - Формат событий, очередей, сообщений
   - Data Contract - Структура данных, версии, обязательные поля
- Data Specification — модели данных, схемы БД, форматы сообщений, правила валидации и сериализации.


ПЛАН УЛУЧШЕНИЯ MEMOBANK:

  1. /prd-to-tasks выполняет обязательный Task Design Coverage Pass перед созданием каждой T2/T3-задачи:
      - определяет необходимые Interface/Component/API/Event/Data specs;
  2. /spec-improve получает дополнительный task-scoped режим:

  /spec-improve TASK-001-T2-FT-001-W1
  - проверить design coverage конкретной задачи;
  - исправить существующие authoritative specs;
  - создать недостающий spec только при отсутствии естественного owner;
  - обновить ссылки задачи и feature metadata;
  - не менять scope, tier, waves и dependencies;
  - потребовать обновления packet через /mb-packet.




  После /spec-design --all развилка простая:

  backbone blocked -> resolve blocker, rerun /spec-design
  backbone complete + foundation changed -> /foundation-to-tasks -> /mb-doctor
  backbone complete + foundation still verified -> /prd-to-tasks FT-001 refresh