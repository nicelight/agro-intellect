from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
import uuid

import pytest

from backend.app.access_admin.actor_context import (
    ActorContext,
    ActorContextDenied,
    ActorContextResolver,
    AuthProvenance,
    AuthTransport,
)
from backend.app.access_admin.models import Account, FarmMembership, LocalSession
from backend.app.access_admin.permissions import (
    GrantStatus,
    OperationKind,
    PermissionSource,
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantPermissionContext,
    PlantSnapshot,
    PlantStatus,
    ROLE_POLICIES,
    RolePreset,
)
from backend.app.access_admin.session_service import ValidatedSession


NOW = datetime(2026, 7, 2, 8, 0, tzinfo=timezone.utc)


class StubSessionValidator:
    def __init__(self, result: ValidatedSession | None) -> None:
        self.result = result
        self.calls: list[object] = []

    def validate_session(self, raw_token: object) -> ValidatedSession | None:
        self.calls.append(raw_token)
        return self.result


class SnapshotProvider:
    def __init__(self, snapshots: dict[uuid.UUID, PlantAccessSnapshot]) -> None:
        self.snapshots = snapshots
        self.calls: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = []

    def __call__(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> PlantAccessSnapshot | None:
        self.calls.append((farm_id, membership_id, plant_id))
        return self.snapshots.get(plant_id)


def _validated_session(role_preset: str = "boss") -> ValidatedSession:
    account_id = uuid.uuid4()
    account = Account(
        account_id=account_id,
        login_name=f"{role_preset}.user",
        display_name="Test User",
        account_status="active",
        password_hash="test-only-hash",
    )
    membership = FarmMembership(
        membership_id=uuid.uuid4(),
        account_id=account_id,
        farm_id=uuid.uuid4(),
        role_preset=role_preset,
        membership_status="active",
    )
    session = LocalSession(
        session_id=uuid.uuid4(),
        account_id=account_id,
        token_hash="a" * 64,
        created_at=NOW,
        expires_at=NOW + timedelta(days=7),
        auth_method="local_password",
    )
    return ValidatedSession(session=session, account=account, membership=membership)


def _snapshot(
    validated: ValidatedSession,
    *,
    plant_status: PlantStatus = PlantStatus.ACTIVE,
    grant_status: GrantStatus = GrantStatus.ACTIVE,
    approve_actions: bool = False,
    include_grant: bool = True,
) -> PlantAccessSnapshot:
    plant_id = uuid.uuid4()
    grant = None
    if include_grant:
        grant = PlantGrantSnapshot(
            grant_id=uuid.uuid4(),
            membership_id=validated.membership.membership_id,
            farm_id=validated.membership.farm_id,
            plant_id=plant_id,
            status=grant_status,
            plant_approve_actions=approve_actions,
        )
    return PlantAccessSnapshot(
        plant=PlantSnapshot(
            plant_id=plant_id,
            farm_id=validated.membership.farm_id,
            status=plant_status,
        ),
        grant=grant,
    )


def _actor(
    validated: ValidatedSession,
    snapshot: PlantAccessSnapshot,
):
    validator = StubSessionValidator(validated)
    provider = SnapshotProvider({snapshot.plant.plant_id: snapshot})
    resolver = ActorContextResolver(
        session_validator=validator,
        snapshot_provider=provider,
    )
    actor = resolver.resolve(
        request_id=" req-test ",
        raw_session_token="synthetic-test-token",
        transport=AuthTransport.COOKIE,
    )
    return actor, validator, provider


def _permission_values(permission: PlantPermissionContext) -> tuple[bool, ...]:
    return (
        permission.can_read,
        permission.can_comment,
        permission.can_operate,
        permission.can_create_domain_tasks,
        permission.can_manage_access,
        permission.can_approve_actions,
    )


def test_actor_context_resolves_canonical_shape_after_session_validation():
    validated = _validated_session("boss")
    snapshot = _snapshot(validated, include_grant=False)
    actor, validator, provider = _actor(validated, snapshot)

    assert validator.calls == ["synthetic-test-token"]
    assert provider.calls == []
    assert actor.request_id == "req-test"
    assert actor.session_id == validated.session.session_id
    assert actor.account_id == validated.account.account_id
    assert actor.farm_id == validated.membership.farm_id
    assert actor.membership_id == validated.membership.membership_id
    assert actor.role_preset is RolePreset.BOSS
    assert actor.membership_status.value == "active"
    assert actor.auth_provenance == AuthProvenance(
        auth_method="local_password",
        session_created_at=NOW,
        session_expires_at=NOW + timedelta(days=7),
        transport=AuthTransport.COOKIE,
    )
    assert {field.name for field in fields(ActorContext)} == {
        "request_id",
        "session_id",
        "account_id",
        "farm_id",
        "membership_id",
        "role_preset",
        "membership_status",
        "auth_provenance",
        "plant_permission_resolver",
    }
    assert {field.name for field in fields(AuthProvenance)} == {
        "auth_method",
        "session_created_at",
        "session_expires_at",
        "transport",
    }
    assert all(
        forbidden not in repr(actor).lower()
        for forbidden in ("password_hash", "token_hash", "authorization", "cookie=")
    )
    with pytest.raises(TypeError):
        ActorContext(request_id="bypass")


def test_actor_context_nested_authority_is_immutable_after_resolution():
    validated = _validated_session("engineer")
    snapshot = _snapshot(validated, approve_actions=False)
    actor, _validator, _provider = _actor(validated, snapshot)
    resolver = actor.plant_permission_resolver
    permission_before = actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.NORMAL_READ,
    )

    replacements = {
        "_farm_id": uuid.uuid4(),
        "_membership_id": uuid.uuid4(),
        "_membership_status": "disabled",
        "_role_preset": RolePreset.BOSS,
        "_snapshot_provider": lambda **_kwargs: snapshot,
    }
    for attribute, replacement in replacements.items():
        with pytest.raises(FrozenInstanceError):
            setattr(resolver, attribute, replacement)

    permission_after = actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.NORMAL_READ,
    )
    assert actor.role_preset is RolePreset.ENGINEER
    assert permission_after == permission_before
    assert permission_after.source is PermissionSource.PLANT_ACCESS_GRANT
    assert permission_after.can_manage_access is False
    assert permission_after.can_approve_actions is False


