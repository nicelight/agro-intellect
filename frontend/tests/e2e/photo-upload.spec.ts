import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { BACKEND_ORIGIN, PHOTO_EVIDENCE } from './global-setup';

const SEED_PASSWORD = 'Op3rator-Demo-Pa$$w0rd!';
const COOKIE_NAME = 'agro_intellect_session';
const PHOTO_DB = PHOTO_EVIDENCE.dbName;

const frontendDir = import.meta.dirname;
const repoRoot = path.resolve(frontendDir, '..', '..', '..');
const evidenceDir = path.join(repoRoot, '.tasks', 'TASK-084-T3-FT-016-W3');
const evidenceFile = path.join(evidenceDir, 'photo-evidence.json');
const testPhotoPath = path.join(evidenceDir, 'test-photo.jpg');
const rereadScript = path.join(
	repoRoot,
	'frontend',
	'tests',
	'e2e',
	'support',
	'reread-photos.py'
);
const python = path.join(repoRoot, '.venv', 'bin', 'python');

// Fail-closed capture compliance: this file produces no trace/video/screenshot
// artifact, so no capture input can carry password/auth material.
test.use({ trace: 'off', video: 'off', screenshot: 'off' });

// A real 1x1 valid JPEG (standard sample); used as the real local test photo.
const TEST_JPEG =
	'/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q==';

interface PhotoRereadSnapshot {
	dbname: string;
	keys: Record<string, string>;
	catalogs: Record<string, Array<Record<string, unknown>>>;
	artifacts: Array<{ ref: string; size: number }>;
	timeline_counts: Record<string, number>;
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

function reread(): PhotoRereadSnapshot {
	const output = execFileSync(
		python,
		[rereadScript, PHOTO_DB, PHOTO_EVIDENCE.artifactRoot, PHOTO_EVIDENCE.timelineRoot],
		{ cwd: repoRoot, encoding: 'utf8' }
	);
	return JSON.parse(output) as PhotoRereadSnapshot;
}

function artifactFingerprint(snapshot: PhotoRereadSnapshot): string {
	return snapshot.artifacts.map((entry) => `${entry.ref}:${entry.size}`).join('\n');
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

async function directUpload(
	context: APIRequestContext,
	cookie: string,
	plantId: string,
	file: Buffer,
	contentType: string,
	photoType: string = 'whole_plant'
): Promise<Awaited<ReturnType<APIRequestContext['post']>>> {
	return context.post(`${BACKEND_ORIGIN}/api/plants/${plantId}/photos`, {
		headers: { cookie: `${COOKIE_NAME}=${cookie}` },
		multipart: {
			file: { name: 'probe-upload.jpg', mimeType: contentType, buffer: file },
			photo_type: photoType
		}
	});
}

function fieldNames(postData: string | undefined): string[] {
	if (!postData) return [];
	if (postData.includes('name="')) {
		return [...postData.matchAll(/name="([^"]+)"/g)].map((match) => match[1]);
	}
	return [...new URLSearchParams(postData).keys()];
}

const FORBIDDEN_FIELD = /^(farm_id|plant_id|actor|role|permission|freshness|request_id|account_id|authorization|session|path|absolute)/i;

test.describe('local photo upload', () => {
	test('Engineer uploads a real local test photo through Photo Intake HTTP; the exact safe checksum/manifest/event refs render and persist exactly once', async ({
		page
	}) => {
		mkdirSync(evidenceDir, { recursive: true });
		const evidenceBytes = Buffer.from(TEST_JPEG, 'base64');
		writeFileSync(testPhotoPath, evidenceBytes);
		const expectedSha256 = createHash('sha256').update(evidenceBytes).digest('hex');

		const evidences = loadEvidences();
		const snapshotStart = reread();
		const tomatoId = snapshotStart.keys['tomato_001'];
		expect(tomatoId).toBeTruthy();
		expect(snapshotStart.catalogs[tomatoId].length).toBe(0);
		expect(snapshotStart.timeline_counts[tomatoId]).toBe(0);

		// No optimistic acceptance: no photo success renders before upload.
		await browserLogin(page, 'engineer');
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('plant-title')).toHaveText('Tomato 001');
		await expect(page.getByTestId('photo-section')).toBeVisible();
		await expect(page.getByTestId('photo-success')).toHaveCount(0);
		evidences['engineer_loaded_photo_surface'] = true;

		const actionBodies: string[] = [];
		const requestedUrls: string[] = [];
		page.on('request', (req) => {
			requestedUrls.push(req.url());
			if (req.method() === 'POST' && req.url().includes('?/add-photo')) {
				actionBodies.push(req.postData() ?? '');
			}
		});

		await page.getByTestId('photo-file').setInputFiles({
			name: 'test-photo.jpg',
			mimeType: 'image/jpeg',
			buffer: evidenceBytes
		});
		await page.getByTestId('photo-type-select').selectOption('whole_plant');
		await page.getByTestId('photo-submit').click();

		await expect(page.getByTestId('photo-success')).toBeVisible();
		const renderedSha256 = (await page.getByTestId('photo-sha256').textContent()) ?? '';
		const renderedOriginalRef = (await page.getByTestId('photo-original-ref').textContent()) ?? '';
		const renderedManifestRef = (await page.getByTestId('photo-manifest-ref').textContent()) ?? '';
		const renderedEventRef = (await page.getByTestId('photo-event-ref-photo_accepted').textContent()) ?? '';
		const renderedLocalOnly = (await page.getByTestId('photo-local-only').textContent()) ?? '';
		const renderedCanTrain = (await page.getByTestId('photo-can-train').textContent()) ?? '';
		const renderedSize = (await page.getByTestId('photo-size').textContent()) ?? '';
		const renderedContentType = (await page.getByTestId('photo-content-type').textContent()) ?? '';
		const renderedPhotoId = (await page.getByTestId('photo-id').textContent()) ?? '';

		// Checksum is authoritative: the returned sha256 must equal the real
		// local test file's digest.
		expect(renderedSha256).toBe(expectedSha256);
		expect(renderedContentType).toBe('image/jpeg');
		expect(Number(renderedSize)).toBe(evidenceBytes.length);
		expect(renderedPhotoId.length).toBeGreaterThan(0);
		// Safe relative artifact refs only; never an absolute filesystem path.
		expect(renderedOriginalRef).toMatch(
			new RegExp(`^plants/([0-9a-f-]{36})/photos/${renderedPhotoId}/original\\.jpg$`)
		);
		expect(renderedManifestRef).toMatch(
			new RegExp(`^plants/([0-9a-f-]{36})/photos/${renderedPhotoId}/manifest\\.initial_capture\\.json$`)
		);
		expect(renderedEventRef).toMatch(/photo_accepted: timeline\.jsonl#[0-9a-f-]{36}/);
		expect(renderedLocalOnly).toBe('local_only');
		expect(renderedCanTrain).toBe('false');
		evidences['exact_checksum_rendered'] = renderedSha256;
		evidences['exact_manifest_and_event_refs_rendered'] = true;

		// No implicit server/cloud/upload wording anywhere in the section.
		const sectionHtml = (await page.getByTestId('photo-section').innerHTML()) ?? '';
		expect(sectionHtml.toLowerCase()).not.toContain('cloud');
		expect(sectionHtml.toLowerCase()).not.toContain('server');
		expect(sectionHtml.toLowerCase()).not.toContain('sync');
		expect(sectionHtml.toLowerCase()).toContain('local_only');
		evidences['no_remote_upload_implication'] = true;

		// Browser-edge exactness: only registered fields reach the action.
		expect(actionBodies.length).toBeGreaterThanOrEqual(1);
		let onlyRegisteredFields = true;
		for (const body of actionBodies) {
			const names = fieldNames(body);
			if (names.some((name) => FORBIDDEN_FIELD.test(name))) {
				onlyRegisteredFields = false;
			}
			if (names.length > 0) {
				for (const name of names) {
					if (!['file', 'photo_type'].includes(name)) onlyRegisteredFields = false;
				}
			}
		}
		evidences['only_registered_fields_sent'] = onlyRegisteredFields;

		// Authoritative reread: exactly one catalog row, exact matching
		// artifact files, one photo_accepted timeline event.
		const snapshotAfter = reread();
		expect(snapshotAfter.catalogs[tomatoId].length).toBe(1);
		expect(snapshotAfter.timeline_counts[tomatoId]).toBe(1);
		evidences['accepted_exactly_once'] = true;

		const row = snapshotAfter.catalogs[tomatoId][0];
		expect(row.sha256).toBe(expectedSha256);
		expect(row.original_file_ref).toBe(renderedOriginalRef);
		expect(row.manifest_ref).toBe(renderedManifestRef);
		expect(row.local_only).toBe(true);
		expect(row.can_train_on).toBe(false);
		const eventRefs = row.event_refs as Record<string, { timeline_ref: string }>;
		expect(eventRefs.photo_accepted?.timeline_ref).toBe(
			renderedEventRef.replace('photo_accepted: ', '')
		);
		evidences['dom_matches_authoritative_catalog'] = true;

		const artifactRefs = snapshotAfter.artifacts.map((entry) => entry.ref);
		expect(artifactRefs).toContain(String(row.original_file_ref));
		expect(artifactRefs).toContain(String(row.manifest_ref));
		expect(artifactRefs.length).toBe(2);
		// The stored original matches the real test file.
		const originalPath = path.join(PHOTO_EVIDENCE.artifactRoot, String(row.original_file_ref ?? ''));
		const storedBytes = readFileSync(originalPath);
		expect(createHash('sha256').update(storedBytes).digest('hex')).toBe(expectedSha256);
		evidences['real_file_stored_and_checksum_matches'] = true;

		// A later failed upload must not leave an optimistic success visible
		// and must not create a second accepted artifact. The `required`
		// attribute blocks an empty file submit in the UI, so the decisive
		// unsupported case is exercised next through the same UI with a
		// bypassing (non-jpeg) file which the backend alone can reject.
		const beforeFailure = artifactFingerprint(snapshotAfter);
		await page.getByTestId('photo-file').setInputFiles({
			name: 'note.txt',
			mimeType: 'text/plain',
			buffer: Buffer.from('not a photo')
		});
		await page.getByTestId('photo-type-select').selectOption('leaf_closeup');
		await page.getByTestId('photo-submit').click();
		await expect(page.getByTestId('photo-error')).toBeVisible();
		await expect(page.getByTestId('photo-error')).toContainText(
			'Unsupported media type.'
		);
		await expect(page.getByTestId('photo-success')).toHaveCount(0);
		evidences['unsupported_rejected_in_ui'] = true;

		const snapshotAfterFailure = reread();
		expect(snapshotAfterFailure.catalogs[tomatoId].length).toBe(1);
		expect(snapshotAfterFailure.timeline_counts[tomatoId]).toBe(1);
		expect(artifactFingerprint(snapshotAfterFailure)).toBe(beforeFailure);
		evidences['no_partial_artifact_after_failure'] = true;

		// No auth material or backend origin reaches the page.
		const pageHtml = await page.content();
		expect(pageHtml).not.toContain('127.0.0.1:8100');
		const token = (await page.context().cookies()).find((c) => c.name === COOKIE_NAME)?.value;
		if (token) expect(pageHtml).not.toContain(token);
		expect(pageHtml).not.toContain(SEED_PASSWORD);
		expect(pageHtml).not.toContain(repoRoot);
		evidences['no_auth_material_or_path_in_page_html'] = !pageHtml.includes('127.0.0.1:8100');
		evidences['backend_origin_absent_from_browser_requests'] = !requestedUrls.some((url) =>
			url.includes('127.0.0.1:8100')
		);

		saveEvidences(evidences);
	});

	test('unsupported, oversized, denied, and archived uploads are truthful non-acceptance failures with no partial artifact', async ({
		page,
		playwright
	}) => {
		const evidences = loadEvidences();
		const before = reread();
		const tomatoId = before.keys['tomato_001'];
		const herbId = before.keys['herb_003'];
		expect(tomatoId).toBeTruthy();
		expect(herbId).toBeTruthy();

		const engineer = await backendSession(playwright, 'engineer');

		// Unsupported media type -> 415 UNSUPPORTED_MEDIA_TYPE.
		const unsupported = await directUpload(
			engineer.context,
			engineer.cookie,
			tomatoId,
			Buffer.from('not a photo'),
			'text/plain'
		);
		expect(unsupported.status()).toBe(415);
		const unsupportedBody = (await unsupported.json()) as { error?: { code?: string } };
		expect(unsupportedBody.error?.code).toBe('UNSUPPORTED_MEDIA_TYPE');
		evidences['unsupported_rejection'] = unsupportedBody.error?.code ?? 'missing';

		// Oversized file (20 MiB + 1) -> 413 UPLOAD_TOO_LARGE.
		const oversized = await directUpload(
			engineer.context,
			engineer.cookie,
			tomatoId,
			Buffer.alloc(20 * 1024 * 1024 + 1),
			'image/jpeg'
		);
		expect(oversized.status()).toBe(413);
		const oversizedBody = (await oversized.json()) as { error?: { code?: string } };
		expect(oversizedBody.error?.code).toBe('UPLOAD_TOO_LARGE');
		evidences['oversized_rejection'] = oversizedBody.error?.code ?? 'missing';

		// Missing grant: Engineer without a grant on tomato_001.
		const nogrant = await backendSession(playwright, 'engineer_nogrant');
		const denied = await directUpload(
			nogrant.context,
			nogrant.cookie,
			tomatoId,
			Buffer.from('x'),
			'image/jpeg'
		);
		expect(denied.status()).toBe(404);
		const deniedBody = (await denied.json()) as { error?: { code?: string } };
		expect(deniedBody.error?.code).toBe('AUTH_PLANT_FORBIDDEN');
		evidences['unauthorized_rejection'] = deniedBody.error?.code ?? 'missing';

		// Archived Plant: an authorized Engineer cannot upload to herb_003.
		const archived = await directUpload(
			engineer.context,
			engineer.cookie,
			herbId,
			Buffer.from('x'),
			'image/jpeg'
		);
		expect(archived.status()).toBe(404);
		const archivedBody = (await archived.json()) as { error?: { code?: string } };
		expect(archivedBody.error?.code).toBe('AUTH_PLANT_FORBIDDEN');
		evidences['archive_rejection'] = archivedBody.error?.code ?? 'missing';

		// UI denial stays presentation-only: denied/archived Plants render the
		// safe shell denial and zero photo surface.
		await browserLogin(page, 'engineer_nogrant');
		await page.goto(`/plants/${tomatoId}`);
		await expect(page.getByTestId('plant-error')).toBeVisible();
		await expect(page.getByTestId('photo-section')).toHaveCount(0);
		evidences['denied_plant_has_no_photo_surface'] = true;

		// Authoritative reread: every rejected request left no catalog row, no
		// artifact file, and no timeline event relative to the pre-request
		// snapshot.
		const after = reread();
		expect(after.catalogs[tomatoId].length).toBe(before.catalogs[tomatoId].length);
		expect(after.catalogs[herbId].length).toBe(before.catalogs[herbId].length);
		expect(after.timeline_counts[tomatoId]).toBe(before.timeline_counts[tomatoId]);
		expect(after.timeline_counts[herbId]).toBe(before.timeline_counts[herbId]);
		expect(artifactFingerprint(after)).toBe(artifactFingerprint(before));
		evidences['all_rejections_left_no_residue'] = true;

		saveEvidences(evidences);
	});
});
