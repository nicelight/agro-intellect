"""Deployment mode and configuration for local-first MVP."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeploymentMode(str, Enum):
    LOOPBACK = "loopback"
    LAN = "lan"


@dataclass(frozen=True)
class DeploymentConfig:
    mode: DeploymentMode = DeploymentMode.LOOPBACK
    allowed_origins: tuple[str, ...] = ()
    csrf_protection_enabled: bool = True