def test_invalid_session_and_identity_fail_before_permission_provider():
    provider = SnapshotProvider({})
    validator = StubSessionValidator(None)
    resolver = ActorContextResolver(
        session_validator=validator,
        snapshot_provider=provider,
    )

    with pytest.raises(ActorContextDenied) as caught:
        resolver.resolve(
            request_id="req-denied",
            raw_session_token="invalid-test-token",
            transport="cookie",
        )

    assert str(caught.value) == "Actor context unavailable."
    assert validator.calls == ["invalid-test-token"]
    assert provider.calls == []

    disabled = _validated_session("engineer")
    disabled.membership.membership_status = "disabled"
    resolver = ActorContextResolver(
        session_validator=StubSessionValidator(disabled),
        snapshot_provider=provider,
    )
    with pytest.raises(ActorContextDenied):
        resolver.resolve(
            request_id="req-disabled",
            raw_session_token="synthetic-test-token",
            transport="cookie",
        )
    assert provider.calls == []

    active = _validated_session("engineer")
    malformed_validator = StubSessionValidator(
        ValidatedSession(
            session=object(),
            account=active.account,
            membership=active.membership,
        )
    )
    resolver = ActorContextResolver(
        session_validator=malformed_validator,
        snapshot_provider=provider,
    )
    with pytest.raises(ActorContextDenied):
        resolver.resolve(
            request_id="req-malformed",
            raw_session_token="synthetic-test-token",
            transport="cookie",
        )
    assert provider.calls == []


@pytest.mark.parametrize(
    ("request_id", "transport"),
    [("", "cookie"), ("   ", "cookie"), ("req-test", "header")],
)
def test_invalid_request_boundary_fails_before_session_validation(
    request_id: str,
    transport: str,
):
    validator = StubSessionValidator(_validated_session())
    resolver = ActorContextResolver(
        session_validator=validator,
        snapshot_provider=SnapshotProvider({}),
    )

    with pytest.raises(ActorContextDenied):
        resolver.resolve(
            request_id=request_id,
            raw_session_token="synthetic-test-token",
            transport=transport,
        )

    assert validator.calls == []


