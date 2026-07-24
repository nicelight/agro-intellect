from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from types import MappingProxyType
import unicodedata
import uuid


_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_AGENT_RE = re.compile(r"[a-z][a-z0-9_]{2,63}\Z")
_ROLES = frozenset({"boss", "engineer", "consultant"})


class AgentChatContractError(ValueError):
    pass


def _closed(value: object, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise AgentChatContractError("Strict v1 object has invalid fields.")
    return dict(value)


def _uuid(value: object, *, version: int | None = None) -> uuid.UUID:
    if not isinstance(value, str):
        raise AgentChatContractError()
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise AgentChatContractError() from None
    if str(parsed) != value.lower() or (version is not None and parsed.version != version):
        raise AgentChatContractError()
    return parsed


def _time(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AgentChatContractError()
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise AgentChatContractError() from None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise AgentChatContractError()
    return parsed


def timestamp_text(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _refs(value: object, *, minimum: int) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AgentChatContractError()
    refs = tuple(value)
    if not minimum <= len(refs) <= 4 or len(set(refs)) != len(refs) or any(
        not isinstance(ref, str) or _REF_RE.fullmatch(ref) is None for ref in refs
    ):
        raise AgentChatContractError()
    return refs


def _actor_ref(value: object) -> Mapping[str, object] | None:
    if value is None:
        return None
    fields = _closed(value, {"account_id", "membership_id", "role_preset"})
    _uuid(fields["account_id"]); _uuid(fields["membership_id"])
    if fields["role_preset"] not in _ROLES:
        raise AgentChatContractError()
    return MappingProxyType(fields)


def _auth_scope(value: object) -> Mapping[str, object] | None:
    if value is None:
        return None
    fields = _closed(value, {"farm_id", "plant_id", "role_preset", "operation_kind", "permission_source", "grant_id"})
    _uuid(fields["farm_id"]); _uuid(fields["plant_id"])
    if fields["role_preset"] not in _ROLES or fields["operation_kind"] != "normal_read":
        raise AgentChatContractError()
    source = fields["permission_source"]
    if source == "boss_role":
        if fields["grant_id"] is not None: raise AgentChatContractError()
    elif source == "plant_access_grant":
        _uuid(fields["grant_id"])
    else:
        raise AgentChatContractError()
    return MappingProxyType(fields)


def _bus_payload(value: object, event_type: str) -> Mapping[str, object]:
    if event_type == "agent_safe_information":
        fields = _closed(value, {"payload_kind", "message_id", "classification_ref", "candidate_claim_type", "quoted_text"})
        if fields["payload_kind"] != "quoted_candidate": raise AgentChatContractError()
        _uuid(fields["message_id"])
        if not isinstance(fields["classification_ref"], str) or not fields["classification_ref"].startswith("safety_classification:"):
            raise AgentChatContractError()
        _uuid(fields["classification_ref"].split(":", 1)[1])
        if fields["candidate_claim_type"] not in {"observation", "hypothesis", "recommendation", "clarification", "team_signal"}:
            raise AgentChatContractError()
        if not isinstance(fields["quoted_text"], str) or not fields["quoted_text"]:
            raise AgentChatContractError()
    else:
        fields = _closed(value, {"payload_kind", "record_type", "record_ref"})
        if fields["payload_kind"] != "domain_event_ref" or fields["record_type"] not in {"daily_checkin", "manual_measurement", "photo_catalog_item"} or not isinstance(fields["record_ref"], str) or _REF_RE.fullmatch(fields["record_ref"]) is None:
            raise AgentChatContractError()
    return MappingProxyType(fields)


@dataclass(frozen=True, slots=True)
class BusEventEnvelopeV1:
    event_id: uuid.UUID; event_type: str; created_at: datetime; farm_id: uuid.UUID; plant_id: uuid.UUID
    actor_ref: Mapping[str, object] | None; source_type: str; source_id: str
    payload: Mapping[str, object]; source_refs: tuple[str, ...]; authorization_scope: Mapping[str, object] | None
    schema_version: int = 1; consumable_by_agents: bool = True

    @classmethod
    def from_untrusted(cls, value: object) -> "BusEventEnvelopeV1":
        f = _closed(value, {"schema_version", "event_id", "event_type", "created_at", "farm_id", "plant_id", "actor_ref", "source_type", "source_id", "payload", "source_refs", "consumable_by_agents", "authorization_scope"})
        if f["schema_version"] != 1 or f["event_type"] not in {"domain_event_ref", "agent_safe_information"} or f["source_type"] not in {"domain_record", "message_envelope"} or f["consumable_by_agents"] is not True:
            raise AgentChatContractError()
        event_id = _uuid(f["event_id"], version=4); farm_id = _uuid(f["farm_id"]); plant_id = _uuid(f["plant_id"])
        source_id = _uuid(f["source_id"])
        actor = _actor_ref(f["actor_ref"]); auth = _auth_scope(f["authorization_scope"])
        if (actor is None) != (auth is None): raise AgentChatContractError()
        event_type = str(f["event_type"]); source_type = str(f["source_type"])
        payload = _bus_payload(f["payload"], event_type)
        refs = _refs(f["source_refs"], minimum=1)
        if (event_type, source_type) not in {
            ("domain_event_ref", "domain_record"),
            ("agent_safe_information", "message_envelope"),
        }:
            raise AgentChatContractError()
        if auth is not None and (
            auth["farm_id"] != str(farm_id)
            or auth["plant_id"] != str(plant_id)
            or actor is None
            or auth["role_preset"] != actor["role_preset"]
        ):
            raise AgentChatContractError()
        if source_type == "message_envelope":
            if actor is None or auth is None or payload["message_id"] != str(source_id):
                raise AgentChatContractError()
            required_refs = {
                f"message_envelope:{source_id}",
                str(payload["classification_ref"]),
            }
            if not required_refs.issubset(refs):
                raise AgentChatContractError()
        elif actor is not None or auth is not None:
            raise AgentChatContractError()
        return cls(event_id, event_type, _time(f["created_at"]), farm_id, plant_id, actor, source_type, str(source_id), payload, refs, auth)

    def as_value(self) -> dict[str, object]:
        return {"schema_version": 1, "event_id": str(self.event_id), "event_type": self.event_type, "created_at": timestamp_text(self.created_at), "farm_id": str(self.farm_id), "plant_id": str(self.plant_id), "actor_ref": dict(self.actor_ref) if self.actor_ref else None, "source_type": self.source_type, "source_id": self.source_id, "payload": dict(self.payload), "source_refs": list(self.source_refs), "consumable_by_agents": True, "authorization_scope": dict(self.authorization_scope) if self.authorization_scope else None}


def _ui_payload(value: object, kind: str) -> Mapping[str, object]:
    if kind == "companion_governance":
        return _companion_ui_payload(value)
    shapes = {
        "agent_introduction": {"payload_kind", "agent_id", "display_name", "competence_summary", "introduction_text", "roster_version"},
        "agent_message": {"payload_kind", "agent_id", "candidate_claim_type", "quoted_text"},
        "block_notice": {"payload_kind", "notice_code", "text"},
        "safety_status": {"payload_kind", "decision_ref", "classification_ref", "action_kind", "safety_status", "reason_code", "summary_text", "evidence_refs", "approval_input_freshness", "expires_at"},
    }
    f = _closed(value, shapes[kind])
    if f["payload_kind"] != kind: raise AgentChatContractError()
    if kind == "agent_message":
        if not isinstance(f["agent_id"], str) or _AGENT_RE.fullmatch(f["agent_id"]) is None or f["candidate_claim_type"] not in {"observation", "hypothesis", "recommendation", "clarification", "team_signal"} or not isinstance(f["quoted_text"], str) or not f["quoted_text"]: raise AgentChatContractError()
    elif kind == "block_notice":
        if f != {"payload_kind": "block_notice", "notice_code": "classification_uncertain", "text": "Сообщение заблокировано до уточнения безопасности."}: raise AgentChatContractError()
    elif kind == "safety_status":
        _safety_status_payload(f)
    else:
        if not isinstance(f["agent_id"], str) or _AGENT_RE.fullmatch(f["agent_id"]) is None or not isinstance(f["roster_version"], int) or isinstance(f["roster_version"], bool) or f["roster_version"] < 1 or any(not isinstance(f[k], str) or not f[k] for k in ("display_name", "competence_summary", "introduction_text")): raise AgentChatContractError()
    return MappingProxyType(f)


def _companion_ui_payload(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AgentChatContractError()
    payload_kind = value.get("payload_kind")
    shapes = {
        "companion_attention": {
            "payload_kind",
            "attention_ref",
            "issue_ref",
            "summary_text",
        },
        "companion_proposal": {
            "payload_kind",
            "proposal_ref",
            "issue_ref",
            "proposal_state",
            "summary_text",
        },
        "companion_decision": {
            "payload_kind",
            "decision_record_ref",
            "issue_ref",
            "proposal_ref",
            "decision_summary",
            "safety_gate_authority",
        },
    }
    if payload_kind not in shapes:
        raise AgentChatContractError()
    fields = _closed(value, shapes[str(payload_kind)])
    _typed_ref(fields["issue_ref"], "companion_issue")
    if payload_kind == "companion_attention":
        _typed_ref(fields["attention_ref"], "companion_attention")
        _compact_text(fields["summary_text"])
    elif payload_kind == "companion_proposal":
        _typed_ref(fields["proposal_ref"], "companion_proposal")
        if fields["proposal_state"] not in {
            "pending",
            "approved",
            "rejected",
            "superseded",
        }:
            raise AgentChatContractError()
        _compact_text(fields["summary_text"])
    else:
        _typed_ref(fields["decision_record_ref"], "decision_record")
        _typed_ref(fields["proposal_ref"], "companion_proposal")
        _compact_text(fields["decision_summary"])
        if fields["safety_gate_authority"] != "not_granted":
            raise AgentChatContractError()
    return MappingProxyType(fields)


def _compact_text(value: object) -> None:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not 1 <= len(value) <= 500
        or any(unicodedata.category(character).startswith("C") for character in value)
    ):
        raise AgentChatContractError()


def _safety_status_payload(fields: dict[str, object]) -> None:
    action = fields["action_kind"]
    status = fields["safety_status"]
    reason = fields["reason_code"]
    supported = {"ph_adjustment", "ec_adjustment", "solution_change"}
    unsupported = {"pump_command", "light_command", "dosing_command", "pruning", "transplanting", "root_trimming", "other_physical_action"}
    if action not in supported | unsupported:
        raise AgentChatContractError()
    decision_id = _typed_ref(fields["decision_ref"], "safety_decision")
    _typed_ref(fields["classification_ref"], "safety_classification")
    evidence = _measurement_refs(fields["evidence_refs"])
    summaries = {
        "unsupported_action": "Действие не поддерживается безопасным процессом MVP.",
        "approval_authority_missing": "Действие заблокировано: у текущего пользователя нет права подтверждения.",
        "approval_input_missing_or_stale": "Перед предложением действия нужны свежие измерения pH и EC.",
        ("ready_for_human_approval", "ph_adjustment"): "Предложена ручная корректировка pH. Требуется решение уполномоченного пользователя.",
        ("ready_for_human_approval", "ec_adjustment"): "Предложена ручная корректировка EC питательного раствора. Требуется решение уполномоченного пользователя.",
        ("ready_for_human_approval", "solution_change"): "Предложена ручная замена питательного раствора. Требуется решение уполномоченного пользователя.",
    }
    expected_summary = summaries.get((reason, action), summaries.get(reason))
    if fields["summary_text"] != expected_summary:
        raise AgentChatContractError()
    freshness = fields["approval_input_freshness"]
    expires = fields["expires_at"]
    if reason == "unsupported_action":
        valid_route = action in unsupported and status == "safety_blocked"
    elif reason == "approval_authority_missing":
        valid_route = action in supported and status == "safety_blocked"
    elif reason == "approval_input_missing_or_stale":
        valid_route = action in supported and status == "needs_fresh_evidence"
    elif reason == "ready_for_human_approval":
        valid_route = action in supported and status == "pending_human_approval"
    else:
        valid_route = False
    if not valid_route:
        raise AgentChatContractError()
    if reason in {"unsupported_action", "approval_authority_missing"}:
        if freshness is not None or expires is not None or evidence:
            raise AgentChatContractError()
        return
    snapshot = _closed(freshness, {"purpose", "window_hours", "computed_at", "ph", "ec"})
    if snapshot["purpose"] != "approval_input" or snapshot["window_hours"] != 2:
        raise AgentChatContractError()
    computed_at = _time(snapshot["computed_at"])
    statuses: list[str] = []
    source_refs: list[str] = []
    measured_times: list[datetime] = []
    for name in ("ph", "ec"):
        item = _closed(snapshot[name], {"status", "source_ref", "measured_at"})
        item_status = item["status"]
        if item_status not in {"fresh", "stale", "missing"}:
            raise AgentChatContractError()
        statuses.append(str(item_status))
        if item_status == "missing":
            if item["source_ref"] is not None or item["measured_at"] is not None:
                raise AgentChatContractError()
        else:
            _typed_ref(item["source_ref"], "manual_measurement")
            measured = _time(item["measured_at"])
            source_refs.append(str(item["source_ref"]))
            measured_times.append(measured)
            is_fresh = computed_at - timedelta(hours=2) <= measured <= computed_at
            if (item_status == "fresh") is not is_fresh:
                raise AgentChatContractError()
    if tuple(dict.fromkeys(source_refs)) != evidence:
        raise AgentChatContractError()
    if reason == "approval_input_missing_or_stale":
        if statuses == ["fresh", "fresh"] or expires is not None:
            raise AgentChatContractError()
    else:
        if statuses != ["fresh", "fresh"] or len(measured_times) != 2:
            raise AgentChatContractError()
        expected_expiry = min(item + timedelta(hours=2) for item in measured_times)
        if _time(expires) != expected_expiry:
            raise AgentChatContractError()
    if not isinstance(decision_id, uuid.UUID):
        raise AgentChatContractError()


def _typed_ref(value: object, kind: str) -> uuid.UUID:
    if not isinstance(value, str) or not value.startswith(f"{kind}:"):
        raise AgentChatContractError()
    return _uuid(value.split(":", 1)[1], version=4)


def _measurement_refs(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AgentChatContractError()
    refs = tuple(value)
    if len(refs) > 2 or len(set(refs)) != len(refs):
        raise AgentChatContractError()
    for ref in refs:
        _typed_ref(ref, "manual_measurement")
    return refs


@dataclass(frozen=True, slots=True)
class UIFeedEventV1:
    ui_event_id: uuid.UUID; created_at: datetime; farm_id: uuid.UUID; plant_id: uuid.UUID; source_type: str; source_id: str
    source_refs: tuple[str, ...]; display_kind: str; display_payload: Mapping[str, object]; visible_to_roles: tuple[str, ...]
    schema_version: int = 1; visible_to_agents: bool = False; consumable_by_agents: bool = False

    @classmethod
    def from_untrusted(cls, value: object) -> "UIFeedEventV1":
        f = _closed(value, {"schema_version", "ui_event_id", "created_at", "farm_id", "plant_id", "source_type", "source_id", "source_refs", "display_kind", "display_payload", "visible_to_roles", "visible_to_agents", "consumable_by_agents"})
        kind = f["display_kind"]
        if f["schema_version"] != 1 or kind not in {"agent_introduction", "agent_message", "block_notice", "safety_status", "companion_governance"} or f["source_type"] not in {"system", "agent_message", "safety", "companion_governance"} or f["visible_to_agents"] is not False or f["consumable_by_agents"] is not False: raise AgentChatContractError()
        roles = tuple(f["visible_to_roles"]) if isinstance(f["visible_to_roles"], list) else ()
        if not roles or len(roles) != len(set(roles)) or not set(roles).issubset(_ROLES): raise AgentChatContractError()
        source_id = _uuid(f["source_id"])
        application_event = kind != "agent_introduction"
        ui_event_id = _uuid(f["ui_event_id"], version=4 if application_event else None)
        source_type = str(f["source_type"])
        expected_source = {
            "agent_introduction": "system",
            "agent_message": "agent_message",
            "block_notice": "safety",
            "safety_status": "safety",
            "companion_governance": "companion_governance",
        }[str(kind)]
        if source_type != expected_source:
            raise AgentChatContractError()
        refs = _refs(f["source_refs"], minimum=0)
        if kind == "agent_introduction":
            if source_id != ui_event_id or f"agent_introduction:{source_id}" not in refs:
                raise AgentChatContractError()
        elif kind == "safety_status":
            payload = _ui_payload(f["display_payload"], str(kind))
            decision_ref = f"safety_decision:{source_id}"
            classification_ref = str(payload["classification_ref"])
            classification_id = classification_ref.split(":", 1)[1]
            expected_refs = (
                f"message_envelope:{classification_id}",
                classification_ref,
                *tuple(payload["evidence_refs"]),
            )
            if ui_event_id != source_id or payload["decision_ref"] != decision_ref or refs != expected_refs or roles != ("boss", "engineer"):
                raise AgentChatContractError()
            return cls(ui_event_id, _time(f["created_at"]), _uuid(f["farm_id"]), _uuid(f["plant_id"]), source_type, str(source_id), refs, str(kind), payload, roles)
        elif kind == "companion_governance":
            payload = _ui_payload(f["display_payload"], str(kind))
            payload_kind = payload["payload_kind"]
            issue_ref = str(payload["issue_ref"])
            if payload_kind == "companion_attention":
                primary_ref = str(payload["attention_ref"])
                expected_refs = (
                    issue_ref,
                    primary_ref,
                    _ref_of_kind(refs, 2, "companion_proposal"),
                )
            elif payload_kind == "companion_proposal":
                primary_ref = str(payload["proposal_ref"])
                expected_refs = (
                    issue_ref,
                    _ref_of_kind(refs, 1, "companion_attention"),
                    primary_ref,
                    _ref_of_kind(refs, 3, "safety_classification"),
                )
            else:
                primary_ref = str(payload["decision_record_ref"])
                expected_refs = (
                    issue_ref,
                    str(payload["proposal_ref"]),
                    primary_ref,
                    *(
                        (_ref_of_kind(refs, 3, "task"),)
                        if len(refs) == 4
                        else ()
                    ),
                )
            primary_id = _typed_ref(primary_ref, primary_ref.split(":", 1)[0])
            if (
                source_id != primary_id
                or ui_event_id != primary_id
                or refs != expected_refs
                or roles != ("boss", "engineer", "consultant")
            ):
                raise AgentChatContractError()
            return cls(ui_event_id, _time(f["created_at"]), _uuid(f["farm_id"]), _uuid(f["plant_id"]), source_type, str(source_id), refs, str(kind), payload, roles)
        elif f"message_envelope:{source_id}" not in refs:
            raise AgentChatContractError()
        return cls(ui_event_id, _time(f["created_at"]), _uuid(f["farm_id"]), _uuid(f["plant_id"]), source_type, str(source_id), refs, str(kind), _ui_payload(f["display_payload"], str(kind)), roles)

    def as_value(self) -> dict[str, object]:
        return {"schema_version": 1, "ui_event_id": str(self.ui_event_id), "created_at": timestamp_text(self.created_at), "farm_id": str(self.farm_id), "plant_id": str(self.plant_id), "source_type": self.source_type, "source_id": self.source_id, "source_refs": list(self.source_refs), "display_kind": self.display_kind, "display_payload": dict(self.display_payload), "visible_to_roles": list(self.visible_to_roles), "visible_to_agents": False, "consumable_by_agents": False}


def _ref_of_kind(refs: tuple[str, ...], index: int, kind: str) -> str:
    try:
        ref = refs[index]
    except IndexError:
        raise AgentChatContractError() from None
    _typed_ref(ref, kind)
    return ref


__all__ = ["AgentChatContractError", "BusEventEnvelopeV1", "UIFeedEventV1", "timestamp_text"]
