import { fail, redirect } from '@sveltejs/kit';
import {
	SESSION_COOKIE_NAME,
	backendFetch,
	parseSetCookie,
	safeErrorFromResult,
	sessionTokenFromCookieHeader
} from '$lib/server/backend';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const { session } = await event.parent();
	if (session) {
		redirect(303, '/');
	}
	return {};
};

export const actions: Actions = {
	login: async (event) => {
		const form = await event.request.formData();
		const login_name = form.get('login_name');
		const password = form.get('password');
		if (
			typeof login_name !== 'string' ||
			typeof password !== 'string' ||
			login_name.length === 0 ||
			password.length === 0
		) {
			return fail(422, {
				error: { code: 'VALIDATION_FAILED', message: 'Request validation failed.' }
			});
		}

		const result = await backendFetch('/api/session/login', {
			method: 'POST',
			json: { login_name, password }
		});

		if (result.unreachable || !result.ok) {
			const error = safeErrorFromResult(result);
			const status = result.status >= 400 && result.status <= 599 ? result.status : 502;
			return fail(status, { error });
		}
		if (!result.setCookie) {
			return fail(502, {
				error: { code: 'BACKEND_SET_COOKIE_MISSING', message: 'Could not start the session.' }
			});
		}
		const parsed = parseSetCookie(result.setCookie);
		if (!parsed) {
			return fail(502, {
				error: { code: 'BACKEND_SET_COOKIE_MISSING', message: 'Could not start the session.' }
			});
		}

		event.cookies.set(SESSION_COOKIE_NAME, parsed.value, {
			path: parsed.path || '/',
			httpOnly: true,
			sameSite: 'lax',
			secure: parsed.secure,
			maxAge: parsed.maxAge
		});
		redirect(303, '/');
	},
	logout: async (event) => {
		const cookie = sessionTokenFromCookieHeader(event.request.headers.get('cookie'));
		await backendFetch('/api/session/logout', { method: 'POST', cookie });
		event.cookies.delete(SESSION_COOKIE_NAME, {
			path: '/',
			httpOnly: true,
			sameSite: 'lax',
			secure: false
		});
		redirect(303, '/login');
	}
};