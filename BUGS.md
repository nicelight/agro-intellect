# BUGS: project_dossier.md logical review

## Critical

### BUG-1 - MessageEnvelope.can_train_on смешан с dataset-level can_train_on

Где: `project_dossier.md` около строк 545, 1468, 1811, 1908.

Проблема: `MessageEnvelope.can_train_on` описан как обучающий сигнал сообщения, но правило `can_train_on=true` задано через `dataset.curator_decision`, `dataset.split`, `dataset.status` и `dataset.confirmation_source`.

Риск: агент может выставить trainable-флаг на сообщение и обойти dataset governance.

Фикс:

- убрать `can_train_on` из `MessageEnvelope`;
- оставить `can_train_on` только на dataset/photo catalog/export snapshot уровне;
- `can_train_on=true` выставляется только через `Training Data Curator Agent` + `Dataset Governance Agent`;
- `Training Data Curator Agent` может сам выбирать обычные данные для обучения при сильных `evidence_refs`;
- human review требуется только для conflict, low confidence, rare valuable example, gold candidate или high-impact label;
- обычные агенты публикуют observation/hypothesis/recommendation, но не решают пригодность данных для обучения.

### BUG-2 - UIFeedEvent.source_agent_id не подходит для system/user UI events

Где: `project_dossier.md` около строк 667, 893.

Проблема: canonical `UIFeedEvent` требует `source_agent_id`, но UI Feed включает события типа `system_ui_status`, где источником не является агент.

Риск: schema будет ломать валидные system UI events или заставит подставлять fake agent id.

Ожидаемый фикс: заменить `source_agent_id` на `source_type + source_id` или явно ограничить `source_agent_id` только agent-событиями.

### BUG-3 - agent_clarification_request требует target_agent_id, но поле не закреплено в контракте

Где: `project_dossier.md` около строк 704, 1745-1770.

Проблема: текст говорит, что `agent_clarification_request` публикуется как Bus event с `target_agent_id`, но `target_agent_id` не указан в полях `BusEventEnvelope` или `MessageEnvelope`.

Риск: разные реализации положат target в разные места или потеряют адресацию уточнения.

Ожидаемый фикс: зафиксировать `payload.target_agent_id` как обязательное поле для `event_type=agent_clarification_request`.

### BUG-4 - timeline.jsonl неясно валидирует Bus events или также UI Feed snapshots

Где: `project_dossier.md` около строк 680, 1529-1531, 1749.

Проблема: сказано, что `timeline.jsonl` может хранить snapshot/export copy UI Feed event, но `timeline_event.schema.json` описывается в контексте Bus/timeline event.

Риск: непонятно, должна ли timeline schema принимать только `BusEventEnvelope` или union с `UIFeedEventSnapshot`.

TODO на анализ: принять архитектурное решение о роли `timeline.jsonl`.

Вариант A: `timeline.jsonl` = только доменный audit/event log.

- хранит Bus/system/task/domain events;
- UI Feed events не пишет;
- `timeline_event.schema.json` валидирует доменные/audit events;
- UI snapshots допустимы только в photo JSON/export snapshot.

Вариант B: `timeline.jsonl` = общий append-only log всего.

- хранит Bus events + UI Feed snapshots;
- `timeline_event.schema.json` должен стать union: `BusEventEnvelope | UIFeedEventSnapshot`;
- проще видеть полную историю, но смешиваются domain/audit и UI presentation.

Предпочтительный вариант: A. Он лучше сохраняет границу `Agent Chat Bus = доменный поток`, `UI Feed = представление`.

## Medium

### BUG-5 - InfluxDB выбран, но roadmap оставляет InfluxDB/TimescaleDB

Где: `project_dossier.md` около строк 140, 2042.

Проблема: InfluxDB уже назначен time-series authority, но roadmap оставляет альтернативу `InfluxDB/TimescaleDB`.

Риск: появляется лишняя архитектурная развилка.

Ожидаемый фикс: оставить только InfluxDB.

### BUG-6 - Training export описан как PostgreSQL + InfluxDB до появления InfluxDB

Где: `project_dossier.md` около строк 1195-1201.

Проблема: InfluxDB появится позже, но training export описан как сборка из PostgreSQL и InfluxDB.

Риск: MVP может быть ошибочно прочитан как требующий InfluxDB.

Ожидаемый фикс: уточнить, что MVP export собирается из PostgreSQL + файлов, а InfluxDB добавляется после датчиков.

### BUG-7 - photo_id глобально уникален, но training export key включает plant_id + captured_at

Где: `project_dossier.md` около строк 1180, 1189-1193.

Проблема: `photo_catalog.photo_id` глобально уникален, но `photo_id + plant_id + captured_at` назван ключом training export.

Риск: неясно, что является настоящим key.

Ожидаемый фикс: назвать `photo_id + plant_id + captured_at` correlation tuple/export join tuple, а не key.

### BUG-8 - Agno output превращается в MessageEnvelope, но не все Bus events являются MessageEnvelope

Где: `project_dossier.md` около строк 202, 525, 563.

Проблема: формулировка говорит, что output становится фактом после превращения в `MessageEnvelope`, но user/system/task events проходят как typed `BusEventEnvelope.payload`, без `MessageEnvelope`.

Риск: реализация может ошибочно требовать `MessageEnvelope` для всех событий.

Ожидаемый фикс: уточнить: agent output проходит через `MessageEnvelope`; non-agent events проходят через typed `BusEventEnvelope.payload`.