def test_fixed_role_policy_and_active_permissions_match_canonical_matrix():
    assert set(ROLE_POLICIES) == {
        RolePreset.BOSS,
        RolePreset.ENGINEER,
        RolePreset.CONSULTANT,
    }
    consultant_policy = ROLE_POLICIES[RolePreset.CONSULTANT]
    assert consultant_policy.can_read is True
    assert consultant_policy.can_comment is True
    assert consultant_policy.can_operate is False
    assert consultant_policy.can_create_domain_tasks is False
    assert consultant_policy.can_manage_access is False
    assert consultant_policy.can_approve_actions is False
    assert consultant_policy.can_approve_governance is False

    boss_session = _validated_session("boss")
    boss_snapshot = _snapshot(boss_session, include_grant=False)
    boss, _validator, _provider = _actor(boss_session, boss_snapshot)
    boss_permission = boss.resolve_plant_permission(
        boss_snapshot.plant.plant_id,
        OperationKind.NORMAL_READ,
    )
    assert _permission_values(boss_permission) == (True, True, True, True, True, True)
    assert boss_permission.source is PermissionSource.BOSS_ROLE
    assert boss_permission.grant_id is None

    engineer_session = _validated_session("engineer")
    engineer_snapshot = _snapshot(engineer_session, approve_actions=True)
    engineer, _validator, _provider = _actor(engineer_session, engineer_snapshot)
    engineer_permission = engineer.resolve_plant_permission(
        engineer_snapshot.plant.plant_id,
        OperationKind.APPROVE_ACTION,
    )
    assert _permission_values(engineer_permission) == (True, True, True, True, False, True)
    assert engineer_permission.source is PermissionSource.PLANT_ACCESS_GRANT
    assert engineer_permission.grant_id == engineer_snapshot.grant.grant_id

    engineer_without_override = PlantAccessSnapshot(
        plant=engineer_snapshot.plant,
        grant=PlantGrantSnapshot(
            grant_id=engineer_snapshot.grant.grant_id,
            membership_id=engineer_snapshot.grant.membership_id,
            farm_id=engineer_snapshot.grant.farm_id,
            plant_id=engineer_snapshot.grant.plant_id,
            status=GrantStatus.ACTIVE,
            plant_approve_actions=False,
        ),
    )
    engineer, _validator, _provider = _actor(
        engineer_session,
        engineer_without_override,
    )
    assert engineer.resolve_plant_permission(
        engineer_snapshot.plant.plant_id,
        OperationKind.APPROVE_ACTION,
    ).can_approve_actions is False

    consultant_session = _validated_session("consultant")
    consultant_snapshot = _snapshot(consultant_session, approve_actions=True)
    consultant, _validator, _provider = _actor(
        consultant_session,
        consultant_snapshot,
    )
    consultant_permission = consultant.resolve_plant_permission(
        consultant_snapshot.plant.plant_id,
        OperationKind.APPROVE_ACTION,
    )
    assert _permission_values(consultant_permission) == (
        True,
        True,
        False,
        False,
        False,
        False,
    )
    assert consultant_permission.source is PermissionSource.PLANT_ACCESS_GRANT


@pytest.mark.parametrize(
    "failure",
    ["missing", "revoked", "membership_mismatch", "farm_mismatch", "plant_mismatch"],
)
def test_missing_revoked_or_mismatched_grant_is_no_leak_denied(failure: str):
    validated = _validated_session("engineer")
    snapshot = _snapshot(validated)
    if failure == "missing":
        snapshot = PlantAccessSnapshot(plant=snapshot.plant)
    elif failure == "revoked":
        snapshot = PlantAccessSnapshot(
            plant=snapshot.plant,
            grant=PlantGrantSnapshot(
                grant_id=snapshot.grant.grant_id,
                membership_id=snapshot.grant.membership_id,
                farm_id=snapshot.grant.farm_id,
                plant_id=snapshot.grant.plant_id,
                status=GrantStatus.REVOKED,
                plant_approve_actions=True,
            ),
        )
    else:
        membership_id = snapshot.grant.membership_id
        farm_id = snapshot.grant.farm_id
        plant_id = snapshot.grant.plant_id
        if failure == "membership_mismatch":
            membership_id = uuid.uuid4()
        elif failure == "farm_mismatch":
            farm_id = uuid.uuid4()
        elif failure == "plant_mismatch":
            plant_id = uuid.uuid4()
        snapshot = PlantAccessSnapshot(
            plant=snapshot.plant,
            grant=PlantGrantSnapshot(
                grant_id=snapshot.grant.grant_id,
                membership_id=membership_id,
                farm_id=farm_id,
                plant_id=plant_id,
                status=GrantStatus.ACTIVE,
                plant_approve_actions=True,
            ),
        )
    actor, _validator, _provider = _actor(validated, snapshot)

    permission = actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.NORMAL_READ,
    )

    assert permission.plant_id == snapshot.plant.plant_id
    assert permission.plant_status is None
    assert _permission_values(permission) == (False, False, False, False, False, False)
    assert permission.source is PermissionSource.DENIED
    assert permission.grant_id is None


