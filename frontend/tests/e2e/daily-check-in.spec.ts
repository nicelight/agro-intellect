import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { BACKEND_ORIGIN } from './global-setup';

const SEED_PASSWORD = 'Op3rator-Demo-Pa$$w0rd!';
const COOKIE_NAME = 'agro_intellect_session';
const CHECK_IN_DB = 'agro_intellect_e2e_083';

const frontendDir = import.meta.dirname;
const repoRoot = path.resolve(frontendDir, '..', '..', '..');
const evidenceDir = path.join(repoRoot, '.tasks', 'TASK-083-T3-FT-016-W3');
const evidenceFile = path.join(evidenceDir, 'checkin-evidence.json');
const rereadScript = path.join(
	repoRoot,
	'frontend',
	'tests',
	'e2e',
	'support',
	'reread-checkins.py'
);
const python = path.join(repoRoot, '.venv', 'bin', 'python');

// Fail-closed capture compliance: this file produces no trace/video/screenshot
// artifact, so no capture input can carry password/auth material.
test.use({ trace: 'off', video: 'off', screenshot: 'off' });

interface RereadCounts {
	plant_key: string;
	check_ins: number;
	measurements: number;
	timeline_checkin_events: number;
}

interface RereadSnapshot {
	dbname: string;
	keys: Record<string, string>;
	counts: Record<string, RereadCounts>;
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

function reread(): RereadSnapshot {
	const output = execFileSync(python, [rereadScript, CHECK_IN_DB], {
		cwd: repoRoot,
		encoding: 'utf8'
	});
	return JSON.parse(output) as RereadSnapshot;
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

async function directCheckIn(
	context: APIRequestContext,
	cookie: string,
	plantId: string,
	body: unknown
): Promise<Awaited<ReturnType<APIRequestContext['post']>>> {
	return context.post(`${BACKEND_ORIGIN}/api/plants/${plantId}/operations/check-ins`, {
		headers: { cookie: `${COOKIE_NAME}=${cookie}` },
		data: body
	});
}

function fieldNames(postData: string | undefined): string[] {
	if (!postData) return [];
	if (postData.includes('name="')) {
		return [...postData.matchAll(/name="([^"]+)"/g)].map((match) => match[1]);
	}
	return [...new URLSearchParams(postData).keys()];
}

const FORBIDDEN_FIELD = /^(farm_id|plant_id|actor|role|permission|freshness|request_id|account_id|authorization|session)/i;

test.describe('daily check-in and observation', () => {
	test('Engineer loads the check-in prompt and submits an exact authorized daily check-in; validation failures are safe and non-mutating', async ({
		page
	}) => {
		const evidences = loadEvidences();

		const snapshotStart = reread();
		const tomatoId = snapshotStart.keys['tomato_001'];
		const herbId = snapshotStart.keys['herb_003'];
		expect(tomatoId).toBeTruthy();
		expect(herbId).toBeTruthy();
		expect(snapshotStart.counts[tomatoId].check_ins).toBe(0);

		// No optimistic state: the workspace never renders a check-in success
		// before the backend returns it.
		await browserLogin(page, 'engineer');
		await page.goto(`/plants/${tomatoId}`);

		await expect(page.getByTestId('plant-title')).toHaveText('Tomato 001');
		await expect(page.getByTestId('check-in-section')).toBeVisible();
		await expect(page.getByTestId('check-in-prompt')).toContainText(
			"Record today's observation"
		);
		await expect(page.getByTestId('check-in-success')).toHaveCount(0);
		evidences['engineer_loaded_check_in_prompt'] = true;

		const actionBodies: string[] = [];
		const requestedUrls: string[] = [];
		page.on('request', (req) => {
			requestedUrls.push(req.url());
			if (req.method() === 'POST' && req.url().includes('?/check-in')) {
				actionBodies.push(req.postData() ?? '');
			}
		});

		// Empty check-in: no observation state and no measurement -> backend
		// CHECK_IN_EMPTY is authoritative and non-mutating.
		await page.getByTestId('check-in-submit').click();
		await expect(page.getByTestId('check-in-error')).toBeVisible();
		await expect(page.getByTestId('check-in-error')).toContainText(
			'Check-in must include an observation or measurement.'
		);
		await expect(page.getByTestId('check-in-success')).toHaveCount(0);
		evidences['empty_check_in_rejected'] = 'CHECK_IN_EMPTY';

		// `observed` with no text -> backend OBSERVATION_TEXT_REQUIRED.
		await page.getByTestId('observation-state-observed').check();
		await page.getByTestId('check-in-submit').click();
		await expect(page.getByTestId('check-in-error')).toContainText(
			'Observation text is required.'
		);
		await expect(page.getByTestId('check-in-success')).toHaveCount(0);
		evidences['observed_without_text_rejected'] = 'OBSERVATION_TEXT_REQUIRED';

		// `no_observation_provided` with text -> backend
		// OBSERVATION_TEXT_FORBIDDEN.
		await page.getByTestId('observation-state-none').check();
		await page.getByTestId('observation-text').fill('should be rejected');
		await page.getByTestId('check-in-submit').click();
		await expect(page.getByTestId('check-in-error')).toContainText(
			'Observation text is not allowed for this observation state.'
		);
		await expect(page.getByTestId('check-in-success')).toHaveCount(0);
		evidences['no_observation_with_text_rejected'] = 'OBSERVATION_TEXT_FORBIDDEN';

		// Authoritative reread: the validation failures changed nothing.
		const snapshotMid = reread();
		expect(snapshotMid.counts[tomatoId].check_ins).toBe(0);
		expect(snapshotMid.counts[tomatoId].measurements).toBe(0);
		expect(snapshotMid.counts[tomatoId].timeline_checkin_events).toBe(0);
		evidences['validation_failures_left_no_residue'] = true;

		// Exact authorized daily check-in / observation succeeds.
		const observationText = 'Leaves look healthy; watering on schedule.';
		await page.getByTestId('observation-state-observed').check();
		await page.getByTestId('observation-text').fill(observationText);
		await page.getByTestId('check-in-submit').click();

		await expect(page.getByTestId('check-in-success')).toBeVisible();
		await expect(page.getByTestId('check-in-state')).toHaveText('observed');
		await expect(page.getByTestId('check-in-text')).toHaveText(observationText);
		await expect(page.getByTestId('check-in-refs')).toHaveText('none');
		const checkInId = (await page.getByTestId('check-in-id').textContent()) ?? '';
		expect(checkInId.length).toBeGreaterThan(0);
		evidences['exact_authorized_check_in_succeeded'] = true;
		evidences['check_in_id'] = checkInId;

		// A later failed request must not leave an optimistic success visible.
		await page.getByTestId('observation-state-observed').check();
		await page.getByTestId('observation-text').fill('');
		await page.getByTestId('check-in-submit').click();
		await expect(page.getByTestId('check-in-error')).toContainText(
			'Observation text is required.'
		);
		await expect(page.getByTestId('check-in-success')).toHaveCount(0);
		evidences['no_optimistic_state_outlives_failed_request'] = true;

		// Authoritative reread: exactly one check-in and one timeline event.
		const snapshotEnd = reread();
		expect(snapshotEnd.counts[tomatoId].check_ins).toBe(1);
		expect(snapshotEnd.counts[tomatoId].timeline_checkin_events).toBe(1);
		evidences['success_persisted_exactly_once'] = true;
		evidences['timeline_event_recorded_once'] = true;

		// Request-body exactness at the browser edge: only registered field
		// names are submitted; no frontend-derived authority field is sent.
		expect(actionBodies.length).toBeGreaterThanOrEqual(4);
		let onlyRegisteredFields = true;
		for (const body of actionBodies) {
			const names = fieldNames(body);
			if (names.some((name) => FORBIDDEN_FIELD.test(name))) {
				onlyRegisteredFields = false;
			}
		}
		const successBody = actionBodies.find((body) => {
			const names = fieldNames(body);
			return names.includes('observation_state') && names.includes('observation_text');
		});
		expect(successBody).toBeTruthy();
		const successNames = fieldNames(successBody);
		expect(successNames).toContain('observation_state');
		expect(successNames).toContain('observation_text');
		evidences['only_registered_fields_sent'] = Boolean(successBody) && onlyRegisteredFields;

		const token = (await page.context().cookies()).find(
			(c) => c.name === COOKIE_NAME
		)?.value;
		const pageHtml = await page.content();
		expect(pageHtml).not.toContain('127.0.0.1:8100');
		if (token) expect(pageHtml).not.toContain(token);
		expect(pageHtml).not.toContain(SEED_PASSWORD);
		evidences['no_auth_material_in_page_html'] = !pageHtml.includes('127.0.0.1:8100');
		evidences['backend_origin_absent_from_browser_requests'] = !requestedUrls.some((url) =>
			url.includes('127.0.0.1:8100')
		);

		saveEvidences(evidences);
	});

	test('permission and archive cases remain safe non-mutating backend failures with no denied-request residue', async ({
		page,
		playwright
	}) => {
		const evidences = loadEvidences();
		const before = reread();
		const tomatoId = before.keys['tomato_001'];
		const herbId = before.keys['herb_003'];

		// Missing grant: Engineer without an access grant on tomato_001.
		const nogrant = await backendSession(playwright, 'engineer_nogrant');
		const denied = await directCheckIn(nogrant.context, nogrant.cookie, tomatoId, {
			observation_state: 'observed',
			observation_text: 'x'
		});
		expect(denied.status()).toBe(404);
		const deniedBody = (await denied.json()) as { error?: { code?: string } };
		expect(deniedBody.error?.code).toBe('AUTH_PLANT_FORBIDDEN');
		evidences['unauthorized_rejection'] = deniedBody.error?.code ?? 'missing';

		// Archived Plant: an authorized Engineer cannot operate herb_003.
		const engineer = await backendSession(playwright, 'engineer');
		const archived = await directCheckIn(engineer.context, engineer.cookie, herbId, {
			observation_state: 'no_observation_provided'
		});
		expect(archived.status()).toBe(404);
		const archivedBody = (await archived.json()) as { error?: { code?: string } };
		expect(archivedBody.error?.code).toBe('AUTH_PLANT_FORBIDDEN');
		evidences['archive_rejection'] = archivedBody.error?.code ?? 'missing';

		// UI denial stays presentation-only: the unauthorized Engineer never
		// reaches a check-in surface for the denied Plant.
		await browserLogin(page, 'engineer_nogrant');
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('plant-error')).toBeVisible();
		await expect(page.getByTestId('check-in-section')).toHaveCount(0);

		// Authoritative reread: the denied requests added no residue relative
		// to the pre-request snapshot (which may include rows confirmed by the
		// success test in the same isolated database).
		const after = reread();
		expect(after.counts[tomatoId].check_ins).toBe(before.counts[tomatoId].check_ins);
		expect(after.counts[herbId].check_ins).toBe(before.counts[herbId].check_ins);
		expect(after.counts[tomatoId].timeline_checkin_events).toBe(
			before.counts[tomatoId].timeline_checkin_events
		);
		expect(after.counts[herbId].timeline_checkin_events).toBe(
			before.counts[herbId].timeline_checkin_events
		);
		evidences['permission_and_archive_left_no_residue'] = true;

		saveEvidences(evidences);
	});

	test('the UI counts Unicode code points and caps 2000, while a bypassing client still gets the authoritative too-long rejection', async ({
		page,
		playwright
	}) => {
		const evidences = loadEvidences();
		const before = reread();
		const tomatoId = before.keys['tomato_001'];

		await browserLogin(page, 'engineer');
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('check-in-section')).toBeVisible();

		// 2100 astral-plane chars become 2000 Unicode code points (each is 2
		// UTF-16 units, so maxlength would not have capped this alone).
		await page.getByTestId('observation-text').fill('😀'.repeat(2100));
		await expect(page.getByTestId('observation-counter')).toHaveText('2000 / 2000');
		const storedCodepoints = await page.evaluate(() => {
			const el = document.querySelector(
				'[data-testid="observation-text"]'
			) as HTMLTextAreaElement;
			return Array.from(el.value).length;
		});
		expect(storedCodepoints).toBe(2000);
		evidences['ui_unicode_codepoint_cap'] = storedCodepoints;

		// A bypassing (non-UI) caller cannot push a 2001-codepoint value past
		// the backend: OBSERVATION_TEXT_TOO_LONG is authoritative.
		const engineer = await backendSession(playwright, 'engineer');
		const tooLong = await directCheckIn(engineer.context, engineer.cookie, tomatoId, {
			observation_state: 'observed',
			observation_text: 'a'.repeat(2001)
		});
		expect(tooLong.status()).toBe(422);
		const tooLongBody = (await tooLong.json()) as { error?: { code?: string } };
		expect(tooLongBody.error?.code).toBe('OBSERVATION_TEXT_TOO_LONG');
		evidences['too_long_rejection'] = tooLongBody.error?.code ?? 'missing';

		// Authoritative reread: the rejected request added no residue.
		const end = reread();
		expect(end.counts[tomatoId].check_ins).toBe(before.counts[tomatoId].check_ins);
		expect(end.counts[tomatoId].timeline_checkin_events).toBe(
			before.counts[tomatoId].timeline_checkin_events
		);
		evidences['too_long_left_no_residue'] = true;

		saveEvidences(evidences);
	});
});
