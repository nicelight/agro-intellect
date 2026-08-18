import { backendFetch, safeErrorFromResult } from '$lib/server/backend';
import type { SafeError } from '$lib/session/types';
import type { PhotoEventRef, PhotoSummary, PhotoUploadOutcome } from './types';

const RESPONSE_INVALID: SafeError = {
	code: 'OPERATION_RESPONSE_INVALID',
	message: 'The service returned an unexpected photo result.'
};

function eventRefFromBody(value: unknown): PhotoEventRef | null {
	if (!value || typeof value !== 'object') return null;
	const raw = value as Record<string, unknown>;
	if (
		typeof raw.timeline_event_id !== 'string' ||
		typeof raw.timeline_ref !== 'string' ||
		typeof raw.event_type !== 'string' ||
		typeof raw.created_at !== 'string'
	) {
		return null;
	}
	return {
		timeline_event_id: raw.timeline_event_id,
		timeline_ref: raw.timeline_ref,
		event_type: raw.event_type,
		created_at: raw.created_at
	};
}

function summaryFromBody(body: unknown): PhotoSummary | null {
	if (!body || typeof body !== 'object') return null;
	const raw = body as Record<string, unknown>;
	if (
		typeof raw.photo_id !== 'string' ||
		typeof raw.farm_id !== 'string' ||
		typeof raw.plant_id !== 'string' ||
		typeof raw.photo_type !== 'string' ||
		typeof raw.captured_at !== 'string' ||
		typeof raw.uploaded_at !== 'string' ||
		typeof raw.content_type !== 'string' ||
		typeof raw.size_bytes !== 'number' ||
		typeof raw.sha256 !== 'string' ||
		typeof raw.original_file_ref !== 'string' ||
		typeof raw.manifest_ref !== 'string' ||
		(raw.check_in_id != null && typeof raw.check_in_id !== 'string') ||
		typeof raw.source_refs !== 'object' ||
		raw.source_refs === null ||
		typeof raw.event_refs !== 'object' ||
		raw.event_refs === null ||
		typeof raw.local_only !== 'boolean' ||
		typeof raw.can_train_on !== 'boolean'
	) {
		return null;
	}

	const eventRefs: Record<string, PhotoEventRef> = {};
	for (const [key, value] of Object.entries(raw.event_refs as Record<string, unknown>)) {
		const ref = eventRefFromBody(value);
		if (!ref) return null;
		eventRefs[key] = ref;
	}

	return {
		photo_id: raw.photo_id,
		farm_id: raw.farm_id,
		plant_id: raw.plant_id,
		photo_type: raw.photo_type,
		captured_at: raw.captured_at,
		uploaded_at: raw.uploaded_at,
		content_type: raw.content_type,
		size_bytes: raw.size_bytes,
		sha256: raw.sha256,
		original_file_ref: raw.original_file_ref,
		manifest_ref: raw.manifest_ref,
		check_in_id: raw.check_in_id == null ? null : raw.check_in_id,
		source_refs: raw.source_refs as Record<string, unknown>,
		event_refs: eventRefs,
		local_only: raw.local_only,
		can_train_on: raw.can_train_on
	};
}

export interface PhotoUploadFile {
	name: string;
	type: string;
	bytes: ArrayBuffer;
}

/**
 * Submit one local photo through the registered Photo Intake HTTP boundary
 * (`POST /api/plants/{plant_id}/photos`) as a server-only multipart upload.
 * Only registered fields (`file`, `photo_type`) are sent; the backend retains
 * file/catalog/checksum/manifest/event/acceptance authority and remains the
 * decisive validator. The browser-selected file crosses this server-only
 * client, never a browser-origin request. Shared safe refs are parsed from the
 * backend response; no filesystem path or auth material is produced here.
 */
export async function submitPhoto(opts: {
	cookie: string | null;
	plant_id: string;
	file: PhotoUploadFile | null;
	photo_type: string | null;
}): Promise<PhotoUploadOutcome> {
	const form = new FormData();
	if (opts.file && opts.file.bytes.byteLength > 0) {
		form.append('file', new Blob([opts.file.bytes], { type: opts.file.type }), opts.file.name);
	}
	if (opts.photo_type && opts.photo_type.trim().length > 0) {
		form.append('photo_type', opts.photo_type);
	}

	const result = await backendFetch(
		`/api/plants/${encodeURIComponent(opts.plant_id)}/photos`,
		{
			method: 'POST',
			cookie: opts.cookie,
			formData: form
		}
	);

	if (result.unreachable || !result.ok) {
		const status = result.status >= 400 && result.status <= 599 ? result.status : 502;
		return { ok: false, status, photo: null, error: safeErrorFromResult(result) };
	}

	const photo = summaryFromBody(result.body);
	if (!photo) {
		return { ok: false, status: 502, photo: null, error: RESPONSE_INVALID };
	}
	return { ok: true, status: result.status, photo, error: null };
}
