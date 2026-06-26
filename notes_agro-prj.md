

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
