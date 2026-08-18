import { fail, redirect } from '@sveltejs/kit';
import {
	backendFetch,
	safeErrorFromResult,
	sessionTokenFromCookieHeader
} from '$lib/server/backend';
import { fetchCheckInPrompt, submitDailyCheckIn } from '$lib/plant-operations/check-in';
import type { CheckInPrompt, CheckInSummary } from '$lib/plant-operations/types';
import { fetchPlantHistoryCard } from '$lib/plant-history/card';
import type { PlantHistoryCard } from '$lib/plant-history/types';
import { fetchPlantFeed } from '$lib/plant-feed/feed';
import type { FeedPage } from '$lib/plant-feed/types';
import { submitPhoto } from '$lib/photo-intake/upload';
import type { PhotoSummary } from '$lib/photo-intake/types';
import type { PlantShell, SafeError } from '$lib/session/types';
import type { Actions, PageServerLoad } from './$types';

export interface PlantWorkspaceData {
	headers: { 'cache-control': string };
	plant: PlantShell | null;
	error: SafeError | null;
	plantCard: PlantHistoryCard | null;
	plantCardError: SafeError | null;
	checkInPrompt: CheckInPrompt | null;
	checkInPromptError: SafeError | null;
	feed: FeedPage | null;
	feedError: SafeError | null;
}

// Feed pages are bounded (limit 10) so the union stays readable and the UI can
// paginate; the backend remains the sole pagination/order authority.
const FEED_PAGE_LIMIT = 10;

export const load: PageServerLoad = async ({ params, request, parent }) => {
	const { session } = await parent();
	if (!session) {
		redirect(303, '/login');
	}

	const cookie = sessionTokenFromCookieHeader(request.headers.get('cookie'));
	const plantId = encodeURIComponent(params.plant_id);

	const result = await backendFetch(`/api/plants/${plantId}`, { cookie });

	let plant: PlantShell | null = null;
	let shellError: SafeError | null = null;
	if (
		!result.unreachable &&
		result.ok &&
		result.body &&
		typeof result.body === 'object' &&
		'plant_id' in result.body
	) {
		const raw = result.body as Record<string, unknown>;
		plant = {
			plant_id: String(raw.plant_id),
			plant_key: String(raw.plant_key ?? ''),
			display_name: String(raw.display_name ?? ''),
			status: raw.status === 'archived' ? 'archived' : 'active'
		};
	} else {
		shellError = safeErrorFromResult(result);
	}

	// Plant History owns the card projection; the PWA only presents its
	// registered safe fields. The card is also the sole authoritative source
	// for archived retained-history Plants, whose shell read (Plant Management
	// HTTP) is active-only. A denied or inconsistent card degrades to the
	// stable safe error and never becomes a direct Timeline/path data access.
	const cardOutcome = await fetchPlantHistoryCard({ cookie, plant_id: params.plant_id });

	// Plant Operations owns the prompt and check-in command; the PWA only
	// presents this protected GET result. A failing prompt degrades to the
	// stable safe error and never implies an available check-in.
	const promptOutcome =
		plant !== null
			? await fetchCheckInPrompt({ cookie, plant_id: params.plant_id })
			: { prompt: null, error: null };

	// Plant Feed owns the strict UIFeedEventV1 union; the PWA only presents its
	// first page through the server-only client. Authorization, Plant status,
	// lazy roster materialization, and cursor semantics remain backend-owned;
	// a failing page degrades to the stable safe error and never implies
	// approval, publication, or agent context.
	const feedOutcome = await fetchPlantFeed({
		cookie,
		plant_id: params.plant_id,
		limit: FEED_PAGE_LIMIT
	});

	const error =
		plant === null && cardOutcome.card === null
			? (shellError ?? cardOutcome.error)
			: null;

	return {
		plant,
		error,
		plantCard: cardOutcome.card,
		plantCardError: cardOutcome.error,
		checkInPrompt: promptOutcome.prompt,
		checkInPromptError: promptOutcome.error,
		feed: feedOutcome.feed,
		feedError: feedOutcome.error
	};
};

