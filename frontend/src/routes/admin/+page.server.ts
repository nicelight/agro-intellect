import { fail, redirect } from '@sveltejs/kit';
import { createEngineer } from '$lib/admin/boss-admin';
import { sessionTokenFromCookieHeader } from '$lib/server/backend';
import type { SafeError } from '$lib/session/types';
import type { Actions, PageServerLoad } from './$types';

const VALIDATION_FAILED: SafeError = {
	code: 'VALIDATION_FAILED',
	message: 'Request validation failed.'
};

export const load: PageServerLoad = async (event) => {
	// The root layout already applies `cache-control: no-store` to every page.
	const { session } = await event.parent();
	if (!session) {
		redirect(303, '/login');
	}
	// Presentation visibility only: backend authz remains authoritative.
	return { denied: session.role_preset !== 'boss' };
};

export const actions: Actions = {
	create: async (event) => {
		const form = await event.request.formData();
		const login_name = form.get('login_name');
		const display_name = form.get('display_name');
		const password = form.get('password');
		if (
			typeof login_name !== 'string' ||
			login_name.length === 0 ||
			typeof display_name !== 'string' ||
			display_name.length === 0 ||
			typeof password !== 'string' ||
			password.length === 0
		) {
			return fail(422, { error: VALIDATION_FAILED });
		}

		// The backend session boundary stays authoritative: a non-Boss submit
		// is rejected by POST /api/admin/accounts with AUTH_FORBIDDEN and is
		// surfaced as its stable safe error.
		const cookie = sessionTokenFromCookieHeader(event.request.headers.get('cookie'));
		const outcome = await createEngineer({
			cookie,
			login_name,
			display_name,
			password
		});

		if (!outcome.ok) {
			const status = outcome.status >= 400 && outcome.status <= 599 ? outcome.status : 502;
			return fail(status, { error: outcome.error });
		}

		// The initial password is never returned; only the safe account summary.
		return { account: outcome.account };
	}
};