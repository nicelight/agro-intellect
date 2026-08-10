---
description: Provider-neutral Agent Runtime binding, typed egress, fail-closed production, and future endpoint selection contract.
status: active
type: interface_contract
last_updated: 2026-08-10
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/dataset-agents-runtime.md
  - .memory-bank/contracts/evidence-redaction.md
---
# Agent Model Provider Boundary

## Scope

This contract defines the provider-neutral boundary between project-owned
Agent Runtime and a model executor. It owns strict binding resolution,
test-only executor injection, typed egress, fail-closed production behavior,
failure normalization, and the route to one future explicitly selected
OpenAI-compatible endpoint.

No provider, model, base URL, authentication mode, credential, or egress
permission is selected for the current code phase. Gemini is not planned.
Installing Agno or another SDK does not make an endpoint selected or prove a
real integration.

## Out of scope

- selecting a provider, model, base URL, account, credential, or cost budget;
- live network calls or credentialed smoke as current code-phase closure;
- provider account creation, billing automation, browser-login automation,
  token scraping, or undocumented credential reuse;
- hardcoded/default endpoints, model ids, fallback chains, provider history,
  model memory, tools, RAG, or Team coordination.

## Related specs

- [.memory-bank/contracts/agent-runtime-adapter.md](agent-runtime-adapter.md):
  invocation, validation, current authorization guard, audit, and handoff.
- [.memory-bank/contracts/evidence-redaction.md](evidence-redaction.md):
  secret-safe diagnostics and evidence.
- [.memory-bank/runbooks/agent-runtime-providers.md](../runbooks/agent-runtime-providers.md):
  current fail-closed operation and the future integration milestone.
- [.memory-bank/testing/agent-runtime.md](../testing/agent-runtime.md):
  deterministic executor and future integration verification.

## Current binding state

Production composition has no accepted provider binding in the current code
phase. Resolving an unbound competence returns
`AGENT_RUNTIME_NOT_CONFIGURED` before network I/O. It MUST NOT:

- select a provider, model, or base URL by default;
- infer a binding from installed SDKs or available environment variables;
- read ChatGPT, Codex, browser, CLI, or IDE credential stores;
- retry another endpoint, substitute fake/canned output, or turn failure into
  model silence;
- accept provider/model/base-URL choice from an HTTP caller, UI, prompt, model
  output, or Plant data.

The future selection milestone will define the exact deployment configuration
shape. Current contracts and task cards MUST NOT invent environment names or
configuration fields that would preselect that decision.

## Provider-neutral executor seam

Every competence invokes one narrow `ModelExecutor`-style protocol:

- input is exactly the registered strict competence request;
- Vision may additionally supply exactly one service-side in-memory media
  value defined by `vision-observation-runtime.md`;
- output is one provider response passed only to the registered strict result
  validator;
- timeout, transport, rate-limit, endpoint, SDK, and parsing failures are
  normalized into the owning stable failure catalog;
- no request/response body, media bytes, prompt, hidden reasoning, credential,
  or raw exception becomes runtime authority or durable evidence.

Production uses only a future selected deployment executor. Tests may inject a
fake/spy executor explicitly through test dependency injection. The test seam
MUST NOT be reachable from production composition or silently selected when
configuration or execution fails.

## Typed egress

The executor receives exactly one registered strict request:

- generic `ProviderRequestV1`;
- `VisionProviderRequestV1` plus one verified in-memory media value;
- `PlantStateProviderRequestV1`;
- `HydroponicsAdvisorProviderRequestV1`;
- `SafetyGateProviderRequestV1`;
- `TaskFollowUpProviderRequestV1`; or
- `CompanionProviderRequestV1`;
- `DatasetGovernanceProviderRequestV1`; or
- `TrainingDataCuratorProviderRequestV1`.

No adjacent executor argument or hidden metadata may add Farm/Plant identity,
ActorContext, session/account/membership/grant state, authorization snapshots,
tokens, cookies, headers, credentials, UI Feed, raw chat, Bus/Timeline replay,
provider history, local absolute paths, or hidden reasoning. Vision media is
the sole binary exception and remains bound to its verified photo ref/hash.

Registered agent-specific governance fields are allowed only when their
owning contract lists them. They remain untrusted and grant no DecisionRecord,
Plant-state, Task, Safety, publication, or actuation authority.

### Registered advisory-only result route

`DatasetGovernanceProviderRequestV1` and
`TrainingDataCuratorProviderRequestV1` are the only registered requests whose
strict results do not enter generic `AgentRuntimeOutcomeV1` and
MessageEnvelope. Their owning
[Dataset Agents Runtime](dataset-agents-runtime.md#registered-advisory-only-exception)
contract defines the competence-local result/outcome and audit matrices.

This exception changes no provider selection or production binding rule. The
two requests use the same fail-closed binding resolver and narrow executor
protocol; tests may inject only explicit fake/spy executors. A valid result is
still untrusted advisory data. Only Dataset Governance may persist its exact
allowlisted advisory fields or invoke its server-owned lifecycle authority.
The provider adapter cannot create a Dataset Candidate, associate evidence,
set lifecycle/quality/split/confirmation/trainability, or produce
MessageEnvelope, Safety, Bus, or UI Feed effects.

## Failure and timeout contract

- Missing production binding or future binding prerequisites returns the
  owning `*_NOT_CONFIGURED` result before executor I/O.
- Timeout, network, rate-limit, endpoint, or SDK failure after executor start
  returns the owning `*_PROVIDER_FAILED` result.
- Strict output validation failure returns the owning `*_OUTPUT_INVALID`
  result.
- No failure is relabeled as `silent`, retried against another endpoint, or
  replaced by fake/canned output.
- Current session/membership/grant/active-Plant authorization is rechecked
  after executor I/O and again at every owning write boundary.

Deterministic tests MUST use fake/spy executors to cover success, timeout,
transport failure, malformed output, current-guard denial, audit failure,
redaction, and no-fallback behavior without network access.

## Safe evidence

Current deterministic evidence may include only strict request/result
snapshots with synthetic values, call counts, timeout/error branch, safe ids
and refs, and redacted stable error codes. It MUST NOT claim a real provider,
model, image interpretation, response, network call, or credential was
verified.

The future selected-endpoint milestone may add a safe endpoint/model reference
defined by that milestone. It still MUST NOT retain credentials, base URLs
with secrets, request/response bodies, media bytes, prompts, raw provider
objects, or hidden reasoning.

## Future OpenAI-compatible integration gate

After the owner selects an endpoint, the existing runbook/testing milestone
must define and verify:

1. exact provider, model, base URL, authentication, egress, timeout, and cost
   budget decisions;
2. one real text response through a canonical competence;
3. one real image request using the accepted-photo integrity boundary;
4. representative provider errors and enforced timeout behavior;
5. redaction across logs, Timeline, test output, and evidence;
6. observed/requested cost or usage against the approved budget; and
7. unchanged no-fallback/no-fake and no-direct-authority rules.

This gate is `deferred/manual/not_applicable_for_current_code_phase`. It is not
a runnable queue task and is not closure evidence for FT-009 through FT-013.

## Verification

Current code-phase tests prove strict binding absence, explicit test injection,
request allowlists, media identity, timeout/error normalization, post-I/O
authorization, redaction, and absence of production fallback. The future
integration milestone owns every real endpoint claim.
