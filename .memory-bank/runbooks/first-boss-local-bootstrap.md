---
description: First Boss one-shot local bootstrap command contract and operator runbook.
status: active
type: runbook
last_updated: 2026-07-09
source_of_truth:
  - .memory-bank/contracts/admin/boss-admin-http.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/contracts/evidence-redaction.md
---
# First Boss Local Bootstrap

## Scope

Defines the one local operator command that creates the first active Boss
Account after the canonical Farm exists.

## Out of scope

Farm/`tomato_001` bootstrap, normal Boss-created personnel flows, hosted
identity, email delivery, password recovery, SaaS tenancy, and PWA UI.

## Command

```bash
bash scripts/bootstrap-first-boss-local.sh --login-name <login_name> --display-name <display_name>
```

Optional:

```bash
bash scripts/bootstrap-first-boss-local.sh --dry-run
```

The command uses the existing Foundation `.env` loading pattern and the
Foundation `AppSettings`/`DatabaseHandle` path. It must run after migrations and
after `bash scripts/bootstrap-farm-local.sh` has created or confirmed the
canonical Farm.

## Inputs

- `--login-name`: required safe text argument; normalized with
  `strip().lower()` by the Account storage boundary.
- `--display-name`: required safe text argument; trimmed and non-empty.
- Password: read interactively with Python `getpass` and confirmation.

The password is never accepted through argv, environment variables, stdin echo,
logs, audit, screenshots, exports, Bus, UI Feed, or task evidence.

## Behavior

- If no canonical Farm exists, fail before mutation with a safe diagnostic that
  tells the operator to run `bash scripts/bootstrap-farm-local.sh`.
- If any active Boss membership already exists for the local Farm, refuse before
  mutation. The command is one-shot, not a password reset or extra-admin tool.
- If normalized login already exists, fail before or during persistence without
  creating Account, FarmMembership, or audit records.
- On success, one DB transaction creates:
  - active Account with normalized login, display name, and Argon2id password
    hash;
  - active FarmMembership for the canonical Farm with `role_preset=boss`;
  - exactly one `account_created` AdminAuditRecord with
    `actor_kind=system_bootstrap`.
- The audit after-summary contains only safe Account, Membership, Farm, role,
  status, and bootstrap refs. It never contains the password, password hash,
  session token, token hash, cookie, auth header, or raw command input beyond
  safe normalized identity fields.
- A successful command does not create a session. The new Boss logs in through
  the normal Session HTTP contract.

## Failure And Redaction

- Unsupported arguments are rejected with safe text.
- Password mismatch, blank fields, invalid login, duplicate login, missing Farm,
  existing active Boss, and persistence failures leave no partial success.
- Unexpected persistence failures use safe diagnostics and must not expose SQL,
  DSN, `.env`, credentials, raw exception text, password material, or hashes.
- `--dry-run` reports that it would inspect prerequisites without prompting for
  a password and without mutation.

## Verification

- Command tests prove no password argv/env path exists and `getpass` is used.
- Integration tests prove missing Farm, existing active Boss, duplicate login,
  password mismatch, and persistence failure leave no partial Account,
  FarmMembership, or AdminAuditRecord.
- Success tests prove one active Boss Account/Membership, exactly one
  `account_created` system-bootstrap audit, Argon2id password hashing, no
  session creation, and successful subsequent login through Session HTTP.
- Redaction tests prove command output and evidence exclude every secret class
  listed above.

## Related specs

- [.memory-bank/contracts/admin/boss-admin-http.md](../contracts/admin/boss-admin-http.md)
- [.memory-bank/domains/admin/admin-audit.md](../domains/admin/admin-audit.md)
- [.memory-bank/contracts/auth/session-security.md](../contracts/auth/session-security.md)
- [.memory-bank/domains/farm/farm-plant-access-storage.md](../domains/farm/farm-plant-access-storage.md)
- [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md)
