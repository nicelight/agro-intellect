from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone
import uuid

import pytest

from backend.app.access_admin.actor_context import (
    ActorContextResolver,
    AuthTransport,
)
from backend.app.access_admin.context_builders import (
    AuthorizationScope,
    ContextSourceKind,
    PlantContextCandidate,
    build_authorized_plant_context,
)
from backend.app.access_admin.models import Account, FarmMembership, LocalSession
from backend.app.access_admin.permissions import (
    GrantStatus,
    OperationKind,
    PermissionSource,
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantSnapshot,
    PlantStatus,
)
from backend.app.access_admin.session_service import ValidatedSession
from backend.app.core.security import generate_session_token


NOW = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)


class StaticSessionValidator:
    def __init__(self, validated: ValidatedSession) -> None:
        self.validated = validated

    def validate_session(self, _raw_token: object) -> ValidatedSession:
        return self.validated


class CandidateProbe:
    def __iter__(self):
        raise AssertionError("denied context must not inspect candidate data")


def _validated_session(role_preset: str) -> ValidatedSession:
    account_id = uuid.uuid4()
    return ValidatedSession(
        account=Account(
            account_id=account_id,
            login_name=f"{role_preset}.context",
            display_name="Context User",
            account_status="active",
            password_hash="test-only-password-hash",
        ),
        membership=FarmMembership(
            membership_id=uuid.uuid4(),
            account_id=account_id,
            farm_id=uuid.uuid4(),
            role_preset=role_preset,
            membership_status="active",
        ),
        session=LocalSession(
            session_id=uuid.uuid4(),
            account_id=account_id,
            token_hash="a" * 64,
            created_at=NOW,
            expires_at=NOW + timedelta(days=7),
            auth_method="local_password",
        ),
    )


def _actor(
    role_preset: str,
    *,
    plant_status: PlantStatus = PlantStatus.ACTIVE,
    grant_status: GrantStatus = GrantStatus.ACTIVE,
    include_grant: bool = True,
):
    validated = _validated_session(role_preset)
    plant_id = uuid.uuid4()
    grant = None
    if include_grant:
        grant = PlantGrantSnapshot(
            grant_id=uuid.uuid4(),
            membership_id=validated.membership.membership_id,
            farm_id=validated.membership.farm_id,
            plant_id=plant_id,
            status=grant_status,
            plant_approve_actions=True,
        )
    snapshot = PlantAccessSnapshot(
        plant=PlantSnapshot(
            plant_id=plant_id,
            farm_id=validated.membership.farm_id,
            status=plant_status,
        ),
        grant=grant,
    )
    actor = ActorContextResolver(
        session_validator=StaticSessionValidator(validated),
        snapshot_provider=lambda **_kwargs: snapshot,
    ).resolve(
        request_id="req-context-builder",
        raw_session_token="synthetic-context-token",
        transport=AuthTransport.COOKIE,
    )
    return actor, snapshot


