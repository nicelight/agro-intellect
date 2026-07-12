

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

sleep 240m && codex -c model_reasoning_effort=max resume 019ec059-2934-7a40-8bc2-eee1e029098b "Задачу опишем тут"

sleep 140m && codex -c model_reasoning_effort=max "$(< prompt.md)" 




**************************************************************************
                      Текущее окно
**************************************************************************




Проведи прайминг $mb чтобы подготовиться к $.
  Учитывай уже созданные design SDD specs из других features.
  После прайминга начни разложение FT-007 на Таски и создание необходимого
  пакета design sdd specs.
  ПОльзуйся сабагентами для наполнения своего контекста, береги контекстное
  окно для стратегического мышления, не забивай контекстное окно вызовами
  tools, которые можно уверенно делегировать сабагентам.

*********************************************************************************
                          TODO 
*********************************************************************************


**********************************************************************************
                                  ОРКЕСТРАЦИЯ
**********************************************************************************
## Роль
Оркестратор

## Стратегическая задача
Достигать поставленной цели, выполняя оркестрацию агентов, при этом беречь свое контекстное окно, производя только стратегическое мышление для компетентного и вдумчивого руководства процессом.
Ничего не делай сам, не загромождай себя второстепенными инструкциями и вызовами tools.
Если возможно что то делегировать воркеру, делегируй это.
 Старайся чтобы /execute выполнял один агент а /verify + /red-verify другой.

## Поставленная Цель
действуй по /autopilot

## Контекст 

**********************************************************************************
**********************************************************************************



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

  7. Мемори банк сейчас разволачивается в hidden дирректории? Это надо исправить.


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
    
            ---------------   