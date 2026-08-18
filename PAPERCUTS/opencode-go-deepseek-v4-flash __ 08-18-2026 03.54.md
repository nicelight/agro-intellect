# Papercuts — opencode-go-deepseek-v4-flash (session 08-18-2026)

- Flaky e2e: `frontend/tests/e2e/pwa-scaffold.spec.ts:41`
  ("never caches protected API/SSR responses or the SSR page") fails about 1/3
  of combined regression runs with `before.length` == 0. Cause: the test waits
  with `await page.waitForFunction(() => navigator.serviceWorker?.ready != null)`
  which resolves immediately because `navigator.serviceWorker.ready` is a
  non-null Promise; it does not actually await SW activation, so the cache may
  still be empty when `cachedUrls(page)` runs. Pre-existing (TASK-080 scaffold
  spec), observed independently of TASK-083 harness changes.

- Backgrounding a loopback uvicorn in a bash tool call with `cmd &` gets the
  process killed when the tool's 120s timeout kills the command's process group,
  even with `nohup`/`disown` (plain `&`); `setsid ... & ` survived until
  manually killed but still made the tool stall until timeout. Cost: a manual
  Feed API preflight against a scratch Postgres DB jumped through several restarts.
  The e2e harness (global-setup starts/stops its own backend) is the reliable path.
- `pgrep -f "uvicorn backend.app.main"` (and `pkill`) matches the current
  `/bin/bash -c` process itself because the pattern string appears in its own
  cmdline; use `pgrep -af` and filter with `grep -v`/exact `--port` matching.
- `provision-postgres.py` fails to DROP the target database with
  `ObjectInUse` if any leftover backend still holds a session on it (stale
  preflight backend); kill the stale backend first.
- A single `npm run test:e2e -- A.spec.ts : B.spec.ts` style chaining via `:`
  is parsed as a `tail` argument; e2e specs that need different provisioning
  modes must be invoked as separate playwright runs anyway.
- Declaring `$state` initializers directly from a SvelteKit `data` prop raises
  the Svelte 5 `state_referenced_locally` warning (capture-initial pattern);
  hydrating once via a guarded `$effect.pre` yields a clean `svelte-check`.
