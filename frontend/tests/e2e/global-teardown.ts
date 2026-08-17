import { execFileSync, execSync } from 'node:child_process';
import { existsSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';

const frontendDir = import.meta.dirname;
const repoRoot = path.resolve(frontendDir, '..', '..', '..');

const provisioningRequested =
	process.argv.some((arg) => arg.includes('boss-engineer-provisioning')) ||
	Boolean(process.env.E2E_DATABASE_URL);

const evidenceDir = provisioningRequested
	? path.join(repoRoot, '.tasks', 'TASK-082-T3-FT-016-W3')
	: path.join(repoRoot, '.tasks', 'TASK-081-T3-FT-016-W2');
const e2eDir = path.join(evidenceDir, 'e2e-browser');
const pidPath = path.join(e2eDir, 'backend.pid');
const dbPath = path.join(e2eDir, 'auth-shell.sqlite3');

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

async function stopBackend(): Promise<void> {
	if (existsSync(pidPath)) {
		const pid = Number(readFileSync(pidPath, 'utf8').trim());
		if (Number.isInteger(pid) && pid > 0) {
			try {
				execSync(`kill ${pid} 2>/dev/null || true`, { shell: '/bin/bash' });
				await new Promise((resolve) => setTimeout(resolve, 800));
				execSync(`kill -0 ${pid} 2>/dev/null && kill -9 ${pid} 2>/dev/null || true`, {
					shell: '/bin/bash'
				});
			} catch {
				// process already gone
			}
		}
		rmSync(pidPath, { force: true });
	}
}

function dropProvisioningDatabase(): void {
	const base = process.env.E2E_DATABASE_URL ?? dotenvValue('DATABASE_URL');
	if (!base || !base.includes('postgresql')) return;
	try {
		const url = new URL(base.replace('postgresql+psycopg://', 'postgresql://'));
		const dbname = 'agro_intellect_e2e_082';
		const creds = url.username + (url.password ? `:${url.password}` : '');
		const adminUrl = `postgresql+psycopg://${creds}@${url.hostname || 'localhost'}:${url.port || '5432'}/postgres`;
		execFileSync(
			path.join(repoRoot, '.venv', 'bin', 'python'),
			[
				'-c',
				`import os,sys; from sqlalchemy import create_engine, text; e=create_engine(os.environ["ADMIN_DSN"], isolation_level="AUTOCOMMIT", pool_pre_ping=True);\nwith e.connect() as c:\n c.execute(text("SELECT 1 FROM pg_catalog.pg_database WHERE datname = :n"), {"n": "${dbname}"})\n c.execute(text('DROP DATABASE IF EXISTS "${dbname}"'))\ne.dispose()`
			],
			{ env: { ...process.env, ADMIN_DSN: adminUrl, PYTHONUNBUFFERED: '1' } }
		);
		console.log('[e2e-teardown] isolated provisioning database dropped');
	} catch {
		console.log('[e2e-teardown] isolated provisioning database already gone or not dropped');
	}
}

export default async function globalTeardown(): Promise<void> {
	await stopBackend();
	if (provisioningRequested) {
		dropProvisioningDatabase();
		console.log('[e2e-teardown] backend stopped; isolated database removed');
		return;
	}
	rmSync(dbPath, { force: true });
	console.log('[e2e-teardown] backend stopped; disposable database removed');
}