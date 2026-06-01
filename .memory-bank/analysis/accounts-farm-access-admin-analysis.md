---
description: Exploratory analysis for future accounts, boss admin, personnel, plant management, and access control.
status: draft
type: analysis
last_updated: 2026-06-01
---
# Accounts, Farm Access, and Boss Admin Analysis

## Status

Это exploratory analysis note, а не PRD, не feature spec и не implementation task.

Текущий MVP явно ограничен local-first single-user / one-plant scope. Аккаунты, персонал, роли, несколько Plants и админка владельца расширяют продукт за пределы текущего MVP. Перед реализацией нужно будет обновить PRD, требования, epics/features, architecture, security model, contracts/states and task decomposition.

## Problem

Нужен вариант будущего продукта, где системой пользуется не один локальный оператор, а владелец/руководитель фермы и команда.

Главный аккаунт, который регистрирует ферму в системе, должен иметь boss/admin surface:

- видеть список персонала;
- добавлять и удалять пользователей;
- менять права пользователей;
- создавать новые Plants;
- убирать старые Plants;
- назначать права конкретных пользователей на конкретные Plants.

## Product Goal

Дать владельцу фермы управляемую модель доступа:

- кто может видеть данные фермы;
- кто может работать с конкретным Plant;
- кто может вводить измерения и фото;
- кто может получать рекомендации;
- кто может подтверждать решения или действия;
- кто может управлять персоналом и Plants.

## Candidate Roles

### Boss

Главный аккаунт фермы.

Candidate rights:

- управляет профилем фермы;
- добавляет/удаляет персонал;
- назначает роли;
- создает, архивирует и восстанавливает Plants;
- назначает доступ пользователей к Plants;
- видит audit по ключевым действиям;
- может выполнять все права Engineer, если не ограничено будущей политикой.

### Engineer

Операционный пользователь, который ведет Plants.

Candidate rights:

- видит назначенные Plants;
- ведет daily check-in;
- загружает фото;
- вводит pH/EC и другие измерения;
- видит plant state, history, tasks, recommendations;
- выполняет check/measurement/follow-up tasks;
- может подтверждать или отклонять action proposals только если Boss выдал такое право.

### Consultant

Советник без операционной власти по умолчанию.

Candidate rights:

- видит назначенные Plants или только выбранные snapshots;
- читает observations, фото, историю, recommendations;
- оставляет комментарии/advice;
- не может менять plant state, measurements, tasks, approvals или user permissions без отдельного права.

## Permission Model

Минимальная будущая модель должна разделять два уровня:

1. Farm-level permissions.
2. Plant-level permissions.

### Farm-Level Permissions

Candidate permissions:

- `farm_manage_profile`
- `users_view`
- `users_invite`
- `users_remove`
- `users_change_roles`
- `plants_create`
- `plants_archive`
- `plants_assign_access`
- `audit_view`

### Plant-Level Permissions

Candidate permissions:

- `plant_view`
- `plant_update_observations`
- `plant_upload_photos`
- `plant_record_measurements`
- `plant_view_recommendations`
- `plant_manage_tasks`
- `plant_record_follow_up`
- `plant_approve_actions`
- `plant_manage_settings`

KISS direction: start with role presets, then allow per-Plant overrides only where needed.

Example presets:

| Role | Default farm rights | Default plant rights |
|---|---|---|
| Boss | All farm rights | All plant rights |
| Engineer | None or limited team visibility | Operational rights for assigned Plants |
| Consultant | None | Read/comment/advice rights for assigned Plants |

## Core Objects

### Account

User identity for login.

Candidate fields:

- `account_id`
- `email` or phone/login identifier
- `display_name`
- `status`: `active | invited | disabled | removed`
- `created_at`
- `last_login_at`

### Farm

Tenant-like boundary for data ownership.

Candidate fields:

- `farm_id`
- `name`
- `created_by_account_id`
- `created_at`
- `status`: `active | archived`

### FarmMembership

Relationship between Account and Farm.

Candidate fields:

- `membership_id`
- `farm_id`
- `account_id`
- `role`: `boss | engineer | consultant`
- `status`: `invited | active | disabled | removed`
- `created_by`
- `created_at`
- `updated_at`

