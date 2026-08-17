import { redirect } from '@sveltejs/kit';
import {
	backendFetch,
	safeErrorFromResult,
	sessionTokenFromCookieHeader
} from '$lib/server/backend';
import type { PlantShell, SafeError } from '$lib/session/types';
import type { PageServerLoad } from './$types';

export interface PlantWorkspaceData {
	headers: { 'cache-control': string };
	plant: PlantShell | null;
	error: SafeError | null;
}

export const load: PageServerLoad = async ({ params, request, parent }) => {
	const { session } = await parent();
	if (!session) {
		redirect(303, '/login');
	}

	const cookie = sessionTokenFromCookieHeader(request.headers.get('cookie'));
	const plantId = encodeURIComponent(params.plant_id);

	const result = await backendFetch(`/api/plants/${plantId}`, { cookie });

	if (result.unreachable || !result.ok) {
		return { plant: null, error: safeErrorFromResult(result) };
	}
	if (!result.body || typeof result.body !== 'object' || !('plant_id' in result.body)) {
		return { plant: null, error: safeErrorFromResult(result) };
	}

	const raw = result.body as Record<string, unknown>;
	const plant: PlantShell = {
		plant_id: String(raw.plant_id),
		plant_key: String(raw.plant_key ?? ''),
		display_name: String(raw.display_name ?? ''),
		status: raw.status === 'archived' ? 'archived' : 'active'
	};
	return { plant, error: null };
};