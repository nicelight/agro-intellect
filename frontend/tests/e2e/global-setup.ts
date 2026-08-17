import { spawn, execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, openSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';

export const BACKEND_ORIGIN = 'http://127.0.0.1:8100';

const frontendDir = import.meta.dirname;
const repoRoot = path.resolve(frontendDir, '..', '..', '..');

// The Boss-provisioning spec hits POST /api/admin/accounts, whose authorized
// path uses PostgreSQL row locks and JSONB audit columns. It therefore boots
// the backend against an isolated local PostgreSQL database (loopback only,
// per the Foundation local-runtime runbook) instead of the disposable SQLite
// used by the session/Plant shell suite. All other specs keep the SQLite path.
const provisioningRequested =
	process.argv.some((arg) => arg.includes('boss-engineer-provisioning')) ||
	Boolean(process.env.E2E_DATABASE_URL);

const evidenceDir = provisioningRequested
	? path.join(repoRoot, '.tasks', 'TASK-082-T3-FT-016-W3')
	: path.join(repoRoot, '.tasks', 'TASK-081-T3-FT-016-W2');
const e2eDir = path.join(evidenceDir, 'e2e-browser');
const dbPath = path.join(e2eDir, 'auth-shell.sqlite3');
const pidPath = path.join(e2eDir, 'backend.pid');
const backendLogPath = path.join(e2eDir, 'backend.log');
const provisioningDbName = 'agro_intellect_e2e_082';

function dotenvValue(key: string): string | null {
	const envPath = path.join(repoRoot, '.env');
	if (!existsSync(envPath)) return null;
	for (const line of readFileSync(envPath, 'utf8').split('\n')) {
		const trimmed = line.trim();
		if (!trimmed || trimmed.startsWith('#')) continue;
		const eq = trimmed.indexOf('=');
		if (eq < 0) continue;
		if (trimmed.slice(0, eq).trim() === key) return trimmed.slice(eq + 1).trim();
	}
	return null;
}

function postgresDsns(): { admin: string; target: string } | null {
	const base = process.env.E2E_DATABASE_URL ?? dotenvValue('DATABASE_URL');
	if (!base || !base.includes('postgresql')) return null;
	try {
		const url = new URL(base.replace('postgresql+psycopg://', 'postgresql://'));
		if (!url.username) return null;
		const host = url.hostname || 'localhost';
		const port = url.port || '5432';
		const creds = url.username + (url.password ? `:${url.password}` : '');
		const target = `postgresql+psycopg://${creds}@${host}:${port}/${provisioningDbName}`;
		const admin = `postgresql+psycopg://${creds}@${host}:${port}/postgres`;
		return { admin, target };
	} catch {
		return null;
	}
}

async function waitForHealth(origin: string, timeoutMs: number): Promise<void> {
	const deadline = Date.now() + timeoutMs;
	let lastError: unknown = null;
	while (Date.now() < deadline) {
		try {
			const response = await fetch(`${origin}/health`, { signal: AbortSignal.timeout(2000) });
			if (response.ok) {
				const body = (await response.json()) as { status?: string };
				if (body.status === 'ok') return;
			}
			lastError = new Error(`health returned ${response.status}`);
		} catch (error) {
			lastError = error;
		}
		await new Promise((resolve) => setTimeout(resolve, 400));
	}
	throw new Error(`backend did not become healthy: ${String(lastError)}`);
}

function startBackend(command: string[], backendEnv: Record<string, string>): void {
	const backendLogFd = openSync(backendLogPath, 'a');
	const child = spawn(path.join(repoRoot, '.venv', 'bin', 'python'), command, {
		cwd: repoRoot,
		env: {
			...process.env,
			PYTHONUNBUFFERED: '1',
			...backendEnv
		},
		stdio: ['ignore', backendLogFd, backendLogFd]
	});
	writeFileSync(pidPath, String(child.pid));
}

export default async function globalSetup(): Promise<void> {
	mkdirSync(e2eDir, { recursive: true });

	if (provisioningRequested) {
		const dsns = postgresDsns();
		if (!dsns) {
			throw new Error(
				'PostgreSQL e2e backend requested but no DATABASE_URL found in .env (or E2E_DATABASE_URL).'
			);
		}
		const provisionOutput = execFileSync(
			path.join(repoRoot, '.venv', 'bin', 'python'),
			[path.join(frontendDir, 'support', 'provision-postgres.py'), dsns.admin, dsns.target],
			{
				cwd: repoRoot,
				env: { ...process.env, PYTHONUNBUFFERED: '1' },
				stdio: ['ignore', 'pipe', 'pipe']
			}
		).toString('utf8');
		console.log(`[e2e-setup] ${provisionOutput.trim()}`);

		startBackend(
			['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8100', '--log-level', 'warning'],
			{ DATABASE_URL: dsns.target, APP_ENV: 'test', APP_NAME: 'agro-intellect-e2e' }
		);
		try {
			await waitForHealth(BACKEND_ORIGIN, 30_000);
		} catch (error) {
			process.kill(Number(readFileSync(pidPath, 'utf8')), 'SIGKILL');
			throw error;
		}
		console.log(`[e2e-setup] backend healthy at ${BACKEND_ORIGIN} (postgresql)`);
		return;
	}

	if (existsSync(dbPath)) rmSync(dbPath, { force: true });
	const seedOutput = execFileSync(
		path.join(repoRoot, '.venv', 'bin', 'python'),
		[path.join(frontendDir, 'support', 'seed-auth-shell.py'), dbPath],
		{
			cwd: repoRoot,
			env: { ...process.env, PYTHONUNBUFFERED: '1' },
			stdio: ['ignore', 'pipe', 'pipe']
		}
	).toString('utf8');
	console.log(`[e2e-setup] ${seedOutput.trim()}`);

	startBackend(
		['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8100', '--log-level', 'warning'],
		{
			DATABASE_URL: `sqlite+pysqlite:///${dbPath}`,
			APP_ENV: 'test',
			APP_NAME: 'agro-intellect-e2e'
		}
	);

	try {
		await waitForHealth(BACKEND_ORIGIN, 30_000);
	} catch (error) {
		process.kill(Number(readFileSync(pidPath, 'utf8')), 'SIGKILL');
		throw error;
	}
	console.log(`[e2e-setup] backend healthy at ${BACKEND_ORIGIN}`);
}