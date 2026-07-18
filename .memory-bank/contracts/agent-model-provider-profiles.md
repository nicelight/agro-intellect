---
description: Explicit Agent Runtime provider profiles, deploy-time model binding, credential boundary, and external-egress rules.
status: active
type: interface_contract
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/evidence-redaction.md
---
# Agent Model Provider Profiles

## Scope

This contract defines how Agent Runtime resolves an explicit provider and
model id for one canonical product agent. It owns supported profile names,
deploy-time binding, credential isolation, typed external egress, dependency
expectations, fail-closed selection, and model-adapter evidence.

Agno/provider SDKs are replaceable execution dependencies. Project-owned Agent
definitions, typed context, validation, authorization, audit, and
MessageEnvelope semantics remain authoritative.

## Out of scope

- Detailed competence policy and application triggers; FT-009 through FT-014
  add them without changing the FT-007 roster identity.
- Bus/UI publication, chat/feed persistence, and delivery reconciliation.
- Provider account creation, billing, browser-login automation, token scraping,
  or undocumented credential refresh.
- Hardcoded/default model ids, fallback chains, provider history, Agno memory,
  tools, RAG, or Team coordination.

## Related specs

- [.memory-bank/contracts/agent-runtime-adapter.md](agent-runtime-adapter.md):
  invocation, validation, current authorization guard, audit, and handoff.
