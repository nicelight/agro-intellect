import type { SafeError } from '$lib/session/types';

export interface PhotoEventRef {
	timeline_event_id: string;
	timeline_ref: string;
	event_type: string;
	created_at: string;
}

export interface PhotoSummary {
	photo_id: string;
	farm_id: string;
	plant_id: string;
	photo_type: string;
	captured_at: string;
	uploaded_at: string;
	content_type: string;
	size_bytes: number;
	sha256: string;
	original_file_ref: string;
	manifest_ref: string;
	check_in_id: string | null;
	source_refs: Record<string, unknown>;
	event_refs: Record<string, PhotoEventRef>;
	local_only: boolean;
	can_train_on: boolean;
}

export interface PhotoUploadOutcome {
	ok: boolean;
	status: number;
	photo: PhotoSummary | null;
	error: SafeError | null;
}

export const ACCEPTED_PHOTO_TYPES = [
	'whole_plant',
	'leaf_closeup',
	'roots',
	'problem_area',
	'other'
] as const;
