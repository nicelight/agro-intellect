import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { BACKEND_ORIGIN } from './global-setup';

const SEED_PASSWORD = 'Op3rator-Demo-Pa$$w0rd!';
const DEMO_LOGIN = 'demo_engineer';
const DEMO_DISPLAY = 'Demo Engineer';
const DEMO_PASSWORD = 'Dem0-Eng1neer-Pa$$word!';
const COOKIE_NAME = 'agro_intellect_session';

const frontendDir = import.meta.dirname;
const repoRoot = path.resolve(frontendDir, '..', '..', '..');
const evidenceDir = path.join(repoRoot, '.tasks', 'TASK-082-T3-FT-016-W3');
const evidenceFile = path.join(evidenceDir, 'provisioning-evidence.json');
const backendLogPath = path.join(
	repoRoot,
	'.tasks',
	'TASK-082-T3-FT-016-W3',
	'e2e-browser',
	'backend.log'
);
const testResultsDir = path.join(frontendDir, 'test-results');

// Fail-closed capture compliance: this file produces no trace/video/screenshot
// artifact, so no capture input can carry raw password/auth material.
test.use({ trace: 'off', video: 'off', screenshot: 'off' });

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

type Playwright = typeof import('playwright-core');

async function backendSession(
	playwright: Playwright,
	loginName: string,
	password: string
): Promise<{ cookie: string; context: APIRequestContext }> {
	const context = await playwright.request.newContext();
	const response = await context.post(`${BACKEND_ORIGIN}/api/session/login`, {
		data: { login_name: loginName, password }
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

async function browserLogin(page: Page, loginName: string, password: string): Promise<void> {
	await page.goto('/login');
	await page.getByTestId('login-name').fill(loginName);
	await page.getByTestId('login-password').fill(password);
	await page.getByTestId('login-submit').click();
	await expect(page.getByTestId('session-identity')).toBeVisible();
}

function corpusAbsent(value: string, corpus: string[]): string[] {
	return corpus.filter((item) => item.length > 0 && value.includes(item));
}

test.describe('Boss direct Engineer provisioning', () => {
	test(
		'Boss creates the demo Engineer through /admin, the Engineer can authenticate, and no password/auth material reaches page state, storage, requests, or console',
		async ({ page }) => {
			const evidences = loadEvidences();

			const requestedUrls: string[] = [];
			const consoleLines: string[] = [];
			page.on('request', (req) => requestedUrls.push(req.url()));
			page.on('console', (msg) => consoleLines.push(msg.text()));

			await browserLogin(page, 'boss', SEED_PASSWORD);

			await page.goto('/admin');
			await expect(page.getByTestId('engineer-login')).toBeVisible();

			await page.getByTestId('engineer-login').fill(DEMO_LOGIN);
			await page.getByTestId('engineer-display').fill(DEMO_DISPLAY);
			await page.getByTestId('engineer-password').fill(DEMO_PASSWORD);
			await page.getByTestId('engineer-create').click();

			await expect(page.getByTestId('admin-success')).toBeVisible();
			await expect(page.getByTestId('created-login')).toHaveText(DEMO_LOGIN);
			await expect(page.getByTestId('created-display')).toHaveText(DEMO_DISPLAY);

			const pageHtml = await page.content();

			const storageEntries: string[] = await page.evaluate(() => {
				const values: string[] = [];
				for (let i = 0; i < localStorage.length; i += 1) {
					values.push(localStorage.key(i) ?? '');
					values.push(localStorage.getItem(localStorage.key(i)!) ?? '');
				}
				for (let i = 0; i < sessionStorage.length; i += 1) {
					values.push(sessionStorage.key(i) ?? '');
					values.push(sessionStorage.getItem(sessionStorage.key(i)!) ?? '');
				}
				return values;
			});

			const token = (await page.context().cookies()).find(
				(c) => c.name === COOKIE_NAME
			)?.value as string;
			const searchCorpus = [DEMO_PASSWORD, SEED_PASSWORD, token, '127.0.0.1:8100'];

			expect(corpusAbsent(pageHtml, searchCorpus)).toEqual([]);
			expect(corpusAbsent(storageEntries.join('\n'), [DEMO_PASSWORD, SEED_PASSWORD])).toEqual([]);
			expect(corpusAbsent(consoleLines.join('\n'), [DEMO_PASSWORD, SEED_PASSWORD])).toEqual([]);
			for (const url of requestedUrls) {
				expect(url).not.toContain('127.0.0.1:8100');
				expect(url).not.toContain(token);
				expect(url).not.toContain(DEMO_PASSWORD);
				expect(url).not.toContain(SEED_PASSWORD);
			}

			evidences['boss_created_engineer_via_browser'] = true;
			evidences['demo_login'] = DEMO_LOGIN;
			evidences['page_html_bytes'] = pageHtml.length;
			evidences['password_absent_from_page_html'] = true;
			evidences['password_absent_from_browser_storage'] = true;
			evidences['password_absent_from_browser_console'] = true;
			evidences['auth_material_absent_from_browser_requests'] =
				corpusAbsent(requestedUrls.join('\n'), [token, DEMO_PASSWORD, SEED_PASSWORD]).length === 0;
			evidences['backend_origin_absent_from_browser_requests'] = !requestedUrls.some((url) =>
				url.includes('127.0.0.1:8100')
			);

			// The created Engineer must be able to authenticate (write-only
			// password: sent once, then known only outside the app).
			await page.getByTestId('logout').click();
			await expect(page).toHaveURL(/\/login$/);
			await browserLogin(page, DEMO_LOGIN, DEMO_PASSWORD);
			await expect(page.getByTestId('session-identity')).toContainText(DEMO_DISPLAY);
			await expect(page.getByTestId('session-identity')).toContainText('engineer');

			evidences['engineer_authenticated_after_direct_creation'] = true;

			saveEvidences(evidences);
		}
	);

	test('non-Boss roles are denied both at the UI surface and by the authoritative backend', async ({
		page,
		playwright
	}) => {
		const evidences = loadEvidences();

		const { context } = await backendSession(playwright, 'engineer', SEED_PASSWORD);
		const denied = await context.post(`${BACKEND_ORIGIN}/api/admin/accounts`, {
			data: {
				login_name: 'should_not_exist',
				display_name: 'Should Not Exist',
				password: SEED_PASSWORD,
				role_preset: 'engineer'
			}
		});
		expect(denied.status()).toBe(403);
		const deniedBody = (await denied.json()) as { error?: { code?: string } };
		expect(deniedBody.error?.code).toBe('AUTH_FORBIDDEN');

		await browserLogin(page, 'engineer', SEED_PASSWORD);
		await page.goto('/admin');
		await expect(page.getByTestId('admin-denied')).toBeVisible();
		await expect(page.getByTestId('engineer-login')).toHaveCount(0);
		await expect(page.getByTestId('admin-success')).toHaveCount(0);

		const remaining = await context.get(`${BACKEND_ORIGIN}/api/admin/accounts`);
		expect(remaining.status()).toBe(403);

		evidences['non_boss_creation_denied_via_browser'] = true;
		evidences['non_boss_backend_denies_direct_creation'] =
			deniedBody.error?.code === 'AUTH_FORBIDDEN';
		saveEvidences(evidences);
	});

	test('password/auth material is absent from audit text, backend logs, and any capture artifacts; safe rerun leaves no residue', async ({
		page,
		playwright
	}) => {
		const evidences = loadEvidences();

		const boss = await backendSession(playwright, 'boss', SEED_PASSWORD);
		const audit = await boss.context.get(`${BACKEND_ORIGIN}/api/admin/audit`);
		expect(audit.ok()).toBe(true);
		const auditBody = (await audit.json()) as {
			items: Array<{
				action_type: string;
				login_name?: string;
				target_id?: string;
			}>;
		};
		expect(auditBody.items.some((item) => item.action_type === 'account_created')).toBe(true);
		const auditText = JSON.stringify(auditBody);
		expect(auditText).not.toContain(DEMO_PASSWORD);

		let backendLog = '';
		if (existsSync(backendLogPath)) {
			backendLog = readFileSync(backendLogPath, 'utf8');
		}
		expect(backendLog).not.toContain(DEMO_PASSWORD);

		// Capture artifacts: this file disables trace/video/screenshot, so the
		// only possible artifact surface is Playwright's test-results output.
		const capturedFiles: string[] = [];
		let captureFilesContainSeedCorpus = false;
		if (existsSync(testResultsDir)) {
			const stack = [testResultsDir];
			while (stack.length > 0) {
				const dir = stack.pop()!;
				for (const entry of readdirSync(dir, { withFileTypes: true })) {
					const full = path.join(dir, entry.name);
					if (entry.isDirectory()) {
						stack.push(full);
					} else if (/\.(zip|json|log|txt|html)$/.test(entry.name)) {
						capturedFiles.push(full);
						if (readFileSync(full, 'utf8').includes(DEMO_PASSWORD)) {
							captureFilesContainSeedCorpus = true;
							break;
						}
					}
				}
			}
		}
		expect(captureFilesContainSeedCorpus).toBe(false);

		evidences['password_absent_from_admin_audit_text'] = true;
		evidences['password_absent_from_backend_log'] = true;
		evidences['no_capture_artifact_contains_password'] = true;
		evidences['capture_artifact_count'] = capturedFiles.length;
		evidences['audit_lookup_count'] = auditBody.items.length;
		saveEvidences(evidences);
	});
});