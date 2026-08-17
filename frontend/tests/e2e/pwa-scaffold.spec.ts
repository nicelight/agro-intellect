import { expect, test, type Page } from '@playwright/test';

const PROTECTED_PATHS = ['/api/protected/sample', '/api/plants/example'];

async function cachedUrls(page: Page): Promise<string[]> {
	return page.evaluate(async () => {
		const urls: string[] = [];
		for (const name of await caches.keys()) {
			const cache = await caches.open(name);
			for (const request of await cache.keys()) {
				urls.push(request.url);
			}
		}
		return urls;
	});
}

test('scaffold renders, registers the service worker, and caches only static shell assets', async ({
	page
}) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { name: 'Operator PWA' })).toBeVisible();

	const registration = await page.evaluate(async () => {
		const reg = await navigator.serviceWorker.ready;
		return { scope: reg.scope, active: reg.active?.state ?? null };
	});
	expect(registration.scope).toBe('http://127.0.0.1:4173/');
	expect(registration.active).toBe('activated');

	const urls = await cachedUrls(page);
	expect(urls.length).toBeGreaterThan(0);
	for (const url of urls) {
		const pathname = new URL(url).pathname;
		expect(pathname).toMatch(/^\/(_app\/|manifest\.webmanifest$|icon-\d+\.png$)/);
		expect(pathname).not.toBe('/');
		expect(pathname).not.toContain('/api/');
	}
});

test('never caches protected API/SSR responses or the SSR page', async ({ page }) => {
	await page.goto('/');
	await page.waitForFunction(() => navigator.serviceWorker?.ready != null);

	const before = await cachedUrls(page);
	expect(before.length).toBeGreaterThan(0);

	for (const path of PROTECTED_PATHS) {
		const status = await page.evaluate(async (p) => (await fetch(p)).status, path);
		expect(status).toBe(404);
	}

	const after = await cachedUrls(page);
	expect(after).toEqual(before);
	for (const url of after) {
		const pathname = new URL(url).pathname;
		expect(pathname).not.toContain('/api/');
		expect(pathname).not.toBe('/');
	}
});

test('serves an installable web app manifest', async ({ page }) => {
	await page.goto('/');

	const manifestResponse = await page.request.get('/manifest.webmanifest');
	expect(manifestResponse.status()).toBe(200);
	expect(manifestResponse.headers()['content-type']).toContain('application/manifest+json');

	const client = await page.context().newCDPSession(page);
	const { errors, data } = await client.send('Page.getAppManifest');
	expect(errors).toEqual([]);
	if (!data) throw new Error('browser returned no app manifest data');

	const manifest = JSON.parse(data);
	expect(manifest.name).toBeTruthy();
	expect(manifest.short_name).toBeTruthy();
	expect(manifest.start_url).toBe('/');
	expect(manifest.display).toBe('standalone');
	expect(manifest.icons).toEqual(
		expect.arrayContaining([
			expect.objectContaining({ sizes: '192x192', type: 'image/png' }),
			expect.objectContaining({ sizes: '512x512', type: 'image/png' })
		])
	);
});