- [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
  canonical identities and post-commit activation/introduction handoff.
- [.memory-bank/contracts/evidence-redaction.md](evidence-redaction.md):
  secret-safe configuration, logs, and evidence.
- [.memory-bank/runbooks/agent-runtime-providers.md](../runbooks/agent-runtime-providers.md):
  configuration and credentialed smoke procedure.

## Binding shape

Production reads one strict, non-secret `AGENT_MODEL_BINDINGS_JSON` object.
Each key is a canonical roster `agent_id`; each value is exactly:

- `provider_profile`: `chatgpt_oauth | deepseek | gemini`;
- `model_id`: non-blank deployment model id, 1 through 128 characters, without
  whitespace, controls, credentials, query strings, or URI userinfo.

Unknown fields, unknown roster ids/profiles, blank model ids, duplicate keys,
and non-object values reject the whole mapping. A partial map is allowed while
product competences are delivered incrementally; invoking an unbound agent
returns `AGENT_RUNTIME_NOT_CONFIGURED`.

The mapping contains no credential, endpoint override, prompt, authorization
snapshot, or fallback list. There is no default agent, provider, or model.
Callers, routes, UI/chat payloads, and model output cannot override it.

`AGENT_EXTERNAL_EGRESS_ENABLED` defaults to `false`. Every version-1 profile
is external and may run only when this value is explicitly `true`.

## Supported profiles

| Profile | Agno/client binding | `auth_mode` and credential source | FT-007 status |
|---|---|---|---|
| `deepseek` | native Agno `DeepSeek(id=model_id)` | `api_key_env`, `DEEPSEEK_API_KEY`; direct `agno` and `openai` dependencies | operational when configured |
| `gemini` | native Agno `Gemini(id=model_id)` | `api_key_env`, `GOOGLE_API_KEY`; direct `agno` and `google-genai` dependencies | operational when configured |
| `chatgpt_oauth` | project-owned `ChatGptOAuthCredentialAdapter`/broker port | `external_oauth_broker`, opaque short-lived credential supplied by an approved adapter | recognized and fail-closed; no built-in adapter |

Provider identity and authentication mode are separate. An API key cannot be
relabeled as OAuth, and a ChatGPT subscription or local Codex login cannot be
treated as an OpenAI API credential.

The project declares direct runtime dependencies in `pyproject.toml`; an
undeclared transitive import is not a supported profile.

## ChatGPT OAuth boundary

The public OpenAI API documents API-key authentication, while the documented
"Sign in with ChatGPT" flow is scoped to Codex clients. FT-007 therefore does
not invent a generic third-party ChatGPT OAuth token, refresh, or model-endpoint
contract.

An operational `chatgpt_oauth` binding requires a later project-approved
adapter contract defining authorized token source, refresh/expiry, revocation,
endpoint/audience, redaction, and credentialed verification. Until then,
selecting the profile returns `AGENT_RUNTIME_NOT_CONFIGURED` before network I/O.

The runtime must never:

- read or copy ChatGPT browser/session or Codex CLI/IDE credential files;
- accept a pasted browser token as runtime configuration;
- substitute `OPENAI_API_KEY` for `chatgpt_oauth`;
- claim operational support merely because the profile id parses.

## Selection and construction

1. Resolve one project-owned definition by canonical `agent_id`.
2. Resolve exactly one profile/model binding from the strict deployment map.
3. Require explicit external-egress enablement.
4. Require the declared dependency and matching credential/approved adapter.
5. Construct exactly one real provider model and one Agno executor.
6. Invoke no other profile/model when construction or execution fails.

Available credentials never influence selection. Missing/invalid binding,
disabled egress, missing dependency/credential, or absent OAuth adapter maps to
`AGENT_RUNTIME_NOT_CONFIGURED`. Timeout, rate limit, network, or SDK failure
after a call begins maps to `AGENT_PROVIDER_FAILED`. Neither condition may
fall back to another provider or fake output.

Safe diagnostics expose only `provider_profile:model_id`. Credentials, broker
responses, credential-bearing endpoints, and raw SDK objects are forbidden.

## External-egress payload

The owner permits external processing, but the provider receives exactly one
registered strict request for the invoked competence: generic
`ProviderRequestV1`, FT-009 `VisionProviderRequestV1` plus its single in-memory
media attachment, FT-009 `PlantStateProviderRequestV1`, FT-010
`HydroponicsAdvisorProviderRequestV1`, FT-011
`SafetyGateProviderRequestV1`, or FT-012
`TaskFollowUpProviderRequestV1`, or FT-013
`CompanionProviderRequestV1`. Every request keeps project-owned
definition/schema instructions and its exact subject allowlist. No adjacent
executor argument or hidden metadata may add business/context fields beyond
the explicit Vision media value.

It must not receive ActorContext, session/account/membership objects, tokens,
cookies, headers, provider credentials, UI Feed, raw chat, admin notices,
timeline replay, provider history, hidden reasoning, or local absolute paths.
Governance content is governed by each registered request's exact typed
allowlist rather than a blanket approval-status prohibition; it remains
untrusted and grants no domain or publication authority.
Photo data remains excluded from generic `ProviderRequestV1`. FT-009 permits
one catalog-authorized, freshly verified in-memory image only through
`vision-observation-runtime.md`; version 1 requires the existing `gemini`
profile and fails closed for other profiles without fallback. FT-010 permits
only the PostgreSQL-derived request from `hydroponics-advisor-runtime.md`;
project-computed freshness is policy metadata, not model-selected evidence or
reusable authorization. FT-011 permits only the five-field pending-message
candidate from `safety-gate-runtime.md`; Farm/Plant, ActorContext, source refs,
evidence, approval state, and downstream routes stay outside provider egress.

FT-012 permits only the strict task/outcome/evidence record union from
`task-follow-up-runtime.md`. Task display text remains a typed untrusted
quotation; Farm/Plant identity, ActorContext, session/account/membership/grant,
raw chat, UI Feed, Bus/Timeline replay, approval state, prompts, caller refs,
and arbitrary evidence payloads remain forbidden. The model may propose only
`check|measurement|follow_up`; no provider field can create action, approve,
complete, record an Outcome, or mutate Plant state.

FT-013 permits only the strict active Plant, selected open issue, latest
check-in, and latest manual-measurement record union from
`companion-runtime.md`. It excludes ActorContext, raw chat, UI/Bus/Timeline
replay, raw prior proposals/decisions, and caller prompts. The model may propose
only a typed human-attention/proposal candidate with
`discussion_only|check|measurement|follow_up|none`; it cannot create a
DecisionRecord, approve/reject, create `action`, mutate Plant state, or bypass
the project classifier/governance transaction.

The selected persisted open issue's normalized `summary_text` is permitted
inside the exact
`companion_issue` record of `CompanionProviderRequestV1` for
`target_mode=existing_issue`. The assembler may copy it only from the current
PostgreSQL issue whose Plant, `issue_id`, open status, and `record_version`
match the authorized explicit command. `target_mode=new_issue` carries no issue
or issue summary. This field is non-authoritative context: sending it grants no
approval, DecisionRecord, Task, Safety, Plant-state, Bus, or agent-context
authority. It does not permit attention/proposal/rationale/decision text,
proposal history, UI/Timeline copies, caller-supplied summaries, or arbitrary
governance fields. No generic request/schema, persisted egress receipt, or new
approval pipeline is added by this rule.

For this competence, "latest" is not inherited from the generic independent
pH/EC assembler: Companion selects the check-in by
`(recorded_at DESC,check_in_id DESC)` and exactly one manual-measurement row by
`(measured_at DESC,measurement_id DESC)`, without merging values from different
rows. The complete production proposal path resolves two explicit bindings
from the same deployment map: `companion` for the proposal candidate and
`safety_gate` for the required persisted project classification. Each may use
its own DeepSeek/Gemini profile/model id and matching credential; selection,
failure, or missing configuration never falls back between them.

Provider request/response bodies are never persisted. Sanitized audit may
record only fields allowed by the Timeline Event contract.

## Product-definition ownership

FT-007 supplies the stable eight-member roster metadata, resolver seam,
provider profiles, and provider-neutral runtime. FT-009 through FT-014 add the
complete runtime definitions, detailed instructions, triggers, claim
restrictions, and effects without changing roster identity.

The FT-007 credentialed smoke resolves an explicit DeepSeek or Gemini transport
and uses an isolated test-only `runtime_contract_smoke` definition through the
test seam. It proves production provider transport over actual persisted Plant
data, but is absent from production definition resolution and does not satisfy
REQ-011 product-agent acceptance.

The test harness resolves that transport only from:

- `AGENT_REAL_SMOKE=1`;
- `AGENT_REAL_SMOKE_PROFILE=deepseek | gemini`;
- `AGENT_REAL_SMOKE_MODEL_ID`, validated by the same model-id rules;
- `AGENT_EXTERNAL_EGRESS_ENABLED=true` and the matching provider credential.

These keys construct an explicit test-only binding passed to the production
provider factory. They are never read by application production composition,
cannot select `chatgpt_oauth`, cannot add a roster member, and cannot satisfy a
product-agent binding. Deterministic tests separately prove the canonical
`AGENT_MODEL_BINDINGS_JSON` resolver.

Smoke acceptance follows the exact Agent Runtime outcome matrix: only audited
`envelope_ready` or strict audited `model_silent` is accepted. Every other
outcome, skip/xfail, fake, fallback, or unaudited result fails.

## Verification

Tests must prove:

- all eight canonical ids can resolve independently through explicit bindings;
- malformed/unknown/blank configuration rejects atomically;
- an unbound agent, disabled egress, missing dependency/credential, or absent
  OAuth adapter fails before provider I/O;
- callers cannot override provider/model and failures never cross-fallback;
- DeepSeek/Gemini constructors receive the exact deployment model id and no
  hardcoded default;
- `chatgpt_oauth` uses only an approved injected adapter and never Codex,
  browser, or `OPENAI_API_KEY` credential substitution;
- outbound object graphs contain only the typed allowlist;
- outbound-spy snapshots match the exact `ProviderRequestV1` shape and record
  order, and prove authorization/ActorContext/session/role/grant data is absent;
- competence-specific outbound snapshots match the registered Vision, Plant
  State, Hydroponics Advisor, Safety Gate, Task and Follow-Up, and Companion
  request allowlists without
  widening generic `ProviderRequestV1`;
- Companion outbound snapshots prove an authorized existing-issue request
  carries exactly the persisted matching `companion_issue.summary_text`, a
  new-issue request carries none, and no attention/proposal/rationale/decision,
  UI/Timeline, caller-supplied, or other field outside the registered request
  allowlist crosses egress;
- logs, timeline, pytest output, and task evidence contain no credentials or
  raw provider payload;
- an explicitly enabled DeepSeek or Gemini smoke invokes exactly one real
  provider through the isolated test-only definition and cannot pass by skip,
  xfail, mock executor, canned output, fallback, blocked/failed outcome, or
  unaudited result, and satisfies the Agent Runtime smoke matrix.

## External compatibility evidence

- [Agno DeepSeek provider](https://docs.agno.com/models/providers/native/deepseek/overview)
- [Agno Google Gemini provider](https://docs.agno.com/models/providers/native/google/overview)
- [OpenAI API authentication](https://platform.openai.com/docs/api-reference/authentication)
- [OpenAI Codex sign in with ChatGPT](https://help.openai.com/en/articles/11381614-api-codex-cli-and-sign-in-with-chatgpt)

These references describe external compatibility only; this project contract
owns runtime behavior.
