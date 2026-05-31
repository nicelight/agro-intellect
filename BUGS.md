# BUGS: PRD Review Blockers

## Critical

### BUG-1 - spec-index.md placeholder-only и не готов для `/prd`

Где: `.memory-bank/spec-index.md`, `.memory-bank/prd.md`, `project_dossier.md`.

Проблема: PRD завершён как clarified input, но SDD route map всё ещё содержит `TBD` / `FT-XXX` placeholders и не регистрирует реальные design areas из PRD/dossier.

Риск: `/prd` decomposition может пойти без маршрутизации критичных specs: Agent Chat Bus, Agno boundary, data model, photo protocol, dataset lifecycle, Safety Gate, testing.

Ожидаемый фикс: через `/spec-init` заполнить реальные planned/candidate/not_applicable areas и не маркировать пустые draft/TBD директории как authoritative specs.

### BUG-2 - Safety Gate / HumanApproval state machine не определён

Где: `.memory-bank/prd.md`, `.memory-bank/constitution.md`, `project_dossier.md`.

Проблема: зафиксировано правило fresh data + safety check + human approval, но не определено, кто и как фиксирует `safety_check_passed`, к каким measurement refs и action params привязано approval, когда оно истекает или инвалидируется.

Риск: replay approval, approval для одних параметров может примениться к другим, невозможно написать надёжные tests.

Ожидаемый фикс: определить `SafetyGateDecision` / `HumanApproval` fields: `action_type`, exact params, `risk_class`, `measurement_refs`, freshness window, `safety_check_result`, `approved_at`, `expires_at`, `status`, invalidation rules, one-time/replay policy.

### BUG-3 - data lifecycle specs и atomic write protocol отсутствуют

Где: `.memory-bank/prd.md` Runtime State / Photo / Timeline / Dataset, `.memory-bank/invariants.md`.

Проблема: PRD требует PostgreSQL authority, filesystem photos, manifests, timeline, dataset lifecycle и sync, но не определены authoritative data/state specs и атомарность записи между DB, filesystem, manifest и timeline.

Риск: partial writes: файл записан, DB rollback; DB commit, manifest failed; timeline append failed; sha mismatch; recovery policy неясен.

Ожидаемый фикс: создать/register `domains/data_model.md`, `domains/photo_protocol.md`, `states/dataset_lifecycle.md`, `states/human_review.md`, `states/sync_lifecycle.md`, `domains/sensor_window.md`; задать `photo_catalog.status=pending|ready|failed`, order of operations, idempotency key, recovery/retry rules, DB constraints.
