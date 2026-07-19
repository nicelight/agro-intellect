from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from backend.app.agent_runtime import (
    AgnoModelExecutorFactory,
    ProductionProviderComposition,
    ProviderBinding,
    ProviderConfigurationError,
)
from backend.app.agent_runtime.providers import AgnoVisionModelExecutor
from backend.app.vision_observation import VisionMediaV1
from tests.backend.vision_observation.test_contracts import _request


def test_vision_factory_is_gemini_only_explicit_and_no_fallback():
    calls = []

    def gemini(**kwargs):
        calls.append(kwargs)
        return object()

    factory = AgnoModelExecutorFactory(
        egress_enabled=True,
        environ={"GOOGLE_API_KEY": "test-secret", "DEEPSEEK_API_KEY": "other"},
        constructors={"gemini": gemini, "deepseek": lambda **_kwargs: pytest.fail("fallback")},
    )
    executor = factory.create_vision(ProviderBinding("gemini", "gemini-2.5-flash"))
    assert isinstance(executor, AgnoVisionModelExecutor)
    assert executor.model_ref == "gemini:gemini-2.5-flash"
    assert calls == [{"id": "gemini-2.5-flash", "api_key": "test-secret"}]

    for binding in (
        ProviderBinding("deepseek", "deepseek-chat"),
        ProviderBinding("gemini", "text-only-model"),
        ProviderBinding("gemini", "gemini-embedding-001"),
    ):
        with pytest.raises(ProviderConfigurationError):
            factory.create_vision(binding)
    assert len(calls) == 1


def test_production_vision_composition_has_no_default_or_cross_agent_route():
    composition = ProductionProviderComposition(
        bindings_json=json.dumps(
            {
                "vision_observation": {
                    "provider_profile": "gemini",
                    "model_id": "gemini-2.5-flash",
                }
            }
        ),
        egress_enabled=True,
        environ={"GOOGLE_API_KEY": "secret"},
        constructors={"gemini": lambda **_kwargs: object()},
    )
    assert isinstance(composition.vision_executor_for(), AgnoVisionModelExecutor)
    with pytest.raises(ProviderConfigurationError):
        composition.vision_executor_for("plant_state")


def test_executor_sends_exact_json_and_one_in_memory_image(monkeypatch):
    seen = {}

    class Image:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Agent:
        def __init__(self, **kwargs):
            seen["agent"] = kwargs

        def run(self, payload, *, images):
            seen["payload"] = json.loads(payload)
            seen["images"] = images
            return SimpleNamespace(
                content={
                    "schema_version": 1,
                    "runtime_decision": "speak",
                    "observation_key": "leaf_spots",
                    "polarity": "present",
                    "severity": "mild",
                    "summary": "Small brown spots are visible.",
                    "confidence": 0.8,
                    "source_refs": [_request().source_refs[1]],
                    "reason_code": None,
                }
            )

    agno = ModuleType("agno")
    agent_module = ModuleType("agno.agent")
    media_module = ModuleType("agno.media")
    agent_module.Agent = Agent
    media_module.Image = Image
    monkeypatch.setitem(sys.modules, "agno", agno)
    monkeypatch.setitem(sys.modules, "agno.agent", agent_module)
    monkeypatch.setitem(sys.modules, "agno.media", media_module)

    request = _request()
    content = b"actual-image-bytes"
    import hashlib

    media = VisionMediaV1(
        source_ref=request.source_refs[1],
        content_type="image/jpeg",
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )
    executor = AgnoVisionModelExecutor(
        binding=ProviderBinding("gemini", "gemini-2.5-flash"),
        model=object(),
    )
    # Return refs are validated by the service, not by this transport seam.
    execution = executor.execute(request, media)
    assert execution.model_ref == "gemini:gemini-2.5-flash"
    assert seen["payload"] == request.as_provider_payload()
    assert len(seen["images"]) == 1
    assert seen["images"][0].kwargs == {"content": content, "format": "jpeg"}
    assert "filepath" not in seen["images"][0].kwargs
    assert "authorization" not in str(seen["payload"]).lower()
