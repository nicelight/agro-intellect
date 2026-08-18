import { backendFetch, safeErrorFromResult } from '$lib/server/backend';
import type { SafeError } from '$lib/session/types';
import type {
	AgentMessagePayload,
	BlockNoticePayload,
	CompanionAttentionPayload,
	CompanionDecisionPayload,
	CompanionProposalPayload,
	FeedItem,
	FeedPage,
	FeedPageOutcome,
	FeedPayload,
	RosterPayload,
	SafetyApprovalInputFreshness,
	SafetyEvidenceItem,
	SafetyStatusPayload
} from './types';

const FEED_RESPONSE_INVALID: SafeError = {
	code: 'FEED_RESPONSE_INVALID',
	message: 'The service returned an unexpected Plant feed result.'
};

function isRecord(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function str(value: unknown): string | null {
	return typeof value === 'string' ? value : null;
}

function bool(value: unknown): boolean | null {
	return typeof value === 'boolean' ? value : null;
}

function num(value: unknown): number | null {
	return typeof value === 'number' && !Number.isNaN(value) ? value : null;
}

function strings(value: unknown): string[] | null {
	if (!Array.isArray(value)) return null;
	const result: string[] = [];
	for (const entry of value) {
		if (typeof entry !== 'string') return null;
		result.push(entry);
	}
	return result;
}

function evidenceItemFromBody(value: unknown): SafetyEvidenceItem | null {
	if (!isRecord(value)) return null;
	const status = str(value.status);
	if (status !== 'fresh' && status !== 'stale' && status !== 'missing') return null;
	const source_ref = value.source_ref == null ? null : str(value.source_ref);
	const measured_at = value.measured_at == null ? null : str(value.measured_at);
	if (source_ref === null && value.source_ref != null) return null;
	if (measured_at === null && value.measured_at != null) return null;
	return { status, source_ref, measured_at };
}

function approvalFreshnessFromBody(value: unknown): SafetyApprovalInputFreshness | null {
	if (!isRecord(value)) return null;
	if (str(value.purpose) !== 'approval_input') return null;
	if (num(value.window_hours) !== 2) return null;
	const computed_at = str(value.computed_at);
	const ph = evidenceItemFromBody(value.ph);
	const ec = evidenceItemFromBody(value.ec);
	if (computed_at === null || ph === null || ec === null) return null;
	return { purpose: 'approval_input', window_hours: 2, computed_at, ph, ec };
}

function rosterFromBody(value: unknown): RosterPayload | null {
	if (!isRecord(value)) return null;
	const agent_id = str(value.agent_id);
	const display_name = str(value.display_name);
	const competence_summary = str(value.competence_summary);
	const introduction_text = str(value.introduction_text);
	const roster_version = num(value.roster_version);
	if (
		agent_id === null ||
		display_name === null ||
		competence_summary === null ||
		introduction_text === null ||
		roster_version === null
	) {
		return null;
	}
	return {
		payload_kind: 'agent_introduction',
		agent_id,
		display_name,
		competence_summary,
		introduction_text,
		roster_version
	};
}

function agentMessageFromBody(value: unknown): AgentMessagePayload | null {
	if (!isRecord(value)) return null;
	const agent_id = str(value.agent_id);
	const candidate_claim_type = str(value.candidate_claim_type);
	const quoted_text = str(value.quoted_text);
	if (agent_id === null || candidate_claim_type === null || quoted_text === null) return null;
	return {
		payload_kind: 'agent_message',
		agent_id,
		candidate_claim_type,
		quoted_text
	};
}

function blockNoticeFromBody(value: unknown): BlockNoticePayload | null {
	if (!isRecord(value)) return null;
	const notice_code = str(value.notice_code);
	const text = str(value.text);
	if (notice_code === null || text === null) return null;
	return { payload_kind: 'block_notice', notice_code, text };
}

function safetyStatusFromBody(value: unknown): SafetyStatusPayload | null {
	if (!isRecord(value)) return null;
	const decision_ref = str(value.decision_ref);
	const classification_ref = str(value.classification_ref);
	const action_kind = str(value.action_kind);
	const safety_status = str(value.safety_status);
	const reason_code = str(value.reason_code);
	const summary_text = str(value.summary_text);
	const evidence_refs = strings(value.evidence_refs);
	const expires_at = value.expires_at == null ? null : str(value.expires_at);
	const freshnessRaw =
		value.approval_input_freshness == null ? null : approvalFreshnessFromBody(value.approval_input_freshness);
	if (
		decision_ref === null ||
		classification_ref === null ||
		action_kind === null ||
		safety_status === null ||
		reason_code === null ||
		summary_text === null ||
		evidence_refs === null ||
		(value.approval_input_freshness != null && freshnessRaw === null) ||
		(expires_at === null && value.expires_at != null)
	) {
		return null;
	}
	return {
		payload_kind: 'safety_status',
		decision_ref,
		classification_ref,
		action_kind,
		safety_status,
		reason_code,
		summary_text,
		evidence_refs,
		approval_input_freshness: freshnessRaw,
		expires_at
	};
}

function companionAttentionFromBody(value: unknown): CompanionAttentionPayload | null {
	if (!isRecord(value)) return null;
	const attention_ref = str(value.attention_ref);
	const issue_ref = str(value.issue_ref);
	const summary_text = str(value.summary_text);
	if (attention_ref === null || issue_ref === null || summary_text === null) return null;
	return { payload_kind: 'companion_attention', attention_ref, issue_ref, summary_text };
}

function companionProposalFromBody(value: unknown): CompanionProposalPayload | null {
	if (!isRecord(value)) return null;
	const proposal_ref = str(value.proposal_ref);
	const issue_ref = str(value.issue_ref);
	const proposal_state = str(value.proposal_state);
	const summary_text = str(value.summary_text);
	if (proposal_ref === null || issue_ref === null || proposal_state === null || summary_text === null) {
		return null;
	}
	return {
		payload_kind: 'companion_proposal',
		proposal_ref,
		issue_ref,
		proposal_state,
		summary_text
	};
}

function companionDecisionFromBody(value: unknown): CompanionDecisionPayload | null {
	if (!isRecord(value)) return null;
	const decision_record_ref = str(value.decision_record_ref);
	const issue_ref = str(value.issue_ref);
	const proposal_ref = str(value.proposal_ref);
	const decision_summary = str(value.decision_summary);
	const safety_gate_authority = str(value.safety_gate_authority);
	if (
		decision_record_ref === null ||
		issue_ref === null ||
		proposal_ref === null ||
		decision_summary === null ||
		safety_gate_authority === null
	) {
		return null;
	}
	// The only registered Companion decision authority is `not_granted`;
	// any other value is not a registered canonically valid presentation.
	if (safety_gate_authority !== 'not_granted') return null;
	return {
		payload_kind: 'companion_decision',
		decision_record_ref,
		issue_ref,
		proposal_ref,
		decision_summary,
		safety_gate_authority: 'not_granted'
	};
}

/**
 * Exact discriminated union parsing of one `UIFeedEventV1` display payload.
 * The approval-gate authority value is preserved as presentation data but the
 * only accepted canonical value is `not_granted`; an unknown payload kind or
 * malformed variant fails closed (returns null) so untrusted rows are never
 * rendered with implied semantics.
 */
function payloadFromBody(displayKind: string | null, value: unknown): FeedPayload | null {
	if (!isRecord(value)) return null;
	const kind = value.payload_kind;
	if (typeof kind !== 'string') return null;
	// Registered variants: the outer `display_kind` must agree exactly with the
	// payload kind, except `companion_governance`, which discriminates one of
	// the three Companion variants by `payload_kind`.
	switch (displayKind) {
		case 'agent_introduction':
		case 'agent_message':
		case 'block_notice':
		case 'safety_status':
			if (kind !== displayKind) return null;
			break;
		case 'companion_governance':
			if (
				kind !== 'companion_attention' &&
				kind !== 'companion_proposal' &&
				kind !== 'companion_decision'
			) {
				return null;
			}
			break;
		default:
			return null;
	}
	switch (kind) {
		case 'agent_introduction':
			return rosterFromBody(value);
		case 'agent_message':
			return agentMessageFromBody(value);
		case 'block_notice':
			return blockNoticeFromBody(value);
		case 'safety_status':
			return safetyStatusFromBody(value);
		case 'companion_attention':
			return companionAttentionFromBody(value);
		case 'companion_proposal':
			return companionProposalFromBody(value);
		case 'companion_decision':
			return companionDecisionFromBody(value);
		default:
			return null;
	}
}

function itemFromBody(value: unknown): FeedItem | null {
	if (!isRecord(value)) return null;
	if (value.schema_version !== 1) return null;
	const ui_event_id = str(value.ui_event_id);
	const created_at = str(value.created_at);
	const farm_id = str(value.farm_id);
	const plant_id = str(value.plant_id);
	const source_type = str(value.source_type);
	const source_id = str(value.source_id);
	const source_refs = strings(value.source_refs);
	const display_kind = str(value.display_kind);
	const visible_to_roles = strings(value.visible_to_roles);
	const visible_to_agents = bool(value.visible_to_agents);
	const consumable_by_agents = bool(value.consumable_by_agents);
	if (
		ui_event_id === null ||
		created_at === null ||
		farm_id === null ||
		plant_id === null ||
		source_type === null ||
		source_id === null ||
		source_refs === null ||
		display_kind === null ||
		visible_to_roles === null ||
		visible_to_agents === null ||
		consumable_by_agents === null
	) {
		return null;
	}
	const payload = payloadFromBody(display_kind, value.display_payload);
	if (!payload) return null;
	// Render only non-consumable, non-agent-visible presentation events; an
	// unexpected flag value fails closed.
	if (visible_to_agents !== false || consumable_by_agents !== false) return null;
	return {
		schema_version: 1,
		ui_event_id,
		created_at,
		farm_id,
		plant_id,
		source_type,
		source_id,
		source_refs,
		display_kind,
		display_payload: payload,
		visible_to_roles,
		visible_to_agents: visible_to_agents as false,
		consumable_by_agents: consumable_by_agents as false
	};
}

function feedPageFromBody(body: unknown): FeedPage | null {
	if (!isRecord(body)) return null;
	if (!Array.isArray(body.items)) return null;
	const next_cursor = body.next_cursor == null ? null : str(body.next_cursor);
	if (next_cursor === null && body.next_cursor != null) return null;
	const items: FeedItem[] = [];
	for (const raw of body.items) {
		const item = itemFromBody(raw);
		if (!item) return null;
		items.push(item);
	}
	return { items, next_cursor };
}

/**
 * Read one page of the protected Plant Feed
 * (`GET /api/plants/{plant_id}/feed`) through the server-only transport.
 * Authorization, current-Plant status, cursor validation, and the exact
 * `UIFeedEventV1` union remain backend-owned; this consumer only renders the
 * returned union as presentation data. It may trivially translate a passed
 * non-empty cursor into the canonical query parameter but never interprets
 * Feed text as HTML/Markdown/URL/command/action input.
 */
export async function fetchPlantFeed(opts: {
	cookie: string | null;
	plant_id: string;
	cursor?: string | null;
	limit?: number;
}): Promise<FeedPageOutcome> {
	const search = new URLSearchParams();
	if (opts.cursor) search.set('cursor', opts.cursor);
	if (opts.limit != null) search.set('limit', String(opts.limit));
	const query = search.size > 0 ? `?${search.toString()}` : '';
	const result = await backendFetch(
		`/api/plants/${encodeURIComponent(opts.plant_id)}/feed${query}`,
		{ cookie: opts.cookie }
	);
	if (result.unreachable || !result.ok) {
		return { feed: null, error: safeErrorFromResult(result) };
	}
	const feed = feedPageFromBody(result.body);
	if (!feed) {
		return { feed: null, error: FEED_RESPONSE_INVALID };
	}
	return { feed, error: null };
}
