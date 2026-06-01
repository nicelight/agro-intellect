---
description: Exploratory architecture note for Companion IssueStack and human DecisionRecord governance.
status: draft
type: analysis
last_updated: 2026-06-01
---
# Companion Issue Stack and Decision Governance Analysis

## Status

Это exploratory architecture note, а не feature spec и не implementation contract.

Документ фиксирует candidate architecture requirements для будущего обсуждения. Он не создает новую FT, не открывает implementation tasks и не меняет текущие authoritative specs. Перед реализацией решения из этого документа должны быть promoted в подходящие architecture/contracts/states/tech-specs документы.

## Problem

Текущий риск PRBLM-005: Global Flow может получить неявного владельца. Если agents, Bus, UI или backend workflow начнут скрыто решать, куда двигаться дальше, система потеряет auditability, human governance и понятные authority boundaries.

Нужна модель, где Companion может быть transparent coordinator для процесса обсуждения, но binding authority остается в явных human decisions и deterministic backend rules.

## Proposed Direction

Companion ведет общий чат, поддерживает reflection over discussion, выявляет findings/gaps/problems/open questions и складывает их в явный `IssueStack`.

Companion самостоятельно выбирает самый важный или острый `current_issue`, фокусирует discussion на нем, слушает участников и после достаточного обсуждения закрывает issue своим `CompanionConclusion`.

Если дальнейшее движение требует binding decision, Companion создает `CompanionProposal`. Это proposal не становится системным решением до approval/rejection от human role `engineer` или `boss`.

Backend workflow не является скрытым координатором. Он только детерминированно исполняет approved `DecisionRecord`, применяет domain rules, Safety Gate, contracts, visibility rules и audit/event persistence.

## Core Objects

### IssueStack

`IssueStack` - явное структурированное состояние, а не скрытая память LLM.

Минимальные поля candidate model:

- `issue_id`
- `title`
- `description`
- `kind`: `finding | gap | problem | open_question | disagreement`
- `severity`: `P0 | P1 | P2 | P3`
- `status`: `open | current | proposed_closed | closed | blocked`
- `source_refs`
- `created_by`
- `created_at`
- `updated_at`
- `current_focus_reason`
- `waiting_on`: `none | consultant | engineer | boss | any_human | agent`
- `closure_summary`
- `closed_by`: usually `companion`
- `closed_at`

### current_issue

`current_issue` - один issue, на котором Companion держит primary attention.

Companion самостоятельно выбирает следующий `current_issue` из `IssueStack`. При смене фокуса Companion должен объяснить short rationale: почему выбран именно этот issue, например severity, blocker status, unresolved disagreement или dependency on human reaction.

### CompanionConclusion

`CompanionConclusion` - итог Companion по текущему issue.

Conclusion может закрывать discussion issue, но не должен сам по себе быть binding system decision. Если issue требует authority, conclusion должен явно ссылаться на созданный или ожидаемый `DecisionRecord`.

### IssueClosedByCompanion

`IssueClosedByCompanion` - event, фиксирующий, что Companion считает текущий issue закрытым.

Это допустимо для MVP: Companion может сам закрывать текущий issue и рапортовать в чат, что вопрос закрыт. Но closure означает "discussion resolved enough", а не "backend may execute action".

### CompanionProposal

`CompanionProposal` - typed event с предложением направления движения процесса.

Candidate fields:

- `proposal_id`
- `issue_id`
- `version`
- `proposal_text`
- `rationale`
- `recommended_next_direction`
- `visible_to_humans=true`
- `visible_to_agents=false` before approval
- `status`: `pending | approved | rejected | superseded | expired`
- `created_by=companion`
- `created_at`

Важно: proposal не должен быть просто markdown message в общем чате. UI может показывать его жирным текстом, но domain boundary должен видеть typed event.

### DecisionRecord

`DecisionRecord` - единственный binding record для движения процесса, если требуется human authority.

Candidate fields:

- `decision_id`
- `proposal_id`
- `issue_id`
- `proposal_version`
- `decision`: `approved | rejected`
- `decided_by`
- `decider_role`: `engineer | boss`
- `decided_at`
- `rationale_optional`
- `source_refs`

В MVP `boss` имеет такие же rights, как `engineer`. Override/supersede механика для boss не входит в MVP, чтобы не перегружать систему.

### HumanAttentionNeeded

`HumanAttentionNeeded` - typed event для ситуации, когда Companion ожидает human reaction или decision.

Candidate fields:

- `issue_id`
- `reason`
- `needed_role`: `engineer | boss | any_human`
- `visible_to_humans=true`
- `visible_to_agents=false | summary_only`
- `created_at`

В UI это может отображаться как `...` или human attention marker. При этом другие agents могут продолжать писать в чат, а Companion может поддерживать с ними dialogue. Marker означает только то, что Companion считает human reaction/decision полезной или необходимой.

## MVP Role Model

### consultant

`consultant` может давать advice, задавать вопросы и участвовать в discussion.

`consultant` не может approve/reject `CompanionProposal`, не создает `DecisionRecord` и не имеет binding authority.

### engineer

`engineer` участвует в discussion и может approve/reject `CompanionProposal`.

Первый валидный `engineer` или `boss` reaction на конкретную `CompanionProposal.version` создает `DecisionRecord`.

### boss

В MVP `boss` равен `engineer` по правам.

