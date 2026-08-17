import type { SafeError } from '$lib/session/types';

export interface AdminMembershipSummary {
	membership_id: string;
	account_id: string;
	farm_id: string;
	role_preset: 'boss' | 'engineer' | 'consultant';
	membership_status: 'active' | 'disabled';
	disabled_at: string | null;
	created_at: string;
	updated_at: string;
}

export interface AdminAccountSummary {
	account_id: string;
	login_name: string;
	display_name: string;
	account_status: 'active' | 'disabled';
	disabled_at: string | null;
	created_at: string;
	updated_at: string;
	membership: AdminMembershipSummary;
}

export interface CreateEngineerOutcome {
	ok: boolean;
	status: number;
	account: AdminAccountSummary | null;
	error: SafeError | null;
}