import { defineConfig, devices } from '@playwright/test';
import { BACKEND_ORIGIN } from './tests/e2e/global-setup';

export default defineConfig({
	testDir: 'tests/e2e',
	fullyParallel: false,
	retries: 0,
	reporter: 'line',
	timeout: 90_000,
	globalSetup: './tests/e2e/global-setup.ts',
	globalTeardown: './tests/e2e/global-teardown.ts',
	use: {
		baseURL: 'http://127.0.0.1:4173',
		trace: 'retain-on-failure'
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		}
	],
	webServer: {
		command:
			'npm run build && npm run preview -- --host 127.0.0.1 --port 4173 --strictPort',
		url: 'http://127.0.0.1:4173',
		env: { BACKEND_ORIGIN },
		reuseExistingServer: !process.env.CI,
		timeout: 180_000
	}
});