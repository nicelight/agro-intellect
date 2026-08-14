---
description: Bug note for TASK-064 redaction credential-leak class (scheme regex vs parser scheme class).
status: active
related_task: TASK-064-T3-FT-015-W1
---

# Bug: TASK-064 redaction leak class — scheme regex vs parser scheme class

- Task: `TASK-064-T3-FT-015-W1` (FT-015-AC-003, REQ-020) — `failed` after 5/5
  attempts (budget `max_attempts_per_task: 5`, `max_consecutive_failures: 5`
  exhausted).
- Symptom: `backend/app/core/redaction.py:17` `_URL_SCHEME_RE =
  \b[a-z][a-z0-9+.-]*://` cannot match the app's own parser scheme class
  `[\w\+]+` (SQLAlchemy `make_url`, `.venv/.../sqlalchemy/engine/url.py:868-870`):
  digit/underscore scheme names (`9x://`, `_dhz://`, `dhz_2://`, `d_hz://`,
  `sqlite_driver://`) do not match, so `_USERINFO_AT_RE`/`_host_qualified_at`
  never engage and raw `user:password@` survives in `redact_url_credentials`,
  `redact_text`, `redact_mapping` AND the actual `AppSettings.redacted_for_log()`
  summary. All such URLs are accepted by `make_url`.
- Evidence: `.tasks/TASK-064-T3-FT-015-W1/xh7-verify-attempt05-probe.{py,txt}`
  (298 passed / 48 failed, one class); earlier corpora: rv4 (ATTEMPT 02/03),
  qb8 (ATTEMPT 04), rvs9 (ATTEMPT 03 adjudicated false positives).
- Attempt history: ATTEMPT 01 slash/space/@ (fixed), ATTEMPT 02 colon-preceded
  `word://` (fixed), ATTEMPT 03 empty-prefix pseudo-scheme (fixed), ATTEMPT 04
  non-empty `:`-free prefix (fixed), ATTEMPT 05 digit/underscore scheme names
  (NOT fixed; functional FAIL), ATTEMPT 06 (owner-authorized recovery, effective
  limit 6) ROOT-CAUSE fix applied 2026-08-14: `_URL_SCHEME_RE` replaced with the
  parser's scheme character class `(?<!\w)[\w\+]+://` — digit/underscore/`+`-led
  scheme names now match exactly like `make_url`; `attempt06-probe.py` 926/926
  GREEN, unchanged xh7 verifier probe rerun 298/298 (was 298/48), gates:
  runtime_redaction 155 passed, deterministic_regression 907 passed, mb-lint
  passed, diff_check exit 0. Pending independent `/verify` (then `/red-verify`).
- Root cause (confirmed): `backend/app/core/redaction.py:17` `_URL_SCHEME_RE =
  \b[a-z][a-z0-9+.-]*://` cannot match the app's own parser scheme class
  `[\w\+]+` (SQLAlchemy `make_url`, `.venv/.../sqlalchemy/engine/url.py:868-870`):
  digit/underscore scheme names (`9x://`, `_dhz://`, `dhz_2://`, `d_hz://`,
  `sqlite_driver://`) do not match, so `_USERINFO_AT_RE`/`_host_qualified_at`
  never engage and raw `user:password@` survives in `redact_url_credentials`,
  `redact_text`, `redact_mapping` AND the actual `AppSettings.redacted_for_log()`
  summary. All such URLs are accepted by `make_url`.
- Evidence: `.tasks/TASK-064-T3-FT-015-W1/xh7-verify-attempt05-probe.{py,txt}`
  (298 passed / 48 failed, one class); earlier corpora: rv4 (ATTEMPT 02/03),
  qb8 (ATTEMPT 04), rvs9 (ATTEMPT 03 adjudicated false positives).
- Fix evidence: `.tasks/TASK-064-T3-FT-015-W1/attempt06-probe.{py,txt}`,
  `attempt06-red.txt` (honest RED 926/205), `attempt06-green.txt` (926/926),
  `attempt06-xh7-rerun.txt` (298/298); gate suites extended with the
  digit/underscore scheme family in `tests/backend/test_foundation_redaction.py`
  and `tests/backend/local_privacy/test_runtime_redaction.py`.
- Dependents blocked (while the task was failed): TASK-067..079 (FT-015 W2),
  TASK-081, TASK-094 (FT-016).
