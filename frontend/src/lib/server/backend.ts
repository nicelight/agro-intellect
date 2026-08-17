import { env } from '$env/dynamic/private';
import type { SafeError } from '$lib/session/types';

export const SESSION_COOKIE_NAME = 'agro_intellect_session';

const DEFAULT_BACKEND_ORIGIN = 'http://127.0.0.1:8000';

export const BACKEND_UNAVAILABLE: SafeError = {
	code: 'BACKEND_UNAVAILABLE',
	message: 'The service could not be reached. Retry later.'
};

const VALIDATION_FAILED: SafeError = {
	code: 'VALIDATION_FAILED',
	message: 'Request validation failed.'
};

export interface BackendResult {
	status: number;
	ok: boolean;
	unreachable: boolean;
	setCookie: string | null;
	body: unknown;
	safeError: SafeError;
}

function isLoopbackHost(hostname: string): boolean {
	const normalized = hostname.toLowerCase().replace(/\.$/, '');
	return (
		normalized === 'localhost' ||
		normalized === '127.0.0.1' ||
		normalized === '::1' ||
		normalized === '[::1]'
	);
}

export function backendOrigin(): string {
	const configured = env.BACKEND_ORIGIN?.trim();
	if (!configured) return DEFAULT_BACKEND_ORIGIN;
	try {
		const url = new URL(configured);
		if (url.protocol !== 'http:' && url.protocol !== 'https:') {
			throw new Error('invalid protocol');
		}
		if (!isLoopbackHost(url.hostname)) {
			throw new Error('non-loopback host');
		}
		return configured.replace(/\/+$/, '');
	} catch {
		throw new Error(
			'BACKEND_ORIGIN must be a validated loopback origin (localhost/127.0.0.1/[::1]).'
		);
	}
}

export function sessionTokenFromCookieHeader(cookieHeader: string | null): string | null {
	if (!cookieHeader) return null;
	for (const part of cookieHeader.split(';')) {
		const eq = part.indexOf('=');
		if (eq < 0) continue;
		const name = part.slice(0, eq).trim();
		if (name !== SESSION_COOKIE_NAME) continue;
		const value = part.slice(eq + 1).trim();
		return value ? value : null;
	}
	return null;
}

export function safeErrorFromBody(status: number, body: unknown): SafeError {
	if (
		body &&
		typeof body === 'object' &&
		'error' in body &&
		typeof (body as { error: unknown }).error === 'object'
	) {
		const error = (body as { error?: { code?: unknown; message?: unknown } }).error;
		if (
			error &&
			typeof error.code === 'string' &&
			error.code.length > 0 &&
			typeof error.message === 'string' &&
			error.message.length > 0
		) {
			return { code: error.code, message: error.message };
		}
	}
	return status >= 500 || status === 0 ? BACKEND_UNAVAILABLE : VALIDATION_FAILED;
}

export function safeErrorFromResult(result: BackendResult): SafeError {
	if (result.unreachable) return BACKEND_UNAVAILABLE;
	return safeErrorFromBody(result.status, result.body);
}

export interface ParsedCookie {
	value: string;
	maxAge: number | undefined;
	path: string | undefined;
	secure: boolean;
}

export function parseSetCookie(header: string): ParsedCookie | null {
	const parts = header.split(';').map((part) => part.trim());
	const nameValue = parts.shift();
	if (!nameValue) return null;
	const eq = nameValue.indexOf('=');
	if (eq <= 0) return null;
	const value = nameValue.slice(eq + 1);
	if (!value || value === '""') return null;

	let maxAge: number | undefined;
	let cookiePath: string | undefined;
	let secure = false;
	for (const part of parts) {
		if (/^max-age=/i.test(part)) {
			const parsed = Number.parseInt(part.slice('max-age='.length), 10);
			if (Number.isInteger(parsed)) maxAge = parsed;
		} else if (/^path=/i.test(part)) {
			cookiePath = part.slice('path='.length);
		} else if (/^secure/i.test(part)) {
			secure = true;
		}
	}
	return { value, maxAge, path: cookiePath, secure };
}

export interface BackendFetchOptions {
	method?: 'GET' | 'POST';
	cookie?: string | null;
	json?: unknown;
}

export async function backendFetch(
	path: string,
	options: BackendFetchOptions = {}
): Promise<BackendResult> {
	const headers = new Headers();
	if (options.cookie) {
		headers.set('cookie', `${SESSION_COOKIE_NAME}=${options.cookie}`);
	}
	if (options.json !== undefined) {
		headers.set('content-type', 'application/json');
	}

	let response: Response;
	try {
		response = await fetch(`${backendOrigin()}${path}`, {
			method: options.method ?? 'GET',
			headers,
			body: options.json !== undefined ? JSON.stringify(options.json) : undefined,
			redirect: 'manual'
		});
	} catch {
		return { status: 0, ok: false, unreachable: true, setCookie: null, body: null, safeError: BACKEND_UNAVAILABLE };
	}

	let body: unknown = null;
	try {
		body = await response.json();
	} catch {
		body = null;
	}
	const setCookie = response.headers.get('set-cookie');

	return {
		status: response.status,
		ok: response.ok,
		unreachable: false,
		setCookie,
		body,
		safeError: safeErrorFromBody(response.status, body)
	};
}