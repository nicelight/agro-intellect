

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

sleep 240m && codex -c model_reasoning_effort=xhigh resume 019ec059-2934-7a40-8bc2-eee1e029098b "Задачу опишем тут"

sleep 120m && codex -c model_reasoning_effort=xhigh resume 019eebb6-9237-7263-8309-57bb787d4eef "$(< prompt.md)" 
 
----------------------
----------------------

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

На ночь запустить:
Твоя основная задача - выполнить рефакторинг из файла IDEAS/specs_without_owners.md. 




**********************************************************************************
**********************************************************************************

Кто еще может использовать не правильную модель генерации контрактов:
```
### Прямой генератор

  - skills/_shared/references/commands/spec-auto.md:68
      - обновляет feature spec_design_links;
      - размещает feature-local design в tech-specs/*;
      - рекомендует один concise feature hub;
      - генерирует Component/API/Event/Data Contracts в рамках feature design.

  ### Поддерживает модель через routing

  - skills/_shared/references/commands/spec-design.md:177
      - сам не создаёт FT-*.md;
      - но направляет feature-local contracts/domain behavior в feature tech-spec;
      - использует natural owner и needed_before_tasks, ведущие далее в /prd-to-tasks.

  ### Особый случай

  - skills/_shared/references/commands/foundation-to-tasks.md:115
      - генерирует Component/API/Event/Data Contracts для FT-000;
      - это substrate specs, задуманные как reusable, а не product-feature hubs;
      - однако содержит старую terminology и разрешает /prd-to-tasks создавать feature-local specs.

  ### Только сохраняют или передают старую модель

  - skills/_shared/references/commands/clarify-feature.md:41: содержит пример .memory-bank/tech-specs/FT-<NNN>-<slug>.md.
  - skills/_shared/references/commands/prd.md:101: создаёт feature routing и spec_design_links, но specs не генерирует.
  ```



подумать как оптимальнее разбивать фичи на таски, чтобы не дробить их на 1-2 часовые, а как то более оптимально для AI-first разработки. 

В проекте :
- проананлизировать, почему Текущий статус FT-001 повторяется минимум в пяти местах:
root index, analysis index, features index, EP-001 и FT-001 feature. 


**********************************************************************************
**********************************************************************************

  -----------------

 SDD design specifications, описывающие устройство системы и технические контракты:

  - Architecture Specification — модули, boundaries, source of truth, runtime/deployment.
  - Component Contract — гарантии и ответственность компонентов.
  - API Contract — REST/gRPC/GraphQL, входы, выходы, ошибки, auth.
  - Event Contract — события, очереди, ordering, retry, idempotency.
  - Data Contract — payload между системными boundaries.
  - Data Specification — внутренние модели, БД, persistence, migrations.
  - State Specification — lifecycle, состояния, переходы и guards.
  - Security/access contracts — credentials, permissions, safety rules.
  - Testing Specification — стратегия и критерии проверки связанных контрактов.
  - При необходимости: ADR, runbook и нормативные guides.



  После /spec-design --all развилка простая:

  backbone blocked -> resolve blocker, rerun /spec-design
  backbone complete + foundation changed -> /foundation-to-tasks -> /mb-doctor
  backbone complete + foundation still verified -> /prd-to-tasks FT-001 refresh