def test_archived_permission_effect_is_bounded_and_fail_closed():
    validated = _validated_session("engineer")
    snapshot = _snapshot(
        validated,
        plant_status=PlantStatus.ARCHIVED,
        approve_actions=True,
    )
    actor, _validator, _provider = _actor(validated, snapshot)

    normal = actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.NORMAL_READ,
    )
    history = actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.RETAINED_HISTORY_READ,
    )
    approval = actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.APPROVE_ACTION,
    )

    assert normal.plant_status is PlantStatus.ARCHIVED
    assert _permission_values(normal) == (False, False, False, False, False, False)
    assert _permission_values(history) == (True, True, False, False, False, False)
    assert _permission_values(approval) == (False, False, False, False, False, False)
    assert history.source is PermissionSource.PLANT_ACCESS_GRANT

    boss_session = _validated_session("boss")
    boss_snapshot = _snapshot(
        boss_session,
        plant_status=PlantStatus.ARCHIVED,
        include_grant=False,
    )
    boss, _validator, _provider = _actor(boss_session, boss_snapshot)
    manage = boss.resolve_plant_permission(
        boss_snapshot.plant.plant_id,
        OperationKind.MANAGE_LIFECYCLE,
    )
    assert _permission_values(manage) == (False, False, False, False, True, False)


def test_unknown_plant_provider_error_and_farm_mismatch_fail_closed():
    validated = _validated_session("boss")
    unknown_provider = SnapshotProvider({})
    actor = ActorContextResolver(
        session_validator=StubSessionValidator(validated),
        snapshot_provider=unknown_provider,
    ).resolve(
        request_id="req-unknown",
        raw_session_token="synthetic-test-token",
        transport="bearer",
    )
    unknown_id = uuid.uuid4()
    denied = actor.resolve_plant_permission(unknown_id, OperationKind.NORMAL_READ)
    assert denied.source is PermissionSource.DENIED
    assert denied.plant_status is None

    def failing_provider(**_kwargs):
        raise RuntimeError("synthetic provider failure")

    failing_actor = ActorContextResolver(
        session_validator=StubSessionValidator(validated),
        snapshot_provider=failing_provider,
    ).resolve(
        request_id="req-provider-failure",
        raw_session_token="synthetic-test-token",
        transport="cookie",
    )
    denied = failing_actor.resolve_plant_permission(
        unknown_id,
        OperationKind.NORMAL_READ,
    )
    assert denied.source is PermissionSource.DENIED

    mismatched = PlantAccessSnapshot(
        plant=PlantSnapshot(
            plant_id=unknown_id,
            farm_id=uuid.uuid4(),
            status=PlantStatus.ACTIVE,
        )
    )
    mismatch_actor, _validator, _provider = _actor(validated, mismatched)
    denied = mismatch_actor.resolve_plant_permission(
        mismatched.plant.plant_id,
        OperationKind.NORMAL_READ,
    )
    assert denied.source is PermissionSource.DENIED
    assert _permission_values(denied) == (False, False, False, False, False, False)


def test_invalid_operation_and_malformed_snapshot_fail_closed():
    validated = _validated_session("engineer")
    snapshot = _snapshot(validated)
    actor, _validator, provider = _actor(validated, snapshot)

    denied = actor.resolve_plant_permission(snapshot.plant.plant_id, "delete")

    assert denied.source is PermissionSource.DENIED
    assert provider.calls == []

    malformed_snapshot = PlantAccessSnapshot(plant=None)
    malformed_actor = ActorContextResolver(
        session_validator=StubSessionValidator(validated),
        snapshot_provider=lambda **_kwargs: malformed_snapshot,
    ).resolve(
        request_id="req-malformed-snapshot",
        raw_session_token="synthetic-test-token",
        transport="cookie",
    )

    denied = malformed_actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.NORMAL_READ,
    )
    assert denied.source is PermissionSource.DENIED
    assert denied.plant_status is None


def test_permission_context_exposes_exact_canonical_envelope():
    validated = _validated_session("consultant")
    snapshot = _snapshot(validated)
    actor, _validator, provider = _actor(validated, snapshot)
    permission = actor.resolve_plant_permission(
        snapshot.plant.plant_id,
        OperationKind.NORMAL_READ,
    )

    assert {field.name for field in fields(PlantPermissionContext)} == {
        "plant_id",
        "plant_status",
        "can_read",
        "can_comment",
        "can_operate",
        "can_create_domain_tasks",
        "can_manage_access",
        "can_approve_actions",
        "source",
        "grant_id",
    }
    assert provider.calls == [
        (
            validated.membership.farm_id,
            validated.membership.membership_id,
            snapshot.plant.plant_id,
        )
    ]
