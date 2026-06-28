

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

  2. /mb-sync
     Тоже почти чистая документационная правка: commands/mb-sync.md + references/workflows/mb-sync.md. Добавить SDD checklist: spec-backbone, spec-index,
     spec_design_links, behavior specs, packet freshness handoff.

  3. /execute
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

codex resume 019f051c-aa2a-74e0-90b0-17bc1509251d
тут выполнялся  /review-tasks-plan FT-001

**********************************************************************************

  Обязательно править task cards

  - TASK-006-T3-FT-001-W1
    Главный owner для security primitives. Нужно уточнить verify, constraints,
    evidence_required, возможно touched_files. Если выберем argon2/bcrypt/
    passlib, сюда надо добавить pyproject.toml в touched_files.

  - TASK-009-T3-FT-001-W2
    Главный owner для cookie/session API. Добавить cookie name, Path, SameSite,
    Secure, Max-Age/Expires, clear-cookie behavior в verification/evidence.

  - TASK-008-T3-FT-001-W2
    Главный owner для ActorContext и interface boundary PlantPermissionContext.
    Нужно синхронизировать shape с FT-002 и убрать двусмысленность ownership.

  - TASK-010-T3-FT-001-W3
    Зависит от canonical PlantPermissionContext в context builders/protected
    routes. Нужно обновить проверки на совместимость shape, denial filtering и
    auth/context exclusion.

  - TASK-011-T3-FT-001-W3
    Integration/docs gate должен покрывать новые security/cookie/permission
    contract checks и docs sync.

  Условно править

  - TASK-005-T3-FT-001-W1
    Только если security repair задаст конкретные storage constraints для
    password_hash / token_hash: длины колонок, nullable rules, индексы, формат
    hash string. Если spec останется на уровне “строка hash, unique token_hash”,
    можно не трогать.

  - TASK-007-T3-FT-001-W2
    Только если repair уточнит service semantics: token verification, session TTL
    calculation, activation primitive, revocation/expiry behavior. Скорее всего
    придется слегка обновить verification/evidence, но меньше, чем 006/009.

**********************************************************************************
**********************************************************************************
**********************************************************************************


Проведи еще раз brownfield-aware global SDD backbone refresh
  -----------------

основные SDD спеки.

- Architecture Specification
- Interface Specification — API, события, протоколы, контракты.
   - Component Contract - Что гарантирует каждый модуль
   - API Contract - REST/gRPC/GraphQL, входы, выходы, ошибки
   - Event Contract - Формат событий, очередей, сообщений
   - Data Contract - Структура данных, версии, обязательные поля
- Data Specification — модели данных, схемы БД, форматы сообщений, правила валидации и сериализации.





  После /spec-design --all развилка простая:

  backbone blocked -> resolve blocker, rerun /spec-design
  backbone complete + foundation changed -> /foundation-to-tasks -> /mb-doctor
  backbone complete + foundation still verified -> /prd-to-tasks FT-001 refresh