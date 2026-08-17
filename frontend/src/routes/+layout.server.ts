import { backendFetch, sessionTokenFromCookieHeader } from '$lib/server/backend';
import type { PlantNavItem, SessionIdentity } from '$lib/session/types';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
	event.setHeaders({ 'cache-control': 'no-store' });

	const cookie = sessionTokenFromCookieHeader(event.request.headers.get('cookie'));

	if (!cookie) {
		return { session: null, plants: [] };
	}

	const me = await backendFetch('/api/session/me', { cookie });
	if (!me.ok || !me.body || typeof me.body !== 'object' || !('account_id' in me.body)) {
		return { session: null, plants: [] };
	}

	const raw = me.body as Record<string, unknown>;
	const session: SessionIdentity = {
		account_id: String(raw.account_id),
		display_name: String(raw.display_name ?? ''),
		farm_id: String(raw.farm_id ?? ''),
		role_preset: String(raw.role_preset ?? ''),
		membership_status: String(raw.membership_status ?? ''),
		session_expires_at: String(raw.session_expires_at ?? '')
	};

	const plants: PlantNavItem[] = [];
	const list = await backendFetch('/api/plants', { cookie });
	if (
		list.ok &&
		list.body &&
		typeof list.body === 'object' &&
		'items' in list.body &&
		Array.isArray((list.body as { items: unknown }).items)
	) {
		for (const item of (list.body as { items: Array<Record<string, unknown>> }).items) {
			if (typeof item !== 'object' || item === null) continue;
			plants.push({
				plant_id: String(item.plant_id),
				plant_key: String(item.plant_key ?? ''),
				display_name: String(item.display_name ?? '')
			});
		}
	}

	return { session, plants };
};