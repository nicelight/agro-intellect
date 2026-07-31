"""Provider-neutral composition bindings.

Production intentionally constructs this value with both executors unbound.
Tests may pass explicit spies through ``create_app``; no environment or caller
input is consulted here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderExecutorBindings:
    companion: object | None = None
    safety_gate: object | None = None


__all__ = ["ProviderExecutorBindings"]
