from __future__ import annotations

import base64
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import uuid

import pytest
from sqlalchemy import select

from backend.app import AppSettings
from backend.app.access_admin.actor_context import ActorContext
from backend.app.access_admin.models import AdminAuditRecord, Plant
from backend.app.photo_intake import PhotoIntakeService, PhotoUploadInput
from backend.app.plant_history import (
    PlantHistoryError,
    PlantHistoryErrorCode,
    PlantHistoryService,
)
from backend.app.plant_operations import (
    DailyCheckIn,
    ManualMeasurement,
    ManualMeasurementInput,
    PlantOperationError,
    PlantOperationErrorCode,
    PlantOperationsService,
)
from backend.app.timeline import TimelineEvent, append_timeline_event
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    disable_membership,
    grant_access,
    revoke_access,
    seed_farm,
)


JPEG_BYTES = b"\xff\xd8\xff\xe0ft006-history-photo"


def test_ft006_bhv001_active_history_is_projected_from_authority_rows(
    ft006_database,
    ft006_photo_store,
    event_ref_factory,
):
    farm = seed_farm(ft006_database)
    boss, _boss_membership = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    plant = create_active_plant(ft006_database, boss, plant_key="history_active")
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    check_in, measurement, photo_id = _create_source_rows(
        ft006_database,
        ft006_photo_store,
        event_ref_factory,
        engineer,
        plant.plant_id,
    )

    with ft006_database.session() as session:
        service = PlantHistoryService(session)
        card = service.get_card(engineer, plant_id=plant.plant_id)
        history = service.list_history(engineer, plant_id=plant.plant_id)

    assert card.plant_id == plant.plant_id
    assert card.farm_id == farm.farm_id
    assert card.status == "active"
    assert card.retained_history_mode == "active_history"
    assert card.permissions["can_read"] is True
    assert card.permissions["can_operate"] is True
    assert card.latest_check_in_ref == {
        "source_type": "daily_checkin",
        "source_id": str(check_in.check_in_id),
    }
    assert card.latest_ph_ref == {
        "source_type": "manual_measurement",
        "source_id": str(measurement.measurement_id),
    }
    assert card.latest_ec_ref == {
        "source_type": "manual_measurement",
        "source_id": str(measurement.measurement_id),
    }
    assert card.latest_ph == Decimal("6.50")
    assert card.latest_ec_ms_cm == Decimal("1.250")
    assert card.ph_fresh_for_analysis is True
    assert card.ec_fresh_for_analysis is True
    assert card.photo_count == 1
    assert card.history_entry_count >= 4

    source_types = {entry.source_type for entry in history.items}
    assert {
        "plant_admin_audit",
        "daily_checkin",
        "manual_measurement",
        "photo_catalog_item",
    }.issubset(source_types)
    assert all(entry.authority_source == "postgresql_read_model" for entry in history.items)
    assert {entry.source_id for entry in history.items}.issuperset(
        {check_in.check_in_id, measurement.measurement_id, photo_id}
    )

    photo_entry = _entry(history.items, "photo_catalog_item", photo_id)
    assert photo_entry.artifact_refs["original_file_ref"].startswith("plants/")
    assert photo_entry.event_refs["photo_accepted"]["event_type"] == "photo_accepted"
    measurement_entry = _entry(
        history.items,
        "manual_measurement",
        measurement.measurement_id,
    )
    assert measurement_entry.event_refs["manual_measurement_recorded"][
        "event_type"
    ] == "manual_measurement_recorded"
    assert measurement_entry.summary["ph"] == "6.50"
    assert measurement_entry.summary["ec_ms_cm"] == "1.250"

    payload = _json_payload(card, history)
    assert "session_id" not in payload
    assert "synthetic-test-token" not in payload
    assert str(ft006_photo_store.path_for_test("plants")) not in payload


