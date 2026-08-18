import type { SafeError } from '$lib/session/types';

export type RetainedHistoryMode = 'active_history' | 'archived_retained_history';

export interface PlantCardRef {
	source_type: string;
	source_id: string;
}

export interface PlantHistoryCard {
	plant_id: string;
	farm_id: string;
	plant_key: string;
	display_name: string;
	status: 'active' | 'archived';
	permissions: Record<string, string | boolean>;
	latest_check_in_ref: PlantCardRef | null;
	latest_ph_ref: PlantCardRef | null;
	latest_ec_ref: PlantCardRef | null;
	latest_ph: string | number | null;
	latest_ec_ms_cm: string | number | null;
	ph_fresh_for_analysis: boolean;
	ec_fresh_for_analysis: boolean;
	photo_count: number;
	history_entry_count: number;
	retained_history_mode: RetainedHistoryMode;
	computed_at: string;
}

export interface PlantHistoryCardOutcome {
	card: PlantHistoryCard | null;
	error: SafeError | null;
}
