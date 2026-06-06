"""Permission engine — gate for agent harness run and tool authorization."""

from __future__ import annotations

from backend.app.api.errors import AppError, ErrorCode
from backend.app.context.models import ActorContext, ActorContextState
from backend.app.harness.models import PermissionDecision, PermissionVerdict


class PermissionEngine:
    def __init__(self, context_builder) -> None:
        self._context_builder = context_builder

    def authorize_run(
        self,
        actor_context: ActorContext,
        agent_profile_id: str,
        request_ref: str,
        tool_name: str | None = None,
        trace_ref: str | None = None,
    ) -> PermissionDecision:
        if actor_context.state is ActorContextState.DENIED:
            return PermissionDecision(
                verdict=PermissionVerdict.DENY,
                reason="Session is invalid or denied.",
                actor_context_ref=actor_context.session_ref,
                tool_name=tool_name,
                trace_ref=trace_ref,
            )

        if actor_context.state is ActorContextState.EXPIRED:
            return PermissionDecision(
                verdict=PermissionVerdict.DENY,
                reason="Session has expired.",
                actor_context_ref=actor_context.session_ref,
                tool_name=tool_name,
                trace_ref=trace_ref,
            )

        if actor_context.state is not ActorContextState.RESOLVED:
            return PermissionDecision(
                verdict=PermissionVerdict.DENY,
                reason="ActorContext is not resolved.",
                actor_context_ref=actor_context.session_ref,
                tool_name=tool_name,
                trace_ref=trace_ref,
            )

        return PermissionDecision(
            verdict=PermissionVerdict.ALLOW,
            reason="ActorContext is resolved; run authorized.",
            actor_context_ref=actor_context.session_ref,
            tool_name=tool_name,
            trace_ref=trace_ref,
        )

    def authorize_tool(
        self,
        actor_context: ActorContext,
        tool_name: str | None = None,
        args: dict | None = None,
        trace_ref: str | None = None,
    ) -> PermissionDecision:
        if actor_context.state is not ActorContextState.RESOLVED:
            return PermissionDecision(
                verdict=PermissionVerdict.DENY,
                reason="ActorContext must be resolved to use tools.",
                actor_context_ref=actor_context.session_ref,
                tool_name=tool_name,
                trace_ref=trace_ref,
            )

        return PermissionDecision(
            verdict=PermissionVerdict.ALLOW,
            reason="Tool access authorized for resolved context.",
            actor_context_ref=actor_context.session_ref,
            tool_name=tool_name,
            trace_ref=trace_ref,
        )

    def require_resolved_context(self, actor_context: ActorContext) -> None:
        if actor_context.state is not ActorContextState.RESOLVED:
            raise AppError(
                code=ErrorCode.PERMISSION_DENIED,
                message="A resolved ActorContext is required.",
                request_ref=actor_context.request_ref,
                next_actions=["authenticate"],
            )