def test_ft006_bhv002_archived_retained_history_has_no_operational_authority(
    ft006_database,
    ft006_photo_store,
    event_ref_factory,
):
    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    consultant, consultant_membership = create_actor(ft006_database, farm, "consultant")
    plant = create_active_plant(ft006_database, boss, plant_key="history_archive")
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    _create_source_rows(
        ft006_database,
        ft006_photo_store,
        event_ref_factory,
        engineer,
        plant.plant_id,
    )
    archive_plant(ft006_database, boss, plant_id=plant.plant_id)

    for actor in (boss, engineer, consultant):
        with ft006_database.session() as session:
            service = PlantHistoryService(session)
            card = service.get_card(actor, plant_id=plant.plant_id)
            history = service.list_history(actor, plant_id=plant.plant_id)
        assert card.retained_history_mode == "archived_retained_history"
        assert card.permissions["can_read"] is True
        assert card.permissions["can_comment"] is True
        assert card.permissions["can_operate"] is False
        assert card.permissions["can_create_domain_tasks"] is False
        assert card.permissions["can_approve_actions"] is False
        assert history.items

    with ft006_database.session() as session:
        with pytest.raises(PlantOperationError) as denied:
            PlantOperationsService(
                session,
                timeline_append=event_ref_factory,
            ).create_check_in(
                boss,
                plant_id=plant.plant_id,
                observation_state="observed",
                observation_text="Archived write attempt",
            )
    assert denied.value.code is PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN


def test_active_and_retained_history_denials_fail_closed(
    ft006_database,
):
    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    disabled_engineer, disabled_membership = create_actor(
        ft006_database,
        farm,
        "engineer",
    )

    ungranted_plant = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_no_grant",
    )

    revoked_plant = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_revoked",
    )
    grant_access(
        ft006_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft006_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    disabled_plant = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_disabled",
    )
    grant_access(
        ft006_database,
        boss,
        plant_id=disabled_plant.plant_id,
        membership_id=disabled_membership.membership_id,
    )
    disable_membership(ft006_database, disabled_membership.membership_id)

    archived_ungranted = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_archived_denied",
    )
    archive_plant(ft006_database, boss, plant_id=archived_ungranted.plant_id)

    wrong_farm_actor = _actor_with_farm_id(engineer, uuid.uuid4())

    denied_cases = [
        (engineer, ungranted_plant.plant_id),
        (engineer, revoked_plant.plant_id),
        (disabled_engineer, disabled_plant.plant_id),
        (engineer, archived_ungranted.plant_id),
        (wrong_farm_actor, ungranted_plant.plant_id),
        (engineer, uuid.uuid4()),
    ]
    for actor, plant_id in denied_cases:
        _assert_history_denied(ft006_database, actor, plant_id)


def test_ft006_bhv003_timeline_replay_cannot_create_or_repair_history(
    ft006_database,
    tmp_path,
    event_ref_factory,
):
    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    plant = create_active_plant(ft006_database, boss, plant_key="history_timeline")
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    with ft006_database.session() as session:
        measurement = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(ph="6.10"),
        ).measurement

    with ft006_database.session() as session, session.begin():
        stored_measurement = session.get(ManualMeasurement, measurement.measurement_id)
        stored_measurement.event_refs = {}

    orphan_source_id = uuid.uuid4()
    append_timeline_event(
        TimelineEvent(
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            actor_ref={"account_id": str(engineer.account_id)},
            event_type="manual_measurement_recorded",
            source_type="manual_measurement",
            source_id=orphan_source_id,
            source_refs={"plant_id": str(plant.plant_id)},
            payload_summary={"ph": "9.99"},
        ),
        settings=AppSettings(local_timeline_root=tmp_path / "timeline"),
    )

    with ft006_database.session() as session:
        service = PlantHistoryService(session)
        card = service.get_card(engineer, plant_id=plant.plant_id)
        history = service.list_history(engineer, plant_id=plant.plant_id)

    assert card.latest_ph == Decimal("6.10")
    assert orphan_source_id not in {entry.source_id for entry in history.items}
    entry = _entry(history.items, "manual_measurement", measurement.measurement_id)
    assert entry.event_refs == {}
    assert entry.summary["ph"] == "6.10"


