"""Tests that auth endpoints produce correct OpenAPI schema."""

from __future__ import annotations

from backend.app.api import create_app
from backend.app.config.deployment import DeploymentConfig, DeploymentMode


def _make_app():
    cfg = DeploymentConfig(mode=DeploymentMode.LOOPBACK, csrf_protection_enabled=False)
    return create_app(cfg)


class TestOpenApiAuth:
    def setup_method(self):
        self.app = _make_app()
        self.schema = self.app.openapi()

    def test_login_endpoint_in_paths(self):
        assert "/api/v1/auth/login" in self.schema["paths"]

    def test_login_post_method(self):
        path_item = self.schema["paths"]["/api/v1/auth/login"]
        assert "post" in path_item

    def test_login_request_body_exists(self):
        post_op = self.schema["paths"]["/api/v1/auth/login"]["post"]
        assert "requestBody" in post_op
        assert "application/json" in post_op["requestBody"]["content"]

    def test_login_response_schema(self):
        post_op = self.schema["paths"]["/api/v1/auth/login"]["post"]
        resp = post_op["responses"]["200"]
        ref = resp["content"]["application/json"]["schema"]["$ref"]
        assert "LoginResponse" in ref

    def test_logout_endpoint_in_paths(self):
        assert "/api/v1/auth/logout" in self.schema["paths"]

    def test_logout_response_schema(self):
        path_item = self.schema["paths"]["/api/v1/auth/logout"]
        post_op = path_item["post"]
        resp = post_op["responses"]["200"]
        ref = resp["content"]["application/json"]["schema"]["$ref"]
        assert "LogoutResponse" in ref

    def test_me_endpoint_in_paths(self):
        assert "/api/v1/auth/me" in self.schema["paths"]

    def test_me_response_schema(self):
        path_item = self.schema["paths"]["/api/v1/auth/me"]
        get_op = path_item["get"]
        resp = get_op["responses"]["200"]
        ref = resp["content"]["application/json"]["schema"]["$ref"]
        assert "MeResponse" in ref

    def test_all_schemas_registered(self):
        schemas = self.schema.get("components", {}).get("schemas", {})
        assert "LoginRequest" in schemas
        assert "LoginResponse" in schemas
        assert "LogoutResponse" in schemas
        assert "MeResponse" in schemas

    def test_schemas_do_not_expose_secrets(self):
        schemas = self.schema.get("components", {}).get("schemas", {})
        sensitive_names = [name for name in schemas if any(
            keyword in name.lower()
            for keyword in ["password", "secret", "credential", "api_key"]
        )]
        assert sensitive_names == [], f"Found potentially sensitive schema names: {sensitive_names}"

    def _resolve_type(self, prop: dict) -> str | list[str] | None:
        if "type" in prop:
            return prop["type"]
        if "anyOf" in prop:
            return [s.get("type") for s in prop["anyOf"] if s.get("type")]
        return None

    def test_me_response_typed_correctly(self):
        schemas = self.schema.get("components", {}).get("schemas", {})
        me_schema = schemas.get("MeResponse", {})
        props = me_schema.get("properties", {})
        assert self._resolve_type(props["state"]) == "string"
        resolved = self._resolve_type(props["account_id"])
        assert resolved is not None
        assert "string" in (resolved if isinstance(resolved, list) else [resolved])

    def test_login_request_has_login_identifier(self):
        schemas = self.schema.get("components", {}).get("schemas", {})
        login_req = schemas.get("LoginRequest", {})
        props = login_req.get("properties", {})
        assert "login_identifier" in props
        assert props["login_identifier"]["type"] == "string"
