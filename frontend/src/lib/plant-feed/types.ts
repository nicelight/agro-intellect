import type { SafeError } from '$lib/session/types';

// Exact `UIFeedEventV1` union types mirrored from the UI Feed contract. Every
// variant is discriminated by `display_payload.payload_kind`; the server-only
// client fails closed on any unknown/invalid shape so the PWA never renders
// unregistered data with implied semantics.

export type RosterPayload = {
	payload_kind: 'agent_introduction';
	agent_id: string;
	display_name: string;
	competence_summary: string;
	introduction_text: string;
	roster_version: number;
};

export type AgentMessagePayload = {
	payload_kind: 'agent_message';
	agent_id: string;
	candidate_claim_type: string;
	quoted_text: string;
};

export type BlockNoticePayload = {
	payload_kind: 'block_notice';
	notice_code: string;
	text: string;
};

export type SafetyEvidenceItem = {
	status: 'fresh' | 'stale' | 'missing';
	source_ref: string | null;
	measured_at: string | null;
};

export type SafetyApprovalInputFreshness = {
	purpose: 'approval_input';
	window_hours: 2;
	computed_at: string;
	ph: SafetyEvidenceItem;
	ec: SafetyEvidenceItem;
};

export type SafetyStatusPayload = {
	payload_kind: 'safety_status';
	decision_ref: string;
	classification_ref: string;
	action_kind: string;
	safety_status: string;
	reason_code: string;
	summary_text: string;
	evidence_refs: string[];
	approval_input_freshness: SafetyApprovalInputFreshness | null;
	expires_at: string | null;
};

export type CompanionAttentionPayload = {
	payload_kind: 'companion_attention';
	attention_ref: string;
	issue_ref: string;
	summary_text: string;
};

export type CompanionProposalPayload = {
	payload_kind: 'companion_proposal';
	proposal_ref: string;
	issue_ref: string;
	proposal_state: string;
	summary_text: string;
};

export type CompanionDecisionPayload = {
	payload_kind: 'companion_decision';
	decision_record_ref: string;
	issue_ref: string;
	proposal_ref: string;
	decision_summary: string;
	safety_gate_authority: 'not_granted';
};

export type FeedPayload =
	| RosterPayload
	| AgentMessagePayload
	| BlockNoticePayload
	| SafetyStatusPayload
	| CompanionAttentionPayload
	| CompanionProposalPayload
	| CompanionDecisionPayload;

export interface FeedItem {
	schema_version: 1;
	ui_event_id: string;
	created_at: string;
	farm_id: string;
	plant_id: string;
	source_type: string;
	source_id: string;
	source_refs: string[];
	display_kind: string;
	display_payload: FeedPayload;
	visible_to_roles: string[];
	visible_to_agents: false;
	consumable_by_agents: false;
}

export interface FeedPage {
	items: FeedItem[];
	next_cursor: string | null;
}

export interface FeedPageOutcome {
	feed: FeedPage | null;
	error: SafeError | null;
}