def test_pagination_source_filter_validation_and_redaction(
    ft006_database,
    ft006_photo_store,
    event_ref_factory,
):
    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    plant = create_active_plant(ft006_database, boss, plant_key="history_pages")
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    check_in, _measurement, _photo_id = _create_source_rows(
        ft006_database,
        ft006_photo_store,
        event_ref_factory,
        engineer,
        plant.plant_id,
    )
    with ft006_database.session() as session:
        PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(
                ec_ms_cm="1.800",
                measured_at=datetime.now(timezone.utc) + timedelta(minutes=1),
            ),
        )

    with ft006_database.session() as session, session.begin():
        stored_check_in = session.get(DailyCheckIn, check_in.check_in_id)
        stored_check_in.source_refs = {
            **stored_check_in.source_refs,
            "session_id": "leaky-session",
            "api_token": "leaky-token",
            "absolute_path": "/home/serg/private/history.sql",
            "safe_note": "operator attached path /home/serg/private/history.sql",
            "windows_note": r"operator attached C:\Users\serg\private\history.sql",
        }
        stored_audit = session.scalar(
            select(AdminAuditRecord)
            .where(AdminAuditRecord.plant_id == plant.plant_id)
            .limit(1)
        )
        assert stored_audit is not None
        stored_audit.after_summary = {
            **stored_audit.after_summary,
            "operator_note": r"reviewed C:\Users\serg\private\audit.json",
        }

    with ft006_database.session() as session:
        service = PlantHistoryService(session)
        first_page = service.list_history(engineer, plant_id=plant.plant_id, limit=2)
        second_page = service.list_history(
            engineer,
            plant_id=plant.plant_id,
            cursor=first_page.next_cursor,
            limit=100,
        )
        measurements = service.list_history(
            engineer,
            plant_id=plant.plant_id,
            source_type="manual_measurement",
        )

    assert len(first_page.items) == 2
    assert first_page.next_cursor is not None
    assert {item.history_entry_id for item in first_page.items}.isdisjoint(
        {item.history_entry_id for item in second_page.items}
    )
    assert measurements.items
    assert {entry.source_type for entry in measurements.items} == {
        "manual_measurement"
    }

    payload = _json_payload(first_page, second_page, measurements)
    assert "safe_note" in payload
    assert "leaky-session" not in payload
    assert "leaky-token" not in payload
    assert "/home/serg" not in payload
    assert r"C:\\Users\\serg" not in payload

    with ft006_database.session() as session:
        service = PlantHistoryService(session)
        invalid_cases = [
            ("limit", {"limit": 0}, PlantHistoryErrorCode.HISTORY_LIMIT_INVALID),
            (
                "source_type",
                {"source_type": "agent_output"},
                PlantHistoryErrorCode.HISTORY_SOURCE_TYPE_INVALID,
            ),
            (
                "cursor",
                {"cursor": "not-a-valid-cursor"},
                PlantHistoryErrorCode.HISTORY_CURSOR_INVALID,
            ),
        ]
        for _name, kwargs, code in invalid_cases:
            with pytest.raises(PlantHistoryError) as error:
                service.list_history(engineer, plant_id=plant.plant_id, **kwargs)
            assert error.value.code is code