def test_context_builder_emits_canonical_authorization_scope_without_auth_data():
    actor, snapshot = _actor("consultant")
    safe = PlantContextCandidate(
        plant_id=snapshot.plant.plant_id,
        source_ref="observation:1",
        source_kind=ContextSourceKind.DOMAIN_RECORD,
        consumable_by_agents=True,
        payload={"observation": "leaf edge changed", "confidence": 0.6},
    )

    result = build_authorized_plant_context(
        actor,
        plant_id=snapshot.plant.plant_id,
        operation_kind=OperationKind.NORMAL_READ,
        candidates=[safe],
    )

    assert result is not None
    assert result.records[0].source_ref == "observation:1"
    assert result.records[0].payload == {
        "observation": "leaf edge changed",
        "confidence": 0.6,
    }
    scope = result.authorization_scope
    assert {field.name for field in fields(AuthorizationScope)} >= {
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
    assert scope.plant_id == snapshot.plant.plant_id
    assert scope.plant_status is PlantStatus.ACTIVE
    assert scope.can_read is True
    assert scope.can_comment is True
    assert scope.can_operate is False
    assert scope.can_create_domain_tasks is False
    assert scope.can_manage_access is False
    assert scope.can_approve_actions is False
    assert scope.source is PermissionSource.PLANT_ACCESS_GRANT
    assert scope.grant_id == snapshot.grant.grant_id
    serialized = repr(result).lower()
    assert all(
        forbidden not in serialized
        for forbidden in (
            "session_id",
            "token_hash",
            "password_hash",
            "auth_header",
            "cookie",
        )
    )


def test_context_builder_filters_non_consumable_and_forbidden_content():
    actor, snapshot = _actor("boss", include_grant=False)
    plant_id = snapshot.plant.plant_id
    candidates = [
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="safe:1",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"measurement": {"ph": 6.1}, "tags": ["manual"]},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="ui:1",
            source_kind="ui_feed",
            consumable_by_agents=True,
            payload={"display": "human only"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="chat:1",
            source_kind="raw_chat",
            consumable_by_agents=True,
            payload={"text": "raw discussion"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="notice:1",
            source_kind="admin_notice",
            consumable_by_agents=True,
            payload={"text": "admin-only"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="proposal:1",
            source_kind="unapproved_proposal",
            consumable_by_agents=True,
            payload={"text": "not approved"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="reasoning:1",
            source_kind="raw_reasoning",
            consumable_by_agents=True,
            payload={"text": "hidden"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="provider:1",
            source_kind="raw_provider_output",
            consumable_by_agents=True,
            payload={"text": "unadapted provider output"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="secret:1",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"nested": {"session_token": "must-not-pass"}},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="not-consumable:1",
            source_kind="domain_record",
            consumable_by_agents=False,
            payload={"value": "human only"},
        ),
        PlantContextCandidate(
            plant_id=uuid.uuid4(),
            source_ref="other-plant:1",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"value": "wrong scope"},
        ),
    ]

    result = build_authorized_plant_context(
        actor,
        plant_id=plant_id,
        operation_kind=OperationKind.NORMAL_READ,
        candidates=candidates,
    )

    assert result is not None
    assert len(result.records) == 1
    assert result.records[0].source_ref == "safe:1"
    assert result.records[0].payload == {
        "measurement": {"ph": 6.1},
        "tags": ["manual"],
    }


def test_context_builder_rejects_auth_material_in_source_ref_and_string_values():
    actor, snapshot = _actor("boss", include_grant=False)
    plant_id = snapshot.plant.plant_id
    raw_session_token = generate_session_token()
    token_hash = "a" * 64
    candidates = [
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref=f"observation:{raw_session_token}",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"note": "otherwise safe"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="observation:auth-header",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"note": "Authorization: Bearer synthetic-marker-value"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="measurement:token-hash",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"nested": ["safe", token_hash]},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="observation:jwt",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"note": "eyJhbGciOiJIUzI1NiJ9.payload.signature"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="session:known-session",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={"note": "safe"},
        ),
        PlantContextCandidate(
            plant_id=plant_id,
            source_ref="observation:safe-value",
            source_kind="domain_record",
            consumable_by_agents=True,
            payload={
                "note": "Authorization policy reviewed; no credential included."
            },
        ),
    ]

    result = build_authorized_plant_context(
        actor,
        plant_id=plant_id,
        operation_kind=OperationKind.NORMAL_READ,
        candidates=candidates,
    )

    assert result is not None
    assert len(result.records) == 1
    assert result.records[0].source_ref == "observation:safe-value"
    serialized = repr(result)
    assert raw_session_token not in serialized
    assert token_hash not in serialized
    assert "synthetic-marker-value" not in serialized


@pytest.mark.parametrize(
    ("grant_status", "include_grant", "plant_status"),
    [
        (GrantStatus.ACTIVE, False, PlantStatus.ACTIVE),
        (GrantStatus.REVOKED, True, PlantStatus.ACTIVE),
        (GrantStatus.ACTIVE, True, PlantStatus.ARCHIVED),
    ],
)
def test_denied_context_is_filtered_before_candidate_iteration(
    grant_status: GrantStatus,
    include_grant: bool,
    plant_status: PlantStatus,
):
    actor, snapshot = _actor(
        "engineer",
        grant_status=grant_status,
        include_grant=include_grant,
        plant_status=plant_status,
    )

    result = build_authorized_plant_context(
        actor,
        plant_id=snapshot.plant.plant_id,
        operation_kind=OperationKind.NORMAL_READ,
        candidates=CandidateProbe(),
    )

    assert result is None


def test_unknown_plant_and_invalid_operation_fail_before_candidate_iteration():
    actor, _snapshot = _actor("engineer")

    assert (
        build_authorized_plant_context(
            actor,
            plant_id=uuid.uuid4(),
            operation_kind=OperationKind.NORMAL_READ,
            candidates=CandidateProbe(),
        )
        is None
    )
    assert (
        build_authorized_plant_context(
            actor,
            plant_id=uuid.uuid4(),
            operation_kind="delete",
            candidates=CandidateProbe(),
        )
        is None
    )