Boss override/supersede над engineer decision intentionally deferred. Если в будущем нужен override, он должен быть отдельной spec decision с audit semantics, а не скрытым изменением старого decision.

## Authority Rules

- Companion может вести discussion, выбирать `current_issue`, создавать/обновлять `IssueStack`, закрывать issues и формулировать `CompanionConclusion`.
- Companion может выбирать лучший proposed resolution при disagreement, но только как `CompanionProposal`.
- `CompanionProposal` становится operative только после первого валидного approval/rejection от `engineer` или `boss`.
- `consultant` input is advisory only.
- Backend исполняет только approved `DecisionRecord` и deterministic rules.
- Safety Gate cannot be bypassed by Companion, engineer, boss, consultant, chat consensus или UI reaction.
- Physical action остается под текущими safety/human approval constraints проекта.

## Visibility Rules

- `CompanionProposal` до approval должен быть `visible_to_humans=true` и `visible_to_agents=false`.
- После approval в agent context может попасть approved summary или resulting `DecisionRecord`, а не raw proposal discussion.
- UI presentation может показывать proposal жирным текстом, но agent context filtering должен опираться на typed visibility metadata, а не на markdown.
- `IssueStack` может иметь разные projections: full human/debug view, agent-safe summary, audit/export view.
- Raw chat, UI Feed, spoiler text и unapproved proposal не должны становиться agent facts.

## Chat Flow Candidate Lifecycle

1. Participants пишут в общий чат: humans и agents выражают opinions, ask questions, answer each other.
2. Companion после каждого relevant message пересматривает `IssueStack`.
3. Companion добавляет новые issues для findings/gaps/problems/open questions.
4. Companion удаляет или закрывает issues, которые считает resolved enough.
5. Companion держит primary attention на `current_issue`.
6. При переходе к новому issue Companion задает один key question всем agents/humans.
7. После key question Companion mostly listens, отвечает по необходимости и поддерживает discussion.
8. Если нужна human reaction/decision, Companion создает `HumanAttentionNeeded`, UI показывает marker вроде `...`.
9. Когда issue выглядит закрытым, Companion публикует `CompanionConclusion` и `IssueClosedByCompanion`.
10. Если нужен следующий direction, Companion создает `CompanionProposal`.
11. Первый валидный approve/reject от `engineer` или `boss` на текущую proposal version создает `DecisionRecord`.
12. Backend исполняет только approved decision через deterministic workflow/services и пишет audit events.

## Integration Impact

### Agent Chat Bus

Нужно проверить, как `IssueStack`, `CompanionProposal`, `DecisionRecord` и visibility flags соотносятся с current Agent Chat Bus contract. Особенно важно не допустить, чтобы unapproved proposal попадал в agent context.

### UI Feed

UI Feed likely должен уметь показывать human-visible proposal, `...` marker, current issue focus и issue closure/conclusion. При этом presentation state не должен становиться agent authority.

### MessageEnvelope and Companion Output

Нужно отделить обычный Companion chat output от typed governance events. Large prose остается presentation/user-facing layer, binding effects должны идти через structured events.

### Backend Workflows

Backend workflow не должен принимать решения вместо Companion/humans. Его роль - deterministic execution of approved decisions, validation, safety checks, persistence and publication.

### Safety Gate

Safety Gate остается hard boundary. `DecisionRecord` может разрешить направление discussion или manual next step, но не может сделать unsafe physical action safe.

### Human Approval

Нужно не смешать два разных approval класса:

- governance approval of `CompanionProposal`;
- safety/action approval for physical plant actions.

Они могут использовать похожие UI controls, но должны иметь разные typed records and semantics.

## Sharp Risks

- Companion может снова стать hidden owner, если `IssueStack` и decisions будут жить только в prompt/history.
- Companion self-closure может скрыть unresolved problem, если closure не audit-backed и не visible.
- First reaction wins может принять слабое решение, если `proposal_version` и role authentication не строгие.
- Disagreement handling может стать arbitrary steering, если Companion не пишет rationale for proposed resolution.
- Visibility boundary может сломаться, если UI markdown используется вместо typed metadata.
- Human attention marker может создать deadlock, если нет `waiting_on` и clear blocked state.
- Governance approval может быть ошибочно смешан с Safety Gate approval.

## Open Questions

- Где должен жить durable `IssueStack`: PostgreSQL runtime state, Agent Chat Bus projection, отдельная state table или later feature-local storage?
- Должен ли `IssueStack` быть global per conversation, per plant, per daily check-in или per workflow session?
- Какие issues Companion может закрывать полностью сам, а какие требуют explicit human acknowledgement?
- Должны ли closed issues попадать в timeline/export snapshots?
- Как долго proposal остается valid, если chat context изменился после его создания?
- Какие exact UI controls нужны для approve/reject и human attention marker?
- Как agent-safe summary должен выглядеть после approval?

## Promotion Criteria

Перед реализацией нужно решить, во что promoted этот analysis note:

- architecture update, если меняется authority model или Global Flow model;
- contract specs, если появляются stable event schemas;
- state spec, если `IssueStack` становится durable lifecycle;
- FT spec, если это становится самостоятельной user-facing capability;
- updates to FT-004/FT-005/FT-011/FT-012/FT-014, если feature-local behavior затрагивает Bus, UI Feed, UI surface, Companion output или human approval.

До promotion этот документ должен считаться discussion artifact, а не binding implementation source.