### Plant

Plant managed inside a Farm.

Candidate fields:

- `plant_id`
- `farm_id`
- `name`
- `kind` / crop metadata
- `status`: `active | archived`
- `created_by`
- `created_at`
- `archived_at`

### PlantAccessGrant

Explicit permission assignment for an Account/Membership on a Plant.

Candidate fields:

- `grant_id`
- `farm_id`
- `plant_id`
- `account_id` or `membership_id`
- `permissions`
- `granted_by`
- `created_at`
- `revoked_at`

## Boss Admin Surface

Candidate screens:

- Personnel list.
- Invite/add user.
- User detail and role editor.
- Plant list.
- Create Plant.
- Archive/restore Plant.
- Plant access matrix: users x Plants.
- Audit/activity view for admin actions.

Minimum useful workflows:

1. Boss creates Farm during registration.
2. Boss creates one or more Plants.
3. Boss invites Engineer or Consultant.
4. Boss assigns user role.
5. Boss grants user access to one or more Plants.
6. User logs in and sees only allowed Plants.
7. Boss changes or revokes access.
8. Archived Plant disappears from normal workflows but remains audit/history accessible to authorized roles.

## Security And Authority Implications

This extension changes the security model substantially.

Required future decisions:

- hosted server vs local LAN only vs hybrid;
- authentication method;
- password/session/token lifecycle;
- invitation flow;
- password reset or account recovery;
- farm/tenant isolation;
- authorization checks on every API;
- audit trail for admin and permission changes;
- data migration from `tomato_001` single-plant assumptions;
- whether Boss can override Engineer decisions;
- whether Consultants can see private photos and measurements;
- how Safety Gate and human approval map to roles.

Important boundary:

Boss admin approval is not the same as Safety Gate physical-action approval. A user may have admin rights but still must follow Safety Gate + human approval rules for physical plant actions.

## Impact On Current MVP Specs

Likely affected areas:

- Constitution: current low-maintenance MVP explicitly excludes multi-user/SaaS-like architecture.
- PRD and requirements: new account, farm, personnel, role, and Plant management requirements.
- Architecture: tenant/farm boundary, auth module, authorization middleware, deployment model.
- Runtime data model: every plant-bound entity likely needs `farm_id` and authorization context.
- API guidelines: authentication, sessions, authorization errors, permission checks.
- UI/PWA: login, boss admin, Plant selector, permission-aware views.
- Safety approval: role required to approve physical-action proposals.
- Dataset governance: tenant/farm isolation for evidence and exports.
- Local security/lazy sync: server-hosted or multi-device access changes assumptions.

## Open Questions

- Это должен быть cloud/server product или локальная фермерская установка в LAN?
- Может ли один Boss владеть несколькими Farms?
- Может ли один Engineer/Consultant работать в нескольких Farms?
- Нужен ли self-registration для персонала или только invite от Boss?
- Какие действия Engineer может делать без Boss approval?
- Может ли Consultant только читать, или может создавать recommendations/tasks?
- Кто может approve physical-action proposals?
- Что значит "убрать Plant": archive, delete, hide, transfer ownership?
- Нужна ли история изменения прав и audit для каждого admin action?
- Нужны ли billing/subscription boundaries?
- Как мигрировать текущий `tomato_001` MVP в модель Farm/Plant?

## Suggested Next Product Step

Перед spec implementation нужен отдельный discovery/PRD slice:

1. Clarify deployment model: local LAN, hosted server, or hybrid.
2. Decide role model and permission presets.
3. Decide Farm/Plant ownership model.
4. Decide whether multi-account support is a new MVP version or a post-MVP phase.
5. Update Constitution or explicitly create a new product stage that relaxes current no multi-user/no SaaS constraints.
6. Write PRD addendum or new PRD section for Accounts, Farm Admin, Personnel, and Plant Access.

## Non-Goals For Current MVP

Until promoted into PRD/specs, this analysis does not authorize:

- implementation of login/accounts;
- multi-user database schema;
- server deployment;
- Plant multi-tenancy;
- permission-aware API rewrites;
- boss admin UI;
- changes to current single-plant `tomato_001` MVP tasks.