def test_postgresql_complete_response_redacts_absolute_paths_and_unsafe_keys(
    ft006_database,
    ft006_photo_store,
    event_ref_factory,
):
    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    plant = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_response_safe",
    )
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    check_in, _measurement, photo_id = _create_source_rows(
        ft006_database,
        ft006_photo_store,
        event_ref_factory,
        engineer,
        plant.plant_id,
    )
    safe_relative_ref = f"plants/{plant.plant_id}/photos/{photo_id}/original.jpg"
    complete_url = (
        "https://example.test/history:detail/section"
        "?next=/private/history&ref=source:/nested#view:/fragment"
    )
    ambiguous_url = (
        "https://example.test/evidence,source:/private/history/value.txt"
    )
    obvious_path_values = {
        "posix_note": "Inspection source /private/history/value.txt",
        "drive_note": r"Inspection source D:\private\history\value.txt",
        "unc_note": r"Inspection source \\history-host\private\value.txt",
        "file_uri_note": "Inspection source file:///private/history/value.txt",
    }
    unsafe_keys = {
        "/private/history/key",
        r"C:\private\history\key",
        r"\\history-host\private\key",
        "file:///private/history/key",
    }
    secret_bearing_keys = (
        "https://history-user:synthetic-userinfo@example.test/history",
        "trace Authorization: Bearer synthetic-bearer-material",
        "trace Basic synthetic-basic-material",
    )
    with ft006_database.session() as session, session.begin():
        stored_check_in = session.get(DailyCheckIn, check_in.check_in_id)
        assert stored_check_in is not None
        stored_check_in.source_refs = {
            **stored_check_in.source_refs,
            "safe_relative_ref": safe_relative_ref,
            "complete_url": complete_url,
            "ambiguous_url": ambiguous_url,
            **{key: "must be omitted" for key in secret_bearing_keys},
            complete_url: "preserved direct URL key",
            "nested": {
                **obvious_path_values,
                **{key: "must be omitted" for key in unsafe_keys},
                **{key: "must be omitted" for key in secret_bearing_keys},
                ambiguous_url: "preserved nested URL key",
                **{
                    f"sample_text_{index}": value
                    for index, value in enumerate(secret_bearing_keys)
                },
                "safe_url_value": complete_url,
            },
        }

    with ft006_database.session() as session:
        service = PlantHistoryService(session)
        stored_plant = session.get(Plant, plant.plant_id)
        assert stored_plant is not None
        for unsafe_display_name in (
            "/private/history/card.txt",
            "Inspection source /private/history/card.txt",
            r"D:\private\history\card.txt",
            r"\\history-host\private\card.txt",
            "file:///private/history/card.txt",
        ):
            stored_plant.display_name = unsafe_display_name
            session.flush()
            unsafe_card = service.get_card(engineer, plant_id=plant.plant_id)
            assert unsafe_card.display_name == "***"
        for safe_display_name in (complete_url, ambiguous_url):
            stored_plant.display_name = safe_display_name
            session.flush()
            assert (
                service.get_card(engineer, plant_id=plant.plant_id).display_name
                == safe_display_name
            )
        card = service.get_card(engineer, plant_id=plant.plant_id)
        history = service.list_history(engineer, plant_id=plant.plant_id)

    assert card.display_name == ambiguous_url
    check_in_entry = _entry(history.items, "daily_checkin", check_in.check_in_id)
    projected_refs = check_in_entry.source_refs["source_refs"]
    assert projected_refs["safe_relative_ref"] == safe_relative_ref
    assert projected_refs["complete_url"] == complete_url
    assert projected_refs["ambiguous_url"] == ambiguous_url
    assert projected_refs[complete_url] == "preserved direct URL key"
    assert all(key not in projected_refs for key in secret_bearing_keys)
    nested = projected_refs["nested"]
    assert {nested[name] for name in obvious_path_values} == {"***"}
    assert nested[ambiguous_url] == "preserved nested URL key"
    assert nested["safe_url_value"] == complete_url
    assert all(key not in nested for key in secret_bearing_keys)
    assert all(
        nested[f"sample_text_{index}"] != value
        and "***" in nested[f"sample_text_{index}"]
        for index, value in enumerate(secret_bearing_keys)
    )
    assert unsafe_keys.isdisjoint(nested)

    response_graph = [asdict(card), asdict(history)]
    keys, strings = _mapping_keys_and_string_values(response_graph)
    assert unsafe_keys.isdisjoint(keys)
    assert safe_relative_ref in strings
    assert complete_url in strings
    assert ambiguous_url in strings
    assert complete_url in keys
    assert ambiguous_url in keys
    assert all(key not in keys for key in secret_bearing_keys)
    assert all(value not in strings for value in secret_bearing_keys)


def test_postgresql_cursor_requires_exact_canonical_service_encoding(
    ft006_database,
    ft006_photo_store,
    event_ref_factory,
):
    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    plant = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_cursor_strict",
    )
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    _create_source_rows(
        ft006_database,
        ft006_photo_store,
        event_ref_factory,
        engineer,
        plant.plant_id,
    )

    with ft006_database.session() as session:
        service = PlantHistoryService(session)
        first_page = service.list_history(engineer, plant_id=plant.plant_id, limit=1)
        assert first_page.next_cursor is not None
        canonical_cursor = first_page.next_cursor
        continued = service.list_history(
            engineer,
            plant_id=plant.plant_id,
            cursor=canonical_cursor,
        )
        assert continued.items

        payload = _decoded_cursor_payload(canonical_cursor)
        malformed = [
            f"!{canonical_cursor}",
            f"{canonical_cursor[:4]} {canonical_cursor[4:]}",
            f"{canonical_cursor}=",
            _encoded_cursor_payload({**payload, "v": 2}),
            _encoded_cursor_payload({**payload, "extra": True}),
            _encoded_cursor_payload(
                {key: value for key, value in payload.items() if key != "source_id"}
            ),
            _encoded_cursor_payload({**payload, "occurred_at": "not-a-timestamp"}),
            _encoded_cursor_payload({**payload, "source_type": "agent_output"}),
            _encoded_cursor_payload({**payload, "source_id": "not-a-uuid"}),
            _encoded_cursor_payload(payload, canonical_json=False),
        ]
        for cursor in malformed:
            with pytest.raises(PlantHistoryError) as error:
                service.list_history(
                    engineer,
                    plant_id=plant.plant_id,
                    cursor=cursor,
                )
            assert error.value.code is PlantHistoryErrorCode.HISTORY_CURSOR_INVALID


