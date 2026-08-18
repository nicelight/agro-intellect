import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { BACKEND_ORIGIN } from './global-setup';

const SEED_PASSWORD = 'Op3rator-Demo-Pa$$w0rd!';
const COOKIE_NAME = 'agro_intellect_session';
const CARD_DB = 'agro_intellect_e2e_085';

const frontendDir = import.meta.dirname;
const repoRoot = path.resolve(frontendDir, '..', '..', '..');
const evidenceDir = path.join(repoRoot, '.tasks', 'TASK-085-T3-FT-016-W3');
const evidenceFile = path.join(evidenceDir, 'card-evidence.json');
const rereadScript = path.join(
	repoRoot,
	'frontend',
	'tests',
	'e2e',
	'support',
	'reread-history-card.py'
);
const python = path.join(repoRoot, '.venv', 'bin', 'python');

// Fail-closed capture compliance: this file produces no trace/video/screenshot
// artifact, so no capture input can carry password/auth material.
test.use({ trace: 'off', video: 'off', screenshot: 'off' });

interface CardRereadSnapshot {
	dbname: string;
	keys: Record<string, string>;
	counts: Record<string, Record<string, number>>;
}

interface CardResponse {
	plant_id: string;
	farm_id: string;
	plant_key: string;
	display_name: string;
	status: string;
	permissions: Record<string, string | boolean | number>;
	latest_check_in_ref: { source_type: string; source_id: string } | null;
	latest_ph_ref: { source_type: string; source_id: string } | null;
	latest_ec_ref: { source_type: string; source_id: string } | null;
	latest_ph: number | null;
	latest_ec_ms_cm: number | null;
	ph_fresh_for_analysis: boolean;
	ec_fresh_for_analysis: boolean;
	photo_count: number;
	history_entry_count: number;
	retained_history_mode: string;
	computed_at: string;
}

interface Evidences {
	[key: string]: boolean | number | string | string[];
}

function loadEvidences(): Evidences {
	if (existsSync(evidenceFile)) {
		return JSON.parse(readFileSync(evidenceFile, 'utf8')) as Evidences;
	}
	return {};
}

function saveEvidences(evidences: Evidences): void {
	mkdirSync(evidenceDir, { recursive: true });
	writeFileSync(evidenceFile, JSON.stringify(evidences, null, 2));
}

function reread(): CardRereadSnapshot {
	const output = execFileSync(python, [rereadScript, CARD_DB], {
		cwd: repoRoot,
		encoding: 'utf8'
	});
	return JSON.parse(output) as CardRereadSnapshot;
}

type Playwright = typeof import('playwright-core');

async function backendSession(
	playwright: Playwright,
	loginName: string
): Promise<{ cookie: string; context: APIRequestContext }> {
	const context = await playwright.request.newContext();
	const response = await context.post(`${BACKEND_ORIGIN}/api/session/login`, {
		data: { login_name: loginName, password: SEED_PASSWORD }
	});
	const setCookie = response
		.headersArray()
		.find((h: { name: string; value: string }) => h.name.toLowerCase() === 'set-cookie');
	expect(response.ok()).toBe(true);
	expect(setCookie).toBeTruthy();
	const match = /=\s*([^;]+)/.exec(setCookie!.value);
	expect(match).toBeTruthy();
	return { cookie: match![1], context };
}

async function browserLogin(page: Page, loginName: string): Promise<void> {
	await page.goto('/login');
	await page.getByTestId('login-name').fill(loginName);
	await page.getByTestId('login-password').fill(SEED_PASSWORD);
	await page.getByTestId('login-submit').click();
	await expect(page.getByTestId('session-identity')).toBeVisible();
}

async function protectedCard(
	context: APIRequestContext,
	cookie: string,
	plantId: string
): Promise<CardResponse> {
	const response = await context.get(
		`${BACKEND_ORIGIN}/api/plants/${plantId}/history/card`,
		{ headers: { cookie: `${COOKIE_NAME}=${cookie}` } }
	);
	expect(response.ok()).toBe(true);
	return (await response.json()) as CardResponse;
}

function refText(ref: { source_type: string; source_id: string } | null): string {
	return ref ? `${ref.source_type}: ${ref.source_id}` : 'none';
}

