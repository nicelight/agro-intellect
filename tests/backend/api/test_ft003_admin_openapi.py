from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app


def test_generated_openapi_contains_ft003_admin_paths_and_statuses():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schema = create_app(database=database).openapi()
    finally:
        database.dispose()

    paths = schema["paths"]
    expected = {
        "/api/admin/accounts": {"get", "post"},
        "/api/admin/accounts/{account_id}/disable": {"post"},
        "/api/admin/memberships/{membership_id}/role": {"patch"},
        "/api/admin/plants": {"get"},
        "/api/admin/audit": {"get"},
    }
    for path, methods in expected.items():
        assert path in paths
        assert methods <= paths[path].keys()

    assert set(paths["/api/admin/accounts"]["post"]["responses"]) >= {
        "201",
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }
    assert set(paths["/api/admin/audit"]["get"]["responses"]) >= {
        "200",
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }


def test_generated_openapi_admin_models_are_safe_and_specific():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schemas = create_app(database=database).openapi()["components"]["schemas"]
    finally:
        database.dispose()

    create = schemas["AdminAccountCreateRequest"]
    assert create["additionalProperties"] is False
    assert set(create["properties"]) == {
        "login_name",
        "display_name",
        "password",
        "role_preset",
    }
    assert create["properties"]["password"]["format"] == "password"
    assert set(create["properties"]["role_preset"]["enum"]) == {
        "boss",
        "engineer",
        "consultant",
    }
    assert "password_hash" not in schemas["AdminAccountSummary"]["properties"]
    assert "token_hash" not in schemas["AdminAccountSummary"]["properties"]

    plant = schemas["AdminPlantProjection"]["properties"]
    assert plant["plant_id"]["format"] == "uuid"
    assert plant["created_at"]["format"] == "date-time"
    assert set(schemas["AdminPlantGrantCounts"]["properties"]) == {
        "active",
        "revoked",
        "approve_actions_enabled",
    }

    audit = schemas["AdminAuditSummary"]["properties"]
    assert audit["admin_audit_id"]["format"] == "uuid"
    assert audit["created_at"]["format"] == "date-time"
    assert "next_cursor" in schemas["AdminAuditListResponse"]["properties"]
