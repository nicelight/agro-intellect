"""Harness domain models — permission verdicts and decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class PermissionVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"
    APPROVAL_REQUIRED = "approval_required"
    REQUIRE_STRONGER_AUTH = "require_stronger_auth"
    RUN_IN_SANDBOX = "run_in_sandbox"
    RUN_AS_DRAFT_ONLY = "run_as_draft_only"


@dataclass(frozen=True)
class PermissionDecision:
    verdict: PermissionVerdict
    reason: str
    actor_context_ref: str | None
    tool_name: str | None = None
    trace_ref: str | None = None
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))