def test_configured_corpus_absent_from_actual_history_serialization(
    ft006_database,
    ft006_photo_store,
    event_ref_factory,
    monkeypatch,
):
    corpus_db_password = "corpus-ph-db-pw-7t3m"
    corpus_env_secret = "corpus-ph-env-secret-4q9w"
    corpus_bearer = "corpus-ph-bearer-6r2k"
    corpus_api_key = "corpus-ph-api-key-1n8v"
    corpus_url_password = "corpus-ph-url-pw-3h5d"
    corpus = [
        corpus_db_password,
        corpus_env_secret,
        corpus_bearer,
        corpus_api_key,
        corpus_url_password,
    ]
    monkeypatch.setenv("AGRO_PH_CORPUS_API_KEY", corpus_api_key)
    monkeypatch.setenv("AGRO_PH_CORPUS_SECRET", corpus_env_secret)
    monkeypatch.setenv("AGRO_PH_CORPUS_DB_URL", corpus_db_password)

    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    plant = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_corpus_probe",
    )
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    check_in, _measurement, photo_id = _create_source_rows(
        ft006_database,
        ft006_photo_store,
        event_ref_factory,
        engineer,
        plant.plant_id,
    )
    with ft006_database.session() as session, session.begin():
        stored_check_in = session.get(DailyCheckIn, check_in.check_in_id)
        assert stored_check_in is not None
        stored_check_in.source_refs = {
            **stored_check_in.source_refs,
            "provenance_note": (
                f"note password={corpus_db_password} env={corpus_env_secret} "
                f"key={corpus_api_key} Authorization: Bearer {corpus_bearer} "
                f"postgresql+psycopg://postgres:{corpus_url_password}@dbhost/agro"
            ),
            "api_token": "corpus-ph-session-token-2v8a",
            "authorization": "Bearer corpus-ph-session-token-2v8a",
            "db_url": f"postgresql+psycopg://user:{corpus_url_password}@dbhost/agro",
            "safe_relative_ref": f"plants/{plant.plant_id}/photos/{photo_id}/original.jpg",
            "nested": {
                "inner_note": f"inner={corpus_env_secret} key={corpus_api_key}",
            },
        }
        stored_plant = session.get(Plant, plant.plant_id)
        assert stored_plant is not None
        stored_plant.display_name = f"Plant {corpus_env_secret}"

    with ft006_database.session() as session:
        service = PlantHistoryService(session)
        card = service.get_card(engineer, plant_id=plant.plant_id)
        first_page = service.list_history(
            engineer,
            plant_id=plant.plant_id,
            limit=2,
        )
        second_page = service.list_history(
            engineer,
            plant_id=plant.plant_id,
            cursor=first_page.next_cursor,
            limit=100,
        )

    payload = _json_payload(card, first_page, second_page)
    assert all(raw not in payload for raw in corpus)
    assert "***" in payload
    assert "postgresql+psycopg://postgres:***@dbhost/agro" in payload
    assert "Plant ***" in payload
    assert "corpus-ph-session-token-2v8a" not in payload

    graph = [asdict(card), asdict(first_page), asdict(second_page)]
    keys, strings = _mapping_keys_and_string_values(graph)
    assert {"api_token", "authorization", "db_url"}.isdisjoint(keys)
    safe_relative_ref = (
        f"plants/{plant.plant_id}/photos/{photo_id}/original.jpg"
    )
    assert safe_relative_ref in strings
    assert first_page.next_cursor is not None
    assert len(first_page.items) == 2
    assert {item.history_entry_id for item in first_page.items}.isdisjoint(
        {item.history_entry_id for item in second_page.items}
    )

    with ft006_database.session() as session:
        stored_check_in = session.get(DailyCheckIn, check_in.check_in_id)
        stored_plant = session.get(Plant, plant.plant_id)
        assert stored_check_in.source_refs["api_token"] == (
            "corpus-ph-session-token-2v8a"
        )
        assert corpus_env_secret in stored_plant.display_name


