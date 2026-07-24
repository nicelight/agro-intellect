from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Union
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import require_actor_context
from ..access_admin.errors import request_id_for
from ..agent_chat.feed import PlantFeedError, PlantFeedErrorCode, PlantFeedService


router = APIRouter(prefix="/api", tags=["plant-feed"])

_UUID_FRAGMENT = (
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
CompanionIssueRef = Annotated[
    str,
    Field(pattern=rf"^companion_issue:{_UUID_FRAGMENT}$"),
]
CompanionAttentionRef = Annotated[
    str,
    Field(pattern=rf"^companion_attention:{_UUID_FRAGMENT}$"),
]
CompanionProposalRef = Annotated[
    str,
    Field(pattern=rf"^companion_proposal:{_UUID_FRAGMENT}$"),
]
DecisionRecordRef = Annotated[
    str,
    Field(pattern=rf"^decision_record:{_UUID_FRAGMENT}$"),
]
CompanionCompactText = Annotated[str, Field(min_length=1, max_length=500)]


class ErrorDetail(BaseModel): code: str; message: str; request_id: str
class ErrorEnvelope(BaseModel): error: ErrorDetail
class AgentIntroductionPayload(BaseModel):
    payload_kind: Literal["agent_introduction"]; agent_id: str; display_name: str; competence_summary: str; introduction_text: str; roster_version: int
class AgentMessagePayload(BaseModel):
    payload_kind: Literal["agent_message"]; agent_id: str; candidate_claim_type: Literal["observation", "hypothesis", "recommendation", "clarification", "team_signal"]; quoted_text: str
class BlockNoticePayload(BaseModel):
    payload_kind: Literal["block_notice"]; notice_code: Literal["classification_uncertain"]; text: Literal["Сообщение заблокировано до уточнения безопасности."]
class SafetyEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["fresh", "stale", "missing"]; source_ref: str | None; measured_at: datetime | None
class SafetyApprovalInputFreshness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Literal["approval_input"]; window_hours: Literal[2]; computed_at: datetime; ph: SafetyEvidenceItem; ec: SafetyEvidenceItem
class SafetyStatusPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload_kind: Literal["safety_status"]
    decision_ref: str; classification_ref: str
    action_kind: Literal["ph_adjustment", "ec_adjustment", "solution_change", "pump_command", "light_command", "dosing_command", "pruning", "transplanting", "root_trimming", "other_physical_action"]
    safety_status: Literal["safety_blocked", "needs_fresh_evidence", "pending_human_approval"]
    reason_code: Literal["unsupported_action", "approval_authority_missing", "approval_input_missing_or_stale", "ready_for_human_approval"]
    summary_text: str; evidence_refs: list[str]
    approval_input_freshness: SafetyApprovalInputFreshness | None
    expires_at: datetime | None
class CompanionAttentionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload_kind: Literal["companion_attention"]
    attention_ref: CompanionAttentionRef
    issue_ref: CompanionIssueRef
    summary_text: CompanionCompactText
class CompanionProposalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload_kind: Literal["companion_proposal"]
    proposal_ref: CompanionProposalRef
    issue_ref: CompanionIssueRef
    proposal_state: Literal["pending", "approved", "rejected", "superseded"]
    summary_text: CompanionCompactText
class CompanionDecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload_kind: Literal["companion_decision"]
    decision_record_ref: DecisionRecordRef
    issue_ref: CompanionIssueRef
    proposal_ref: CompanionProposalRef
    decision_summary: CompanionCompactText
    safety_gate_authority: Literal["not_granted"]
DisplayPayload = Annotated[Union[AgentIntroductionPayload, AgentMessagePayload, BlockNoticePayload, SafetyStatusPayload, CompanionAttentionPayload, CompanionProposalPayload, CompanionDecisionPayload], "payload_kind"]
class UIFeedItemResponse(BaseModel):
    schema_version: Literal[1]; ui_event_id: uuid.UUID; created_at: datetime; farm_id: uuid.UUID; plant_id: uuid.UUID
    source_type: Literal["system", "agent_message", "safety", "companion_governance"]; source_id: str; source_refs: list[str]
    display_kind: Literal["agent_introduction", "agent_message", "block_notice", "safety_status", "companion_governance"]; display_payload: DisplayPayload
    visible_to_roles: list[Literal["boss", "engineer", "consultant"]]; visible_to_agents: Literal[False]; consumable_by_agents: Literal[False]
class PlantFeedResponse(BaseModel): items: list[UIFeedItemResponse]; next_cursor: str | None


_ERRORS = {PlantFeedErrorCode.AUTH_PLANT_FORBIDDEN: (404, "Plant is not available."), PlantFeedErrorCode.FEED_CURSOR_INVALID: (422, "Feed cursor is invalid."), PlantFeedErrorCode.FEED_LIMIT_INVALID: (422, "Feed limit is invalid."), PlantFeedErrorCode.VALIDATION_FAILED: (422, "Request validation failed."), PlantFeedErrorCode.FEED_PERSISTENCE_FAILED: (500, "Plant feed could not be read.")}
_RESPONSES = {401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}}


@router.get("/plants/{plant_id}/feed", response_model=PlantFeedResponse, responses=_RESPONSES, openapi_extra={"parameters": [{"name": "cursor", "in": "query", "required": False, "schema": {"type": "string"}}, {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100}}]})
def get_plant_feed(plant_id: uuid.UUID, request: Request, response: Response, actor: ActorContext = Depends(require_actor_context)):
    try:
        cursor, limit = _query(request)
        try:
            with request.app.state.database.session() as session:
                page = PlantFeedService(session).list_feed(actor, plant_id=plant_id, cursor=cursor, limit=limit)
        except PlantFeedError: raise
        except Exception: raise PlantFeedError(PlantFeedErrorCode.FEED_PERSISTENCE_FAILED) from None
    except PlantFeedError as error:
        status, message = _ERRORS[error.code]
        return JSONResponse(status_code=status, content={"error": {"code": error.code.value, "message": message, "request_id": request_id_for(request)}}, headers={"Cache-Control": "no-store"})
    response.headers["Cache-Control"] = "no-store"
    return {"items": [item.as_value() for item in page.items], "next_cursor": page.next_cursor}


def _query(request: Request) -> tuple[str | None, int]:
    if any(key not in {"cursor", "limit"} for key in request.query_params.keys()) or any(len(request.query_params.getlist(key)) > 1 for key in ("cursor", "limit")):
        raise PlantFeedError(PlantFeedErrorCode.VALIDATION_FAILED)
    cursor = request.query_params.get("cursor")
    if cursor == "": raise PlantFeedError(PlantFeedErrorCode.FEED_CURSOR_INVALID)
    raw_limit = request.query_params.get("limit")
    if raw_limit is None: return cursor, 50
    try:
        if not raw_limit or raw_limit.strip() != raw_limit or not raw_limit.isascii() or not raw_limit.isdecimal(): raise ValueError
        limit = int(raw_limit)
        if raw_limit != str(limit): raise ValueError
    except ValueError: raise PlantFeedError(PlantFeedErrorCode.FEED_LIMIT_INVALID) from None
    return cursor, limit


__all__ = ["router"]
