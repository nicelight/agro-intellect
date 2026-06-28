---
description: Foundation evidence and redaction contract for logs, scripts, tests, and handoff artifacts.
status: active
owner: architecture
type: contract
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/invariants.md
  - backend/app/core/redaction.py
  - tests/backend/test_foundation_redaction.py
---
# Evidence Redaction Contract

## Ownership

- Owns: redaction rules for Foundation command output, test output, local bootstrap/database transcripts, and task evidence artifacts.
- Does not own: product privacy UX, account/session authorization, dataset governance, or feature-specific redaction checks.
- Related specs:
  - [.memory-bank/runbooks/foundation-local-runtime.md](../runbooks/foundation-local-runtime.md): owns local command flow and troubleshooting notes.
  - [.memory-bank/testing/foundation-test-harness.md](../testing/foundation-test-harness.md): owns evidence commands and verification surface.
  - [.memory-bank/contracts/api-guidelines.md](api-guidelines.md): owns API error redaction guardrails.

## Shape

Allowed Foundation evidence:

- command names and exit status;
- redacted stdout/stderr excerpts;
- pytest summaries;
- `/health` and `/ready` response bodies;
- Alembic revision status without credential-bearing database URLs;
- Memory Bank gate output;
- paths to `.protocols/` and `.tasks/` reports.

Forbidden Foundation evidence:

- plaintext `.env` contents;
- passwords, tokens, API keys, auth headers, credentials, private keys, or session material;
- credential-bearing `DATABASE_URL` or DSN values;
- raw provider payloads or hidden model reasoning;
- screenshots or exports containing auth material.

## Rules

- Scripts and reports MUST pass secret-bearing text through the redaction helper or an equivalent fallback before printing.
- Script output MUST NOT use shell tracing (`set -x`) or print `.env` contents.
- Database URLs MAY retain safe username/host/database context only when the password is masked as `***`.
- Unsupported arguments and failures MUST be redacted before display.
- Evidence artifacts under `.tasks/` and `.protocols/` MUST contain enough context to reproduce the check without leaking secrets.

## Edge Cases / Errors

- If redaction cannot be applied safely, the command or report should omit the sensitive value rather than print it.
- Local PostgreSQL authentication failures must be actionable but must not echo credentials.
- Future feature-specific redaction requirements may extend this contract but must not weaken it.

## Verification Target

- `tests/backend/test_foundation_redaction.py` verifies assignment, URL, auth header, environment, unsupported-argument, and script-message redaction.
- Foundation scripts are inspected by tests to ensure they avoid shell tracing and `.env` printing.
