from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app


def test_generated_openapi_contains_exact_ft002_paths_and_statuses():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schema = create_app(database=database).openapi()
    finally:
        database.dispose()

    paths = schema["paths"]
    expected = {
        "/api/farm": {"get", "patch"},
        "/api/plants": {"get", "post"},
        "/api/plants/{plant_id}": {"get", "patch"},
        "/api/plants/{plant_id}/archive": {"post"},
        "/api/plants/{plant_id}/restore": {"post"},
        "/api/plants/{plant_id}/access": {"get"},
        "/api/plants/{plant_id}/access/{membership_id}": {"put"},
        "/api/plants/{plant_id}/access/{membership_id}/revoke": {"post"},
    }
    for path, methods in expected.items():
        assert path in paths
        assert methods <= paths[path].keys()

    assert set(paths["/api/plants"]["post"]["responses"]) >= {
        "201",
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }
    assert set(
        paths["/api/plants/{plant_id}/access/{membership_id}"]["put"]["responses"]
    ) >= {"200", "201", "401", "403", "404", "409", "422", "500"}


def test_generated_openapi_models_forbid_server_owned_request_fields():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schemas = create_app(database=database).openapi()["components"]["schemas"]
    finally:
        database.dispose()

    create = schemas["PlantCreateRequest"]
    assert create["additionalProperties"] is False
    assert set(create["properties"]) == {"plant_key", "display_name"}
    assert create["properties"]["plant_key"]["pattern"] == (
        "^[a-z0-9]+(?:_[a-z0-9]+)*$"
    )
    assert create["required"] == ["plant_key", "display_name"]
    assert schemas["PlantAccessRequest"]["additionalProperties"] is False

    plant = schemas["PlantSummary"]["properties"]
    assert plant["plant_id"]["format"] == "uuid"
    assert plant["created_at"]["format"] == "date-time"
    assert set(schemas["PlantPermissionSummary"]["properties"]["source"]["enum"]) == {
        "boss_role",
        "plant_access_grant",
    }
