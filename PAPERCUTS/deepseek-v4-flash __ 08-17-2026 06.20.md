# Papercuts — deepseek-v4-flash session 2026-08-17

## `vite preview` binds IPv6 loopback only (Playwright health check timeout)
- `vite preview` (vite 8.2.1, SvelteKit 2.70.2, adapter-node) printed
  `Local: http://localhost:4173/` but listened only on `[::1]:4173`; the
  Playwright webServer health check against `http://127.0.0.1:4173` timed out
  (180s). Fix: add `--host 127.0.0.1` to the preview/webServer command.
  No error was printed by the server itself.

## `expect(x).toBeTruthy()` does not narrow `string | undefined` for svelte-check
- `const { data } = await client.send('Page.getAppManifest')` — `data` is
  `string | undefined`; an `expect(data).toBeTruthy()` assertion did not narrow
  it for svelte-check (TS 6.0.3); required an explicit
  `if (!data) throw new Error(...)`.

## Bash tool kills background children of a command
- Background servers started inside a tool call (`cmd &`) are killed when the
  tool call returns (even with `nohup ... &`); `setsid nohup ... &` keeps the
  process alive across calls. Relevant for manual server debugging; Playwright
  `webServer` (a foreground child) is unaffected.

## Fresh SQLite test/probe DDL fails without a registered `btrim` function
- Any new SQLite-based probe or test that calls
  `Base.metadata.create_all(engine)` fails with
  `sqlite3.OperationalError: no such function: btrim` because several table
  CHECK constraints (`accounts.login_name_canonical` etc.) call
  `btrim(...)`. The existing history API fixture registers it via
  `event.listen(engine, "connect", conn.create_function("btrim", 1, strip))`;
  new in-memory-SQLite fixtures/tests must do the same before `create_all`.

## `create_actor` cannot seed a disabled-membership actor
- `tests/backend/plant_operations/conftest.py::create_actor` resolves the
  ActorContext through `ActorContextResolver`, and `_validated_identity_is_consistent`
  requires `membership_status == "active"`; requesting
  `membership_status="disabled"` raises `ActorContextDenied` at fixture time.
  To test an authentically disabled actor, insert Account + disabled
  FarmMembership + LocalSession rows directly and build the `ActorContext` via
  `ActorContext._from_validated` (see
  `tests/backend/dataset_governance/test_dataset_candidate_reads.py::_disabled_actor`).

## Duplicate query params in a `params=` dict collapse silently
- Passing `params={"cursor": "a", "cursor": "b"}` to a TestClient request
  silently keeps only the last value (dict literal lacks duplicate keys), so a
  "duplicate parameter is rejected" test never exercises the duplicate path.
  Pass `params=[("cursor", "a"), ("cursor", "b")]` (list of tuples).
