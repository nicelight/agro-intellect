from __future__ import annotations

import json

import pytest

from backend.app.agent_runtime import (
    AgnoModelExecutor,
    AgnoModelExecutorFactory,
    CANONICAL_ROSTER_V1,
    ProviderBinding,
    ProviderBindingResolver,
    ProviderConfigurationError,
    ProductionProviderComposition,
    canonical_roster,
    parse_provider_bindings,
)
from backend.app.config import AppSettings


EXPECTED_IDS = (
    "companion",
    "vision_observation",
    "plant_state",
    "hydroponics_advisor",
    "task_follow_up",
    "safety_gate",
    "dataset_governance",
    "training_data_curator",
)
EXPECTED_NAMES = (
    "Companion Agent",
    "Vision Observation Agent",
    "Plant State Agent",
    "Hydroponics Advisor Agent",
    "Task & Follow-up Agent",
    "Safety Gate Agent",
    "Dataset Governance Agent",
    "Training Data Curator Agent",
)
EXPECTED_FEATURES = (
    "FT-013",
    "FT-009",
    "FT-009",
    "FT-010",
    "FT-012",
    "FT-011",
    "FT-014",
    "FT-014",
)


def test_canonical_roster_v1_is_exact_ordered_and_immutable():
    assert isinstance(CANONICAL_ROSTER_V1, tuple)
    assert canonical_roster() is CANONICAL_ROSTER_V1
    assert tuple(item.agent_id for item in CANONICAL_ROSTER_V1) == EXPECTED_IDS
    assert tuple(item.display_name for item in CANONICAL_ROSTER_V1) == EXPECTED_NAMES
    assert tuple(item.owning_feature for item in CANONICAL_ROSTER_V1) == EXPECTED_FEATURES
    assert all(item.output_schema_version == 1 for item in CANONICAL_ROSTER_V1)
    assert all(item.competence_summary for item in CANONICAL_ROSTER_V1)
    assert all(item.introduction_text for item in CANONICAL_ROSTER_V1)
    with pytest.raises(ValueError):
        canonical_roster(2)


def test_settings_keep_binding_non_secret_and_egress_explicit():
    settings = AppSettings.from_env(
        {
            "AGENT_MODEL_BINDINGS_JSON": json.dumps(
                {"companion": {"provider_profile": "gemini", "model_id": "gemini-x"}}
            ),
            "AGENT_EXTERNAL_EGRESS_ENABLED": "true",
        }
    )
    assert settings.agent_external_egress_enabled is True
    assert settings.redacted_for_log()["agent_model_bindings"] == "configured"
    assert "gemini-x" not in str(settings.redacted_for_log())


def test_binding_parser_accepts_partial_map_and_resolves_no_default():
    resolver = ProviderBindingResolver.from_json(
        '{"companion":{"provider_profile":"deepseek","model_id":"deepseek-chat"}}'
    )
    assert resolver.resolve("companion") == ProviderBinding("deepseek", "deepseek-chat")
    assert resolver.resolve("plant_state") is None


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        "[]",
        '{"unknown":{"provider_profile":"deepseek","model_id":"x"}}',
        '{"companion":{"provider_profile":"unknown","model_id":"x"}}',
        '{"companion":{"provider_profile":"gemini","model_id":""}}',
        '{"companion":{"provider_profile":"gemini","model_id":"bad id"}}',
        '{"companion":{"provider_profile":"gemini","model_id":"x?key=secret"}}',
        '{"companion":{"provider_profile":"gemini","model_id":"x","api_key":"secret"}}',
        '{"companion":{"provider_profile":"gemini","model_id":"x"},"companion":{"provider_profile":"deepseek","model_id":"y"}}',
    ],
)
def test_binding_parser_rejects_entire_malformed_or_unsafe_map(value):
    with pytest.raises(ProviderConfigurationError):
        parse_provider_bindings(value)


def test_native_factories_receive_exact_model_and_matching_credential_only():
    calls = []

    def deepseek(**kwargs):
        calls.append(("deepseek", kwargs))
        return object()

    def gemini(**kwargs):
        calls.append(("gemini", kwargs))
        return object()

    factory = AgnoModelExecutorFactory(
        egress_enabled=True,
        environ={"DEEPSEEK_API_KEY": "test-secret", "GOOGLE_API_KEY": "other-secret"},
        constructors={"deepseek": deepseek, "gemini": gemini},
    )
    executor = factory.create(ProviderBinding("deepseek", "deployment-model"))
    assert isinstance(executor, AgnoModelExecutor)
    assert executor.model_ref == "deepseek:deployment-model"
    assert calls == [
        ("deepseek", {"id": "deployment-model", "api_key": "test-secret"})
    ]


@pytest.mark.parametrize(
    ("binding", "egress", "environment"),
    [
        (ProviderBinding("deepseek", "x"), False, {"DEEPSEEK_API_KEY": "secret"}),
        (ProviderBinding("deepseek", "x"), True, {}),
        (ProviderBinding("gemini", "x"), True, {"DEEPSEEK_API_KEY": "wrong"}),
        (ProviderBinding("chatgpt_oauth", "x"), True, {"OPENAI_API_KEY": "wrong"}),
    ],
)
def test_factory_fails_closed_without_egress_matching_key_or_oauth_broker(
    binding, egress, environment
):
    with pytest.raises(ProviderConfigurationError):
        AgnoModelExecutorFactory(
            egress_enabled=egress,
            environ=environment,
            constructors={"deepseek": lambda **_kwargs: object(), "gemini": lambda **_kwargs: object()},
        ).create(binding)


def test_constructor_failure_does_not_try_another_provider():
    calls = []

    def fail(**_kwargs):
        calls.append("deepseek")
        raise RuntimeError("provider unavailable")

    def fallback(**_kwargs):
        calls.append("gemini")
        return object()

    factory = AgnoModelExecutorFactory(
        egress_enabled=True,
        environ={"DEEPSEEK_API_KEY": "secret", "GOOGLE_API_KEY": "secret"},
        constructors={"deepseek": fail, "gemini": fallback},
    )
    with pytest.raises(ProviderConfigurationError):
        factory.create(ProviderBinding("deepseek", "x"))
    assert calls == ["deepseek"]


def test_production_composition_resolves_each_explicit_roster_binding_only():
    bindings = {
        agent_id: {"provider_profile": "gemini", "model_id": f"model-{index}"}
        for index, agent_id in enumerate(EXPECTED_IDS, start=1)
    }
    calls = []
    composition = ProductionProviderComposition(
        bindings_json=json.dumps(bindings),
        egress_enabled=True,
        environ={"GOOGLE_API_KEY": "secret"},
        constructors={"gemini": lambda **kwargs: calls.append(kwargs) or object()},
    )
    for agent_id in EXPECTED_IDS:
        composition.executor_for(agent_id)
    assert [call["id"] for call in calls] == [f"model-{index}" for index in range(1, 9)]
    with pytest.raises(ProviderConfigurationError):
        composition.executor_for("runtime_contract_smoke")


def test_unbound_agent_fails_before_constructor():
    calls = []
    composition = ProductionProviderComposition(
        bindings_json="{}",
        egress_enabled=True,
        environ={"GOOGLE_API_KEY": "secret"},
        constructors={"gemini": lambda **kwargs: calls.append(kwargs) or object()},
    )
    with pytest.raises(ProviderConfigurationError):
        composition.executor_for("companion")
    assert calls == []
