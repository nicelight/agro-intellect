import { backendFetch, safeErrorFromResult } from '$lib/server/backend';
import type { SafeError } from '$lib/session/types';
import type {
	CheckInOutcome,
	CheckInPrompt,
	CheckInSummary,
	ObservationState,
	PromptOutcome
} from './types';

const RESPONSE_INVALID: SafeError = {
	code: 'OPERATION_RESPONSE_INVALID',
	message: 'The service returned an unexpected check-in result.'
};

function promptFromBody(body: unknown): CheckInPrompt | null {
	if (!body || typeof body !== 'object') return null;
	const raw = body as Record<string, unknown>;
	if (typeof raw.plant_id !== 'string' || typeof raw.prompt !== 'string') return null;
	return {
		plant_id: raw.plant_id,
		prompt: raw.prompt,
		photo_upload_available: raw.photo_upload_available === true
	};
}

function summaryFromBody(body: unknown): CheckInSummary | null {
	if (!body || typeof body !== 'object') return null;
	const raw = body as Record<string, unknown>;
	const state = raw.observation_state;
	if (
		typeof raw.check_in_id !== 'string' ||
		typeof raw.plant_id !== 'string' ||
		(state !== 'observed' && state !== 'no_observation_provided') ||
		typeof raw.observed_at !== 'string' ||
		typeof raw.recorded_at !== 'string' ||
		typeof raw.photo_upload_available !== 'boolean' ||
		typeof raw.measurement_refs !== 'object' ||
		raw.measurement_refs === null ||
		typeof raw.event_refs !== 'object' ||
		raw.event_refs === null ||
		typeof raw.freshness !== 'object' ||
		raw.freshness === null
	) {
		return null;
	}

	const freshnessRaw = raw.freshness as Record<string, unknown>;
	const freshness = {
		latest_ph_ref: freshnessRaw.latest_ph_ref == null ? null : String(freshnessRaw.latest_ph_ref),
		latest_ec_ref: freshnessRaw.latest_ec_ref == null ? null : String(freshnessRaw.latest_ec_ref),
		latest_ph: freshnessRaw.latest_ph == null ? null : Number(freshnessRaw.latest_ph),
		latest_ec_ms_cm:
			freshnessRaw.latest_ec_ms_cm == null ? null : Number(freshnessRaw.latest_ec_ms_cm),
		ph_fresh_for_analysis: freshnessRaw.ph_fresh_for_analysis === true,
		ec_fresh_for_analysis: freshnessRaw.ec_fresh_for_analysis === true,
		ph_fresh_for_approval_input: freshnessRaw.ph_fresh_for_approval_input === true,
		ec_fresh_for_approval_input: freshnessRaw.ec_fresh_for_approval_input === true,
		missing_or_stale: Array.isArray(freshnessRaw.missing_or_stale)
			? freshnessRaw.missing_or_stale.map((entry) => String(entry))
			: [],
		computed_at: String(freshnessRaw.computed_at ?? '')
	};

	return {
		check_in_id: raw.check_in_id,
		plant_id: raw.plant_id,
		observation_state: state as ObservationState,
		observation_text: raw.observation_text == null ? null : String(raw.observation_text),
		observed_at: raw.observed_at,
		recorded_at: raw.recorded_at,
		measurement_refs: (raw.measurement_refs as unknown[]).map((entry) => String(entry)),
		event_refs: raw.event_refs as Record<string, Record<string, unknown>>,
		freshness,
		photo_upload_available: raw.photo_upload_available
	};
}

/**
 * Load the Plant Operations check-in prompt
 * (`GET /api/plants/{plant_id}/operations/check-in-prompt`). The prompt text is
 * presentation-only; authorization and Plant status remain backend-owned.
 */
export async function fetchCheckInPrompt(opts: {
	cookie: string | null;
	plant_id: string;
}): Promise<PromptOutcome> {
	const result = await backendFetch(
		`/api/plants/${encodeURIComponent(opts.plant_id)}/operations/check-in-prompt`,
		{ cookie: opts.cookie }
	);
	if (result.unreachable || !result.ok) {
		return { prompt: null, error: safeErrorFromResult(result) };
	}
	const prompt = promptFromBody(result.body);
	if (!prompt) {
		return { prompt: null, error: RESPONSE_INVALID };
	}
	return { prompt, error: null };
}

export interface DailyCheckInFields {
	observation_state?: string;
	observation_text?: string | null;
}

/**
 * Submit the daily check-in / observation shape through the registered Plant
 * Operations command (`POST /api/plants/{plant_id}/operations/check-ins`).
 * Only registered field names are sent; value rules (state enum, text rules,
 * authority, Plant status) remain backend-owned and are surfaced verbatim as
 * stable safe errors. No optimistic success is produced here.
 */
export async function submitDailyCheckIn(opts: {
	cookie: string | null;
	plant_id: string;
	fields: DailyCheckInFields;
}): Promise<CheckInOutcome> {
	const body: Record<string, unknown> = {};
	if (opts.fields.observation_state !== undefined) {
		body.observation_state = opts.fields.observation_state;
	}
	if (opts.fields.observation_text != null && opts.fields.observation_text.trim().length > 0) {
		body.observation_text = opts.fields.observation_text;
	}

	const result = await backendFetch(
		`/api/plants/${encodeURIComponent(opts.plant_id)}/operations/check-ins`,
		{
			method: 'POST',
			cookie: opts.cookie,
			json: body
		}
	);

	if (result.unreachable || !result.ok) {
		const status = result.status >= 400 && result.status <= 599 ? result.status : 502;
		return { ok: false, status, check_in: null, error: safeErrorFromResult(result) };
	}

	const check_in = summaryFromBody(result.body);
	if (!check_in) {
		return { ok: false, status: 502, check_in: null, error: RESPONSE_INVALID };
	}
	return { ok: true, status: result.status, check_in, error: null };
}
