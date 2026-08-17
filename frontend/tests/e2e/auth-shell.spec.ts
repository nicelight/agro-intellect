import {
	test,
	expect,
	type APIRequestContext,
	type Page
} from '@playwright/test';
import { writeFileSync } from 'node:fs';
import { BACKEND_ORIGIN } from './global-setup';

const PASSWORD = 'Op3rator-Demo-Pa$$w0rd!';
const COOKIE_NAME = 'agro_intellect_session';

interface BackendSession {
	cookie: string;
	context: APIRequestContext;
}

async function backendSession(
	playwright: typeof import('playwright-core'),
	loginName: string
): Promise<BackendSession> {
	const context = await playwright.request.newContext();
	const response = await context.post(`${BACKEND_ORIGIN}/api/session/login`, {
		data: { login_name: loginName, password: PASSWORD }
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
	await page.getByTestId('login-password').fill(PASSWORD);
	await page.getByTestId('login-submit').click();
	await expect(page.getByTestId('session-identity')).toBeVisible();
}

test.describe('authorized session and Plant shell', () => {
	test('Boss sees admin navigation and every active Plant from the backend list', async ({
		page
	}) => {
		await browserLogin(page, 'boss');

		await expect(page.getByTestId('session-identity')).toContainText('Boss Operator');
		await expect(page.getByTestId('admin-nav')).toBeVisible();
		await expect(page.getByTestId('plant-nav-tomato_001')).toBeVisible();
		await expect(page.getByTestId('plant-nav-pepper_002')).toBeVisible();
		await expect(page.getByTestId('plant-nav-herb_003')).toHaveCount(0);
	});

	test('Engineer sees only the granted active Plant and no admin navigation', async ({
		page,
		playwright
	}) => {
		const { context } = await backendSession(playwright, 'engineer');
		const { items } = await (await context.get(`${BACKEND_ORIGIN}/api/plants`)).json();
		expect(items.map((item: { plant_key: string }) => item.plant_key)).toEqual([
			'tomato_001'
		]);
		const tomatoId = items[0].plant_id;

		await browserLogin(page, 'engineer');
		await expect(page.getByTestId('admin-nav')).toHaveCount(0);
		await expect(page.getByTestId('plant-nav-tomato_001')).toBeVisible();
		await expect(page.getByTestId('plant-nav-pepper_002')).toHaveCount(0);

		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('plant-title')).toHaveText('Tomato 001');
		await expect(page.getByTestId('plant-key')).toHaveText('tomato_001');
	});

	test('absent grant denies the Plant workspace with a safe backend error', async ({
		page,
		playwright
	}) => {
		const { context } = await backendSession(playwright, 'engineer_nogrant');
		const { items } = await (await context.get(`${BACKEND_ORIGIN}/api/plants`)).json();
		expect(items).toEqual([]);

		await browserLogin(page, 'engineer_nogrant');
		await expect(page.getByTestId('no-plants')).toBeVisible();

		const denied = await context.get(
			`${BACKEND_ORIGIN}/api/plants/00000000-0000-0000-0000-000000000000`
		);
		expect(denied.status()).toBe(404);

		await page.goto('/plants/00000000-0000-0000-0000-000000000000');
		await expect(page.getByTestId('plant-error')).toBeVisible();
		await expect(page.getByTestId('plant-error')).toContainText('not available');
		await expect(page.getByTestId('plant-title')).toHaveCount(0);
	});

	test('revoked grant denies the Plant workspace and matches backend denial', async ({
		page,
		playwright
	}) => {
		const boss = await backendSession(playwright, 'boss');
		const { items } = await (await boss.context.get(`${BACKEND_ORIGIN}/api/plants`)).json();
		const tomatoId = items.find((item: { plant_key: string }) => item.plant_key === 'tomato_001')
			.plant_id;

		const revoked = await backendSession(playwright, 'engineer_revoked');
		const denied = await revoked.context.get(`${BACKEND_ORIGIN}/api/plants/${tomatoId}`);
		expect(denied.status()).toBe(404);

		await browserLogin(page, 'engineer_revoked');
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('plant-error')).toBeVisible();
	});

	test('Consultant has no Plant and no admin navigation', async ({ page, playwright }) => {
		const { context } = await backendSession(playwright, 'consultant');
		const { items } = await (await context.get(`${BACKEND_ORIGIN}/api/plants`)).json();
		expect(items).toEqual([]);

		await browserLogin(page, 'consultant');
		await expect(page.getByTestId('admin-nav')).toHaveCount(0);
		await expect(page.getByTestId('no-plants')).toBeVisible();
	});

	test('disabled account login shows the stable safe error', async ({ page }) => {
		await page.goto('/login');
		await page.getByTestId('login-name').fill('boss_disabled');
		await page.getByTestId('login-password').fill(PASSWORD);
		await page.getByTestId('login-submit').click();
		await expect(page.getByTestId('login-error')).toContainText('Account is disabled.');
	});

	test('disabled membership login shows the stable safe error', async ({ page }) => {
		await page.goto('/login');
		await page.getByTestId('login-name').fill('engineer_disabledmem');
		await page.getByTestId('login-password').fill(PASSWORD);
		await page.getByTestId('login-submit').click();
		await expect(page.getByTestId('login-error')).toContainText(
			'Farm membership is disabled.'
		);
	});

	test('missing membership login shows the stable safe error', async ({ page }) => {
		await page.goto('/login');
		await page.getByTestId('login-name').fill('noseat');
		await page.getByTestId('login-password').fill(PASSWORD);
		await page.getByTestId('login-submit').click();
		await expect(page.getByTestId('login-error')).toContainText(
			'Farm membership is required.'
		);
	});

	test('logout clears the cookie and discards transient session state', async ({
		page,
		context
	}) => {
		await browserLogin(page, 'boss');
		await expect(page.getByTestId('session-identity')).toBeVisible();

		await page.getByTestId('logout').click();

		await expect(page).toHaveURL(/\/login$/);
		const sessionCookie = (await context.cookies()).find(
			(c) => c.name === COOKIE_NAME
		);
		expect(sessionCookie).toBeUndefined();
		await expect(page.getByTestId('sign-in-link')).toBeVisible();

		await page.goto('/');
		await expect(page).toHaveURL(/\/login$/);
	});

	test('invalid session falls back to the safe login surface without a crash', async ({
		page,
		context,
		playwright
	}) => {
		await browserLogin(page, 'engineer');

		const sessionCookie = (await context.cookies()).find(
			(c) => c.name === COOKIE_NAME
		);
		expect(sessionCookie).toBeTruthy();
		const requestContext = await playwright.request.newContext();
		const revoked = await requestContext.post(`${BACKEND_ORIGIN}/api/session/logout`, {
			headers: { cookie: `${COOKIE_NAME}=${sessionCookie!.value}` }
		});
		expect(revoked.status()).toBe(204);

		await page.goto('/');
		await expect(page).toHaveURL(/\/login$/);
		await expect(page.getByTestId('sign-in-link')).toBeVisible();
	});

	test('transport forwards only through the server: no backend origin, token, or secret in browser transport state', async ({
		page,
		context
	}) => {
		const requestedUrls: string[] = [];
		const postBodies: string[] = [];
		page.on('request', (req) => {
			requestedUrls.push(req.url());
			if (req.method() === 'POST') {
				postBodies.push(req.postData() ?? '');
			}
		});

		await browserLogin(page, 'boss');
		const token = (await context.cookies()).find((c) => c.name === COOKIE_NAME)!.value;

		await page.goto('/');
		const homeHtml = await page.content();
		const plantHref =
			(await page.getByTestId('plant-nav-tomato_001').getAttribute('href')) ?? '';
		const tomatoId = plantHref.split('/').pop();
		await page.goto(`/plants/${tomatoId}`);
		const plantHtml = await page.content();

		expect(requestedUrls).not.toEqual([]);
		for (const url of requestedUrls) {
			expect(url).not.toContain('127.0.0.1:8100');
			expect(url).not.toContain(token);
			expect(url).not.toContain(PASSWORD);
		}
		for (const body of postBodies) {
			expect(body).not.toContain(token);
			expect(body).not.toContain('127.0.0.1:8100');
		}

		for (const html of [homeHtml, plantHtml]) {
			expect(html).not.toContain('127.0.0.1:8100');
			expect(html).not.toContain(token);
			expect(html).not.toContain(PASSWORD);
			expect(html).not.toContain('Authorization');
		}

		await expect(page.getByTestId('plant-title')).toHaveText('Tomato 001');

		writeFileSync(
			`${import.meta.dirname}/../../../.tasks/TASK-081-T3-FT-016-W2/auth-shell-transport-evidence.json`,
			JSON.stringify(
				{
					backend_origin: BACKEND_ORIGIN,
					checked_corpus: [
						'backend-origin',
						'raw-session-token',
						'password',
						'Authorization-header-key'
					],
					page_html_bytes: homeHtml.length + plantHtml.length,
					browser_request_count: requestedUrls.length,
					no_backend_origin_in_browser_requests: true,
					no_raw_token_in_browser_requests: true,
					no_password_in_browser_requests: true,
					no_backend_origin_in_html: true,
					no_raw_token_in_html: true
				},
				null,
				2
			)
		);
	});

	test('protected SSR documents are served with no-store', async ({ page }) => {
		const noStore: Record<string, string> = {};
		page.on('response', (response) => {
			if (response.request().isNavigationRequest() && response.status() === 200) {
				noStore[response.url()] = response.headers()['cache-control'] ?? '';
			}
		});

		await browserLogin(page, 'boss');
		await page.goto('/');

		const plantHref =
			(await page.getByTestId('plant-nav-tomato_001').getAttribute('href')) ?? '/plants/unknown';
		const tomatoId = plantHref.split('/').pop();
		await page.goto(`/plants/${tomatoId}`);

		await expect(page.getByTestId('plant-title')).toHaveText('Tomato 001');

		for (const header of Object.values(noStore)) {
			expect(header.toLowerCase()).toContain('no-store');
		}
	});
});