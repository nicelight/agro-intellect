"""Strict deployment bindings and no-fallback Agno provider composition."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from os import environ as os_environ
import re
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from .contracts import ProviderRequestV1
from .roster import CANONICAL_AGENT_IDS
from .service import ModelExecution


_MODEL_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
SUPPORTED_PROVIDER_PROFILES = frozenset({"deepseek", "gemini", "chatgpt_oauth"})


class ProviderConfigurationError(RuntimeError):
    """Safe fail-closed configuration error."""

    def __init__(self) -> None:
        super().__init__("Agent Runtime provider is not configured.")


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    provider_profile: str
    model_id: str

    def __post_init__(self) -> None:
        if (
            self.provider_profile not in SUPPORTED_PROVIDER_PROFILES
            or not isinstance(self.model_id, str)
            or _MODEL_ID_RE.fullmatch(self.model_id) is None
        ):
            raise ProviderConfigurationError()

    @property
    def model_ref(self) -> str:
        return f"{self.provider_profile}:{self.model_id}"


class ProviderBindingResolver:
    def __init__(self, bindings: Mapping[str, ProviderBinding]) -> None:
        self._bindings = dict(bindings)

    @classmethod
    def from_json(cls, value: str) -> "ProviderBindingResolver":
        return cls(parse_provider_bindings(value))

    def resolve(self, agent_id: str) -> ProviderBinding | None:
        return self._bindings.get(agent_id)


class ChatGptOAuthCredentialAdapter(Protocol):
    def build_executor(self, binding: ProviderBinding): ...


class _AgentModelResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    runtime_decision: str
    candidate_claim_type: str | None
    candidate_output: str | None
    confidence: float | None
    source_refs: list[str]
    reason_code: str | None


class AgnoModelExecutor:
    """Production executor that sends only the serialized ProviderRequestV1."""

    def __init__(self, *, binding: ProviderBinding, model: object) -> None:
        self._binding = binding
        self._model = model
        self.model_ref = binding.model_ref

    def execute(self, request: ProviderRequestV1) -> ModelExecution:
        from agno.agent import Agent

        agent = Agent(
            model=self._model,
            output_schema=_AgentModelResultSchema,
            markdown=False,
        )
        payload = json.dumps(
            request.as_provider_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        response = agent.run(payload)
        content = getattr(response, "content", response)
        if isinstance(content, BaseModel):
            result = content.model_dump()
        elif isinstance(content, Mapping):
            result = dict(content)
        elif isinstance(content, str):
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("Provider returned a non-object result.")
            result = parsed
        else:
            raise ValueError("Provider returned an unsupported result.")
        return ModelExecution(model_ref=self.model_ref, result=result)


ModelConstructor = Callable[..., object]


class AgnoModelExecutorFactory:
    """Construct exactly one explicitly selected provider; never fall back."""

    def __init__(
        self,
        *,
        egress_enabled: bool,
        environ: Mapping[str, str] | None = None,
        chatgpt_oauth_adapter: ChatGptOAuthCredentialAdapter | None = None,
        constructors: Mapping[str, ModelConstructor] | None = None,
    ) -> None:
        self._egress_enabled = egress_enabled
        self._environ = os_environ if environ is None else environ
        self._oauth_adapter = chatgpt_oauth_adapter
        self._constructors = dict(constructors or {})

    def create(self, binding: ProviderBinding) -> object:
        if not self._egress_enabled:
            raise ProviderConfigurationError()
        if binding.provider_profile == "chatgpt_oauth":
            if self._oauth_adapter is None:
                raise ProviderConfigurationError()
            try:
                return self._oauth_adapter.build_executor(binding)
            except Exception:
                raise ProviderConfigurationError() from None

        credential_name = (
            "DEEPSEEK_API_KEY"
            if binding.provider_profile == "deepseek"
            else "GOOGLE_API_KEY"
        )
        credential = self._environ.get(credential_name)
        if not isinstance(credential, str) or not credential:
            raise ProviderConfigurationError()
        try:
            constructor = self._constructors.get(binding.provider_profile)
            if constructor is None:
                constructor = _native_constructor(binding.provider_profile)
            model = constructor(id=binding.model_id, api_key=credential)
        except Exception:
            raise ProviderConfigurationError() from None
        return AgnoModelExecutor(binding=binding, model=model)


class ProductionProviderComposition:
    """Resolve a canonical agent's deployment binding before construction."""

    def __init__(
        self,
        *,
        bindings_json: str,
        egress_enabled: bool,
        environ: Mapping[str, str] | None = None,
        chatgpt_oauth_adapter: ChatGptOAuthCredentialAdapter | None = None,
        constructors: Mapping[str, ModelConstructor] | None = None,
    ) -> None:
        self._resolver = ProviderBindingResolver.from_json(bindings_json)
        self._factory = AgnoModelExecutorFactory(
            egress_enabled=egress_enabled,
            environ=environ,
            chatgpt_oauth_adapter=chatgpt_oauth_adapter,
            constructors=constructors,
        )

    def executor_for(self, agent_id: str) -> object:
        if agent_id not in CANONICAL_AGENT_IDS:
            raise ProviderConfigurationError()
        binding = self._resolver.resolve(agent_id)
        if binding is None:
            raise ProviderConfigurationError()
        return self._factory.create(binding)


def parse_provider_bindings(value: str) -> dict[str, ProviderBinding]:
    if not isinstance(value, str):
        raise ProviderConfigurationError()
    try:
        raw = json.loads(value, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise ProviderConfigurationError() from None
    if not isinstance(raw, dict):
        raise ProviderConfigurationError()
    bindings: dict[str, ProviderBinding] = {}
    for agent_id, item in raw.items():
        if agent_id not in CANONICAL_AGENT_IDS or not isinstance(item, dict):
            raise ProviderConfigurationError()
        if set(item) != {"provider_profile", "model_id"}:
            raise ProviderConfigurationError()
        if not isinstance(item["provider_profile"], str) or not isinstance(
            item["model_id"], str
        ):
            raise ProviderConfigurationError()
        bindings[agent_id] = ProviderBinding(
            provider_profile=item["provider_profile"],
            model_id=item["model_id"],
        )
    return bindings


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def _native_constructor(profile: str) -> ModelConstructor:
    if profile == "deepseek":
        from agno.models.deepseek import DeepSeek

        return DeepSeek
    if profile == "gemini":
        from agno.models.google import Gemini

        return Gemini
    raise ProviderConfigurationError()


__all__ = [
    "AgnoModelExecutor",
    "AgnoModelExecutorFactory",
    "ChatGptOAuthCredentialAdapter",
    "ProviderBinding",
    "ProviderBindingResolver",
    "ProviderConfigurationError",
    "ProductionProviderComposition",
    "SUPPORTED_PROVIDER_PROFILES",
    "parse_provider_bindings",
]
