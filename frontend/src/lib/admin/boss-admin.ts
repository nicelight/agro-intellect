import { backendFetch, safeErrorFromResult } from '$lib/server/backend';
import type { SafeError } from '$lib/session/types';
import type { AdminAccountSummary, CreateEngineerOutcome } from './types';

const VALIDATION_FAILED: SafeError = {
	code: 'VALIDATION_FAILED',
	message: 'Request validation failed.'
};

const RESPONSE_INVALID: SafeError = {
	code: 'ADMIN_RESPONSE_INVALID',
	message: 'The service returned an unexpected account summary.'
};

function accountFromBody(body: unknown): AdminAccountSummary | null {
	if (!body || typeof body !== 'object') return null;
	const raw = body as Record<string, unknown>;
	if (
		typeof raw.account_id !== 'string' ||
		typeof raw.login_name !== 'string' ||
		typeof raw.display_name !== 'string'
	) {
		return null;
	}
	const membershipRaw = raw.membership;
	if (!membershipRaw || typeof membershipRaw !== 'object') return null;
	const membershipEntry = membershipRaw as Record<string, unknown>;
	return {
		account_id: raw.account_id,
		login_name: raw.login_name,
		display_name: raw.display_name,
		account_status: String(raw.account_status ?? 'active') as 'active' | 'disabled',
		disabled_at: raw.disabled_at === null || raw.disabled_at === undefined ? null : String(raw.disabled_at),
		created_at: String(raw.created_at ?? ''),
		updated_at: String(raw.updated_at ?? ''),
		membership: {
			membership_id: String(membershipEntry.membership_id ?? ''),
			account_id: String(membershipEntry.account_id ?? ''),
			farm_id: String(membershipEntry.farm_id ?? ''),
			role_preset: String(membershipEntry.role_preset ?? '') as 'boss' | 'engineer' | 'consultant',
			membership_status: String(membershipEntry.membership_status ?? '') as 'active' | 'disabled',
			disabled_at:
				membershipEntry.disabled_at === null || membershipEntry.disabled_at === undefined
					? null
					: String(membershipEntry.disabled_at),
			created_at: String(membershipEntry.created_at ?? ''),
			updated_at: String(membershipEntry.updated_at ?? '')
		}
	};
}

/**
 * Create a demo Engineer through the registered Boss Admin action
 * (`POST /api/admin/accounts`). The initial password is sent once and never
 * echoed, stored, or logged by this client; only the safe account summary and
 * stable backend errors flow back to the caller.
 */
export async function createEngineer(opts: {
	cookie: string | null;
	login_name: string;
	display_name: string;
	password: string;
}): Promise<CreateEngineerOutcome> {
	if (!opts.login_name || !opts.display_name || !opts.password) {
		return { ok: false, status: 422, account: null, error: VALIDATION_FAILED };
	}

	const result = await backendFetch('/api/admin/accounts', {
		method: 'POST',
		cookie: opts.cookie,
		json: {
			login_name: opts.login_name,
			display_name: opts.display_name,
			password: opts.password,
			role_preset: 'engineer'
		}
	});

	if (result.unreachable || !result.ok) {
		const status = result.status >= 400 && result.status <= 599 ? result.status : 502;
		return { ok: false, status, account: null, error: safeErrorFromResult(result) };
	}

	const account = accountFromBody(result.body);
	if (!account) {
		return { ok: false, status: 502, account: null, error: RESPONSE_INVALID };
	}
	return { ok: true, status: result.status, account, error: null };
}