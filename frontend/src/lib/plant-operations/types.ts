import type { SafeError } from '$lib/session/types';

export type ObservationState = 'observed' | 'no_observation_provided';

export interface CheckInPrompt {
	plant_id: string;
	prompt: string;
	photo_upload_available: boolean;
}

export interface PromptOutcome {
	prompt: CheckInPrompt | null;
	error: SafeError | null;
}

export interface FreshnessProjection {
	latest_ph_ref: string | null;
	latest_ec_ref: string | null;
	latest_ph: number | null;
	latest_ec_ms_cm: number | null;
	ph_fresh_for_analysis: boolean;
	ec_fresh_for_analysis: boolean;
	ph_fresh_for_approval_input: boolean;
	ec_fresh_for_approval_input: boolean;
	missing_or_stale: string[];
	computed_at: string;
}

export interface CheckInSummary {
	check_in_id: string;
	plant_id: string;
	observation_state: ObservationState;
	observation_text: string | null;
	observed_at: string;
	recorded_at: string;
	measurement_refs: string[];
	event_refs: Record<string, Record<string, unknown>>;
	freshness: FreshnessProjection;
	photo_upload_available: boolean;
}

export interface CheckInOutcome {
	ok: boolean;
	status: number;
	check_in: CheckInSummary | null;
	error: SafeError | null;
}
