import { backendFetch, safeErrorFromResult } from '$lib/server/backend';
import type { SafeError } from '$lib/session/types';
import type {
	PlantCardRef,
	PlantHistoryCard,
	PlantHistoryCardOutcome,
	RetainedHistoryMode
} from './types';

const RESPONSE_INVALID: SafeError = {
	code: 'HISTORY_CARD_RESPONSE_INVALID',
	message: 'The service returned an unexpected Plant card result.'
};

function refFromBody(value: unknown): PlantCardRef | null {
	if (!value || typeof value !== 'object') return null;
	const raw = value as Record<string, unknown>;
	if (typeof raw.source_type !== 'string' || typeof raw.source_id !== 'string') {
		return null;
	}
	return { source_type: raw.source_type, source_id: raw.source_id };
}

function optionalOrNull(value: unknown): string | number | null {
	if (value == null) return null;
	if (typeof value === 'string' || typeof value === 'number') return value;
	return null;
}

function permissionFromBody(value: unknown): Record<string, string | boolean> {
	const permissions: Record<string, string | boolean> = {};
	if (value && typeof value === 'object') {
		for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
			if (typeof item === 'boolean' || typeof item === 'string') {
				permissions[key] = item;
			}
		}
	}
	return permissions;
}

/**
 * Parse and validate the protected Plant History card response. Only the
 * registered safe fields are copied; an unexpected shape is treated as an
 * invalid response and rendered as a fail-closed safe error. Exact
 * refs/freshness/counts/permissions/mode come from the backend projection and
 * are never invented here.
 */
function cardFromBody(body: unknown): PlantHistoryCard | null {
	if (!body || typeof body !== 'object') return null;
	const raw = body as Record<string, unknown>;
	if (
		typeof raw.plant_id !== 'string' ||
		typeof raw.farm_id !== 'string' ||
		typeof raw.plant_key !== 'string' ||
		typeof raw.display_name !== 'string' ||
		(raw.status !== 'active' && raw.status !== 'archived') ||
		(raw.retained_history_mode !== 'active_history' &&
			raw.retained_history_mode !== 'archived_retained_history') ||
		typeof raw.photo_count !== 'number' ||
		typeof raw.history_entry_count !== 'number' ||
		typeof raw.ph_fresh_for_analysis !== 'boolean' ||
		typeof raw.ec_fresh_for_analysis !== 'boolean' ||
		typeof raw.computed_at !== 'string'
	) {
		return null;
	}

	const latestCheckIn = refFromBody(raw.latest_check_in_ref);
	const latestPhRef = refFromBody(raw.latest_ph_ref);
	const latestEcRef = refFromBody(raw.latest_ec_ref);
	if (
		(raw.latest_check_in_ref != null && latestCheckIn === null) ||
		(raw.latest_ph_ref != null && latestPhRef === null) ||
		(raw.latest_ec_ref != null && latestEcRef === null)
	) {
		return null;
	}

	return {
		plant_id: raw.plant_id,
		farm_id: raw.farm_id,
		plant_key: raw.plant_key,
		display_name: raw.display_name,
		status: raw.status as 'active' | 'archived',
		permissions: permissionFromBody(raw.permissions),
		latest_check_in_ref: latestCheckIn,
		latest_ph_ref: latestPhRef,
		latest_ec_ref: latestEcRef,
		latest_ph: optionalOrNull(raw.latest_ph),
		latest_ec_ms_cm: optionalOrNull(raw.latest_ec_ms_cm),
		ph_fresh_for_analysis: raw.ph_fresh_for_analysis,
		ec_fresh_for_analysis: raw.ec_fresh_for_analysis,
		photo_count: raw.photo_count,
		history_entry_count: raw.history_entry_count,
		retained_history_mode: raw.retained_history_mode as RetainedHistoryMode,
		computed_at: raw.computed_at
	};
}

/**
 * Load the Plant History card
 * (`GET /api/plants/{plant_id}/history/card`) through the server-only
 * transport. The card refs/counts/freshness/permissions/mode are presentation
 * data from the owning Plant History projection; authorization, Plant status,
 * and retained-history authority remain backend-owned. A denied or
 * inconsistent card degrades to the stable safe error and never becomes a
 * direct Timeline, path, or data access.
 */
export async function fetchPlantHistoryCard(opts: {
	cookie: string | null;
	plant_id: string;
}): Promise<PlantHistoryCardOutcome> {
	const result = await backendFetch(
		`/api/plants/${encodeURIComponent(opts.plant_id)}/history/card`,
		{ cookie: opts.cookie }
	);
	if (result.unreachable || !result.ok) {
		return { card: null, error: safeErrorFromResult(result) };
	}
	const card = cardFromBody(result.body);
	if (!card) {
		return { card: null, error: RESPONSE_INVALID };
	}
	return { card, error: null };
}