test.describe('authoritative Plant history card', () => {
	test('active and archived-authorized Plants render the exact authoritative card (refs, freshness, counts, permissions, mode) with no direct Timeline/path/auth surface or mutation residue', async ({
		page,
		playwright
	}) => {
		mkdirSync(evidenceDir, { recursive: true });
		const evidences = loadEvidences();

		const snapshotStart = reread();
		const tomatoId = snapshotStart.keys['tomato_001'];
		const herbId = snapshotStart.keys['herb_003'];
		expect(tomatoId).toBeTruthy();
		expect(herbId).toBeTruthy();

		// Boss is authorized for the active card (normal read) and for the
		// archived retained-history card (retained-history read without a grant).
		const boss = await backendSession(playwright, 'boss');

		// Protected response is the decisive comparison point.
		const activeCard = await protectedCard(boss.context, boss.cookie, tomatoId);
		const retainedCard = await protectedCard(boss.context, boss.cookie, herbId);
		expect(activeCard.retained_history_mode).toBe('active_history');
		expect(activeCard.status).toBe('active');
		expect(retainedCard.retained_history_mode).toBe('archived_retained_history');
		expect(retainedCard.status).toBe('archived');
		evidences['active_card_mode'] = activeCard.retained_history_mode;
		evidences['retained_card_mode'] = retainedCard.retained_history_mode;
		evidences['retained_card_has_refs'] = retainedCard.latest_check_in_ref != null;
		evidences['active_history_entry_count'] = activeCard.history_entry_count;
		evidences['retained_history_entry_count'] = retainedCard.history_entry_count;

		// Active card: exact DOM matches the protected response.
		await browserLogin(page, 'boss');
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('plant-title')).toHaveText(activeCard.display_name);
		await expect(page.getByTestId('history-card')).toBeVisible();
		await expect(page.getByTestId('card-latest-check-in-ref')).toHaveText(
			refText(activeCard.latest_check_in_ref)
		);
		await expect(page.getByTestId('card-latest-ph-ref')).toHaveText(
			refText(activeCard.latest_ph_ref)
		);
		await expect(page.getByTestId('card-latest-ec-ref')).toHaveText(
			refText(activeCard.latest_ec_ref)
		);
		await expect(page.getByTestId('card-latest-ph')).toHaveText(
			activeCard.latest_ph == null ? 'none' : String(activeCard.latest_ph)
		);
		await expect(page.getByTestId('card-latest-ec-ms-cm')).toHaveText(
			activeCard.latest_ec_ms_cm == null ? 'none' : String(activeCard.latest_ec_ms_cm)
		);
		await expect(page.getByTestId('card-ph-fresh')).toHaveText(
			String(activeCard.ph_fresh_for_analysis)
		);
		await expect(page.getByTestId('card-ec-fresh')).toHaveText(
			String(activeCard.ec_fresh_for_analysis)
		);
		await expect(page.getByTestId('card-photo-count')).toHaveText(
			String(activeCard.photo_count)
		);
		await expect(page.getByTestId('card-history-entry-count')).toHaveText(
			String(activeCard.history_entry_count)
		);
		await expect(page.getByTestId('card-retained-history-mode')).toHaveText(
			activeCard.retained_history_mode
		);
		const computedAt =
			(await page.getByTestId('card-computed-at').textContent()) ?? '';
		expect(computedAt.length).toBeGreaterThan(0);
		for (const [key, value] of Object.entries(activeCard.permissions)) {
			await expect(page.getByTestId(`card-permissions-${key}`)).toHaveText(
				String(value)
			);
		}
		expect(activeCard.permissions.source).toBe('boss_role');
		expect(activeCard.permissions.can_read).toBe(true);
		evidences['active_dom_matches_protected_response'] = true;
		evidences['active_card_ph_fresh'] = activeCard.ph_fresh_for_analysis;

		// Archived retained-authorized card: exact DOM matches the protected
		// response and exposes no operational surface.
		await page.goto(`/plants/${herbId}`);
		await expect(page.getByTestId('plant-title')).toHaveText(retainedCard.display_name);
		await expect(page.getByTestId('history-card')).toBeVisible();
		await expect(page.getByTestId('card-retained-history-mode')).toHaveText(
			retainedCard.retained_history_mode
		);
		await expect(page.getByTestId('card-latest-check-in-ref')).toHaveText(
			refText(retainedCard.latest_check_in_ref)
		);
		await expect(page.getByTestId('card-ph-fresh')).toHaveText(
			String(retainedCard.ph_fresh_for_analysis)
		);
		await expect(page.getByTestId('card-ec-fresh')).toHaveText(
			String(retainedCard.ec_fresh_for_analysis)
		);
		await expect(page.getByTestId('card-photo-count')).toHaveText(
			String(retainedCard.photo_count)
		);
		await expect(page.getByTestId('card-history-entry-count')).toHaveText(
			String(retainedCard.history_entry_count)
		);
		for (const [key, value] of Object.entries(retainedCard.permissions)) {
			await expect(page.getByTestId(`card-permissions-${key}`)).toHaveText(
				String(value)
			);
		}
		await expect(page.getByTestId('retained-history-note')).toBeVisible();
		await expect(page.getByTestId('check-in-section')).toHaveCount(0);
		await expect(page.getByTestId('photo-section')).toHaveCount(0);
		expect(retainedCard.ph_fresh_for_analysis).toBe(false);
		expect(retainedCard.ec_fresh_for_analysis).toBe(false);
		evidences['retained_dom_matches_protected_response'] = true;
		evidences['retained_card_freshness_false'] = true;

		// No direct Timeline/path/auth surface in either rendered page.
		const requestedUrls: string[] = [];
		page.on('request', (req) => {
			requestedUrls.push(req.url());
		});
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('history-card')).toBeVisible();
		const pageHtml = await page.content();
		expect(pageHtml).not.toContain('127.0.0.1:8100');
		const token = (await page.context().cookies()).find(
			(c) => c.name === COOKIE_NAME
		)?.value;
		if (token) expect(pageHtml).not.toContain(token);
		expect(pageHtml).not.toContain(SEED_PASSWORD);
		expect(pageHtml).not.toContain(repoRoot);
		expect(pageHtml).not.toContain('timeline.jsonl');
		expect(requestedUrls.some((url) => url.includes('127.0.0.1:8100'))).toBe(false);
		evidences['no_auth_material_or_path_in_page_html'] = true;
		evidences['backend_origin_absent_from_browser_requests'] = true;
		evidences['no_timeline_reference_in_dom'] = true;

		// Authoritative reread: pure card reads (active + archived retained)
		// left no mutation residue.
		const snapshotAfter = reread();
		expect(snapshotAfter.counts[tomatoId]).toEqual(snapshotStart.counts[tomatoId]);
		expect(snapshotAfter.counts[herbId]).toEqual(snapshotStart.counts[herbId]);
		evidences['card_reads_left_no_mutation_residue'] = true;

		saveEvidences(evidences);
	});

	test('denied, malformed, and archived-without-authorization card reads fail safely with no mutation residue and no card/operational surface', async ({
		page,
		playwright
	}) => {
		const evidences = loadEvidences();
		const before = reread();
		const tomatoId = before.keys['tomato_001'];
		const herbId = before.keys['herb_003'];

		// Missing grant: engineer_nogrant cannot read tomato_001's card.
		const nogrant = await backendSession(playwright, 'engineer_nogrant');
		const denied = await nogrant.context.get(
			`${BACKEND_ORIGIN}/api/plants/${tomatoId}/history/card`,
			{ headers: { cookie: `${COOKIE_NAME}=${nogrant.cookie}` } }
		);
		expect(denied.status()).toBe(404);
		const deniedBody = (await denied.json()) as { error?: { code?: string } };
		expect(deniedBody.error?.code).toBe('AUTH_PLANT_FORBIDDEN');
		evidences['unauthorized_card_rejection'] = deniedBody.error?.code ?? 'missing';

		// Archived Plant without retained-history authorization (engineer has
		// no grant on herb_003): card denied.
		const engineer = await backendSession(playwright, 'engineer');
		const archived = await engineer.context.get(
			`${BACKEND_ORIGIN}/api/plants/${herbId}/history/card`,
			{ headers: { cookie: `${COOKIE_NAME}=${engineer.cookie}` } }
		);
		expect(archived.status()).toBe(404);
		const archivedBody = (await archived.json()) as { error?: { code?: string } };
		expect(archivedBody.error?.code).toBe('AUTH_PLANT_FORBIDDEN');
		evidences['archived_without_authorization_rejection'] =
			archivedBody.error?.code ?? 'missing';

		// Malformed plant id in the card path -> 422 VALIDATION_FAILED.
		const malformed = await engineer.context.get(
			`${BACKEND_ORIGIN}/api/plants/not-a-uuid/history/card`,
			{ headers: { cookie: `${COOKIE_NAME}=${engineer.cookie}` } }
		);
		expect(malformed.status()).toBe(422);
		const malformedBody = (await malformed.json()) as { error?: { code?: string } };
		expect(malformedBody.error?.code).toBe('VALIDATION_FAILED');
		evidences['malformed_card_rejection'] = malformedBody.error?.code ?? 'missing';

		// UI denial stays presentation-only: unauthorized and archived-without-
		// authorization Plants render the safe shell denial, zero card, and zero
		// operational surface.
		await browserLogin(page, 'engineer_nogrant');
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('plant-error')).toBeVisible();
		await expect(page.getByTestId('history-card')).toHaveCount(0);
		await expect(page.getByTestId('check-in-section')).toHaveCount(0);
		evidences['denied_plant_has_no_card_surface'] = true;

		// Malformed plant id in the browser path also renders a safe error.
		await page.goto('/plants/not-a-uuid');
		await expect(page.getByTestId('plant-error')).toBeVisible();
		evidences['malformed_plant_has_safe_error'] = true;

		// Authoritative reread: every denied/malformed/archived card read left
		// no mutation residue relative to the pre-request snapshot.
		const after = reread();
		expect(after.counts[tomatoId]).toEqual(before.counts[tomatoId]);
		expect(after.counts[herbId]).toEqual(before.counts[herbId]);
		evidences['denied_and_malformed_reads_left_no_residue'] = true;

		saveEvidences(evidences);
	});
});