export const actions: Actions = {
	'feed-more': async (event) => {
		const cookie = sessionTokenFromCookieHeader(event.request.headers.get('cookie'));
		if (!cookie) {
			redirect(303, '/login');
		}

		const form = await event.request.formData();
		const cursorRaw = form.get('cursor');
		const cursor = typeof cursorRaw === 'string' && cursorRaw.length > 0 ? cursorRaw : null;

		// Only the opaque Feed cursor is forwarded; Feed text is never sent back
		// to the backend and never becomes a command/agent input. Cursor and
		// authority validation are backend-owned.
		const outcome = await fetchPlantFeed({
			cookie,
			plant_id: event.params.plant_id,
			cursor,
			limit: FEED_PAGE_LIMIT
		});

		if (outcome.error !== null) {
			return fail(502, { feedMoreError: outcome.error });
		}

		return { feed: outcome.feed };
	},
	'check-in': async (event) => {
		const cookie = sessionTokenFromCookieHeader(event.request.headers.get('cookie'));
		if (!cookie) {
			redirect(303, '/login');
		}

		const form = await event.request.formData();
		const observationState = form.get('observation_state');
		const observationText = form.get('observation_text');

		// Only registered Plant Operations field names are forwarded; the
		// backend validates the state enum, text rules, authority, and Plant
		// status and remains the sole command/data owner. No frontend-derived
		// fields are accepted, and no optimistic success is created here.
		const outcome = await submitDailyCheckIn({
			cookie,
			plant_id: event.params.plant_id,
			fields: {
				observation_state:
					typeof observationState === 'string' && observationState.length > 0
						? observationState
						: undefined,
				observation_text:
					typeof observationText === 'string' && observationText.length > 0
						? observationText
						: null
			}
		});

		if (!outcome.ok) {
			const status = outcome.status >= 400 && outcome.status <= 599 ? outcome.status : 502;
			return fail(status, { error: outcome.error });
		}

		return { checkIn: outcome.check_in as CheckInSummary };
	},
	'add-photo': async (event) => {
		const cookie = sessionTokenFromCookieHeader(event.request.headers.get('cookie'));
		if (!cookie) {
			redirect(303, '/login');
		}

		const form = await event.request.formData();
		const filePart = form.get('file');
		const photoTypePart = form.get('photo_type');

		// Only the registered `file` and `photo_type` fields are forwarded.
		// The browser `required`/`accept` attributes are advisory only; the
		// backend validates content type, size, photo_type enum, authority, and
		// Plant status and remains the decisive acceptance owner. No optimistic
		// acceptance, checksum, manifest, or path is computed here.
		const isFileLike =
			filePart !== null &&
			typeof filePart === 'object' &&
			'arrayBuffer' in filePart &&
			typeof (filePart as { arrayBuffer?: unknown }).arrayBuffer === 'function' &&
			typeof (filePart as { name?: unknown }).name === 'string' &&
			typeof (filePart as { type?: unknown }).type === 'string';
		const file =
			isFileLike && (filePart as { size: number }).size > 0
				? {
						name: (filePart as { name: string }).name,
						type: (filePart as { type: string }).type,
						bytes: await (filePart as { arrayBuffer(): Promise<ArrayBuffer> }).arrayBuffer()
					}
				: null;
		const photoType =
			typeof photoTypePart === 'string' && photoTypePart.trim().length > 0
				? photoTypePart
				: null;

		const outcome = await submitPhoto({
			cookie,
			plant_id: event.params.plant_id,
			file,
			photo_type: photoType
		});

		if (!outcome.ok) {
			const status = outcome.status >= 400 && outcome.status <= 599 ? outcome.status : 502;
			return fail(status, { photoError: outcome.error });
		}

		return { photo: outcome.photo as PhotoSummary };
	}
};