class _Unrenderable:
    def __str__(self) -> str:
        raise RuntimeError("cannot render this value")


def test_unrenderable_history_value_fails_closed_registered_error(
    ft006_database,
    event_ref_factory,
):
    farm = seed_farm(ft006_database)
    boss, _ = create_actor(ft006_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft006_database, farm, "engineer")
    plant = create_active_plant(
        ft006_database,
        boss,
        plant_key="history_fail_closed",
    )
    grant_access(
        ft006_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    with ft006_database.session() as session:
        result = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_check_in(
            engineer,
            plant_id=plant.plant_id,
            observation_state="observed",
            observation_text="Fail-closed probe",
            measurement=ManualMeasurementInput(ph="6.50"),
        )
        check_in_id = result.check_in.check_in_id

    with ft006_database.session() as session:
        stored_check_in = session.get(DailyCheckIn, check_in_id)
        assert stored_check_in is not None
        stored_check_in.event_refs = {"bad": _Unrenderable()}
        with pytest.raises(PlantHistoryError) as error:
            PlantHistoryService(session).list_history(
                engineer,
                plant_id=plant.plant_id,
            )
        assert error.value.code is PlantHistoryErrorCode.HISTORY_PERSISTENCE_FAILED
        assert "HISTORY_PERSISTENCE_FAILED" in str(error.value)
        assert "cannot render" not in str(error.value)


def _create_source_rows(
    database,
    photo_store,
    event_ref_factory,
    actor,
    plant_id,
):
    with database.session() as session:
        check_in_result = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_check_in(
            actor,
            plant_id=plant_id,
            observation_state="observed",
            observation_text="History source observation",
            measurement=ManualMeasurementInput(ph="6.50", ec_ms_cm="1.250"),
        )
    event_ref_factory.events.clear()
    with database.session() as session:
        photo = PhotoIntakeService(
            session,
            artifact_store=photo_store,
            timeline_append=event_ref_factory,
        ).accept_photo(
            actor,
            plant_id=plant_id,
            upload=PhotoUploadInput(
                content=JPEG_BYTES,
                content_type="image/jpeg",
                photo_type="leaf_closeup",
                check_in_id=check_in_result.check_in.check_in_id,
            ),
        ).item
    return (
        check_in_result.check_in,
        check_in_result.measurements[0],
        photo.photo_id,
    )


def _entry(items, source_type: str, source_id: uuid.UUID):
    return next(
        item
        for item in items
        if item.source_type == source_type and item.source_id == source_id
    )


def _json_payload(*values) -> str:
    return json.dumps([asdict(value) for value in values], default=str, sort_keys=True)


def _decoded_cursor_payload(cursor: str) -> dict[str, object]:
    padded = cursor + ("=" * (-len(cursor) % 4))
    decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    payload = json.loads(decoded.decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def _encoded_cursor_payload(
    payload: dict[str, object],
    *,
    canonical_json: bool = True,
) -> str:
    separators = (",", ":") if canonical_json else (", ", ": ")
    raw = json.dumps(payload, separators=separators, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _mapping_keys_and_string_values(value: object) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    strings: list[str] = []

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                keys.add(str(key))
                visit(nested)
        elif isinstance(item, list | tuple):
            for nested in item:
                visit(nested)
        elif isinstance(item, str):
            strings.append(item)

    visit(value)
    return keys, strings


def _assert_history_denied(database, actor, plant_id) -> None:
    with database.session() as session:
        with pytest.raises(PlantHistoryError) as error:
            PlantHistoryService(session).get_card(actor, plant_id=plant_id)
    assert error.value.code is PlantHistoryErrorCode.AUTH_PLANT_FORBIDDEN


def _actor_with_farm_id(actor: ActorContext, farm_id: uuid.UUID) -> ActorContext:
    clone = object.__new__(ActorContext)
    for name in (
        "request_id",
        "session_id",
        "account_id",
        "farm_id",
        "membership_id",
        "role_preset",
        "membership_status",
        "auth_provenance",
        "plant_permission_resolver",
    ):
        object.__setattr__(
            clone,
            name,
            farm_id if name == "farm_id" else getattr(actor, name),
        )
    return clone
