from backend.app.main import create_app


def test_production_app_registers_complete_companion_router_exactly_once():
    schema = create_app().openapi()
    companion_paths = {
        "/api/plants/{plant_id}/companion/runs": {"post"},
        "/api/plants/{plant_id}/companion/issues": {"get"},
        "/api/plants/{plant_id}/companion/issues/{issue_id}": {"get"},
        "/api/plants/{plant_id}/companion/proposals/{proposal_id}/decision": {"post"},
        "/api/plants/{plant_id}/companion/issues/{issue_id}/close": {"post"},
    }
    for path, methods in companion_paths.items():
        assert path in schema["paths"]
        assert set(schema["paths"][path]) == methods

    assert "/api/plants/{plant_id}/feed" in schema["paths"]
    assert "/api/plants/{plant_id}/tasks" in schema["paths"]
    operation_ids = [
        operation["operationId"]
        for path in companion_paths
        for operation in schema["paths"][path].values()
    ]
    assert len(operation_ids) == len(set(operation_ids)) == 5

    run_operation = schema["paths"]["/api/plants/{plant_id}/companion/runs"]["post"]
    request_schema = schema["components"]["schemas"]["CompanionRunRequestV1"]
    response_schema = schema["components"]["schemas"]["CompanionRunResponseV1"]
    assert request_schema["required"] == [
        "schema_version",
        "request_id",
        "issue_id",
        "expected_issue_version",
    ]
    assert set(request_schema["properties"]) == set(request_schema["required"])
    assert set(response_schema["properties"]) == {
        "schema_version",
        "run_id",
        "route_status",
        "issue_ref",
        "attention_ref",
        "proposal_ref",
        "classification_ref",
        "model_ref",
        "reason_code",
    }
    assert {"200", "401", "403", "404", "409", "422", "500", "502", "503"} <= set(
        run_operation["responses"]
    )
