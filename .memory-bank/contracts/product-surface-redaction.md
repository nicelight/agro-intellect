---
description: Product runtime secret and auth-material redaction contract across persisted, serialized, exported, and captured surfaces.
status: active
type: security_contract
last_updated: 2026-08-12
source_of_truth:
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/contracts/auth/session-security.md
---
# Product Surface Redaction

## Scope

This contract applies the shared redaction baseline to product runtime output.
It covers application logs and safe API errors, Timeline and retained-history
exports, photo manifests, Agent Chat Bus, UI Feed, agent/provider context, and
browser screenshot artifacts when that frontend surface exists.

It does not authorize a generic free-text pipeline or replace each owning
boundary's strict payload allowlist. The Foundation evidence contract remains
the owner for bootstrap, command, and task-evidence output.

## Secret corpus

The forbidden corpus includes:

- plaintext passwords and password reset/bootstrap values;
- raw session tokens, token digests, cookies, bearer credentials, and
  authorization headers;
- provider/API keys, private keys, credentials, and configured secret values;
- plaintext `.env` values selected by sensitive keys;
- credential-bearing database URLs and DSNs.

The shared runtime marker is `***`. Exact configured secret values and
structured auth fields are authoritative fixtures. Pattern-based detection is
defense in depth and must not be the only proof for configured values.

## Surface rules

| Surface | Owning boundary | Required behavior |
|---|---|---|
| application logs and safe API errors | Runtime Substrate plus the owning HTTP contract | sanitize before emission; stable errors expose neither internal exception text nor forbidden corpus |
| Timeline and retained-history/export output | Timeline Audit and Plant History | strict registered summaries first, then redact or fail closed before append/serialization |
| photo manifests | Photo Intake | manifest allowlist excludes auth fields and sanitizes any accepted string value before the atomic write |
| Agent Chat Bus and UI Feed | Agent Chat & UI Feed | strict typed payloads exclude auth material; authorized text is sanitized before persistence/publication |
| agent/provider context | Agent Runtime Core and competence owner | strict request allowlists exclude credentials, raw ActorContext, cookies, headers, UI text, and provider history |
| screenshots/browser captures | Operator PWA | sanitize or omit forbidden values before capture; raw auth fields must never be rendered as capture input |

Rules:

- Redaction or rejection MUST happen before persistence, append, publication,
  serialization, export, or capture. A cleanup pass is not acceptance.
- Runtime authentication/provider source values MUST remain unchanged for their
  owning operation; only output copies are sanitized.
- When a boundary cannot prove safe output, it MUST fail closed with its
  registered safe error instead of emitting the uncertain value.
- Redaction MUST NOT create runtime, audit, UI, agent-context, upload, or sync
  authority.
- The current brownfield tree has no Operator PWA or screenshot output. FT-015
  proves that absence rather than adding a competing frontend; FT-016 must
  apply this contract when it creates the capture surface.

## Errors and edge cases

- A configured secret embedded inside otherwise allowed text is still removed.
- A credential-bearing URL may retain safe scheme/host/database context only
  after its credential component is masked.
- Empty/non-secret values need not be replaced merely because their field is
  optional; actual structured auth fields remain forbidden from product
  payload schemas.
- Sanitizer failure must not include the rejected raw value in its error.
- Secret-looking inert candidate text does not gain authority. If it contains
  an actual configured secret or structured auth value, the owning boundary
  redacts or rejects it before output.

## Verification target

- A single configured corpus is injected through actual serializers/writers
  for logs/errors, Timeline/history, manifests, Bus, UI Feed, and agent-context
  assembly; captured output contains none of the raw values.
- Tests prove source credentials remain usable and unchanged after an output
  copy is sanitized.
- Safe failure paths contain the stable error only and no rejected value.
- Source inspection proves no current frontend/screenshot capture surface;
  the FT-016 consumer contract retains this spec as a required input.

## Related specs

- [Evidence Redaction](evidence-redaction.md)
- [Session Security](auth/session-security.md)
- [Timeline Event](timeline-event.md)
- [Agent Chat Bus](agent-chat-bus.md)
- [UI Feed](ui-feed.md)
- [MessageEnvelope](message-envelope.md)
- [Photo Artifacts](../domains/photo-artifacts.md)

