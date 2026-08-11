---
description: Strict provider-neutral Dataset Governance and Training Data Curator agent input, advisory result, and curator gate contract for FT-014.
status: active
type: interface_contract
last_updated: 2026-08-12
source_of_truth:
  - .memory-bank/features/FT-014-dataset-governance-trainability.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/domains/dataset-governance.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
---
# Dataset Agents Runtime

## Scope

Defines the provider-neutral runtime for the two canonical roster agents
owned by FT-014: `dataset_governance` (Dataset Governance Agent) and
`training_data_curator` (Training Data Curator Agent). Both produce strict
typed advisory results over one existing authorized Dataset Candidate.
Neither result is lifecycle, quality, split, or trainability authority: the
server-owned curator gate in
[states/dataset-governance.md](../states/dataset-governance.md#ft-014-transition-authority)
alone may apply a `curator_auto` confirmation from canonical row state.

## Registered advisory-only exception

Architecture decision AD-011 registers these two roster agents as the only
current advisory-only exception to generic Agent Runtime. Their results have no
MVP MessageEnvelope/Safety/Bus/UI consumer, so they use
`runtime_route=dataset_advisory_v1` fixed by the immutable roster definition.
The caller, model, provider configuration, and missing binding cannot select or
change that route.

The route reuses the shared provider binding resolver, narrow executor seam,
test-only fake/spy injection, redaction, and current authorization helpers. It
does not construct generic `ProviderRequestV1`, `AgentModelResultV1`,
`AgentRuntimeOutcomeV1`, or MessageEnvelope. Dataset Governance owns the
application command, candidate locks, advisory writes, and any later
server-owned transition; Agent Runtime Core and the provider adapter own none
of those mutable fields.

## Out of scope

- Any HTTP boundary or public agent endpoint; invocation is an explicit
  internal application call over an existing candidate (operator decision D1);
- MessageEnvelope, Safety classification, Agent Chat Bus, or UI Feed
  publication — dataset agent results have no downstream consumer route in
  MVP (decision D6);
- candidate creation, evidence wiring, and lifecycle transactions, owned by
  [.memory-bank/domains/dataset-governance.md](../domains/dataset-governance.md);
- `gold` designation by the model, `split` assignment, export, fine-tuning,
  model evaluation, schedulers, workers, tools, RAG, or agent memory;
- generic `ProviderRequestV1` changes, caller prompts, raw provider
  persistence, or any production fake/canned/fallback output.

## Related specs

- [.memory-bank/contracts/agent-runtime-adapter.md](agent-runtime-adapter.md):
  shared provider binding, post-model guard, sanitized audit, and closed
  failure semantics.
- [.memory-bank/contracts/agent-model-provider-profiles.md](agent-model-provider-profiles.md):
  provider-neutral executor, typed egress, fail-closed production, and the
  deferred selected-endpoint milestone.
- [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
  canonical `dataset_governance` and `training_data_curator` identities.
- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md):
  lifecycle, transition table, and the strong-evidence policy.
- [.memory-bank/domains/dataset-governance.md](../domains/dataset-governance.md):
  candidate persistence and the advisory/transition seams.

## Module and command boundary

Implementation lives under `backend/app/dataset_governance/` and reuses the
project provider factory and current-authorization helpers. It appends the
dedicated sanitized `dataset_agent_runtime_decided` Timeline event under the
closed matrix below; generic `agent_runtime_decided` remains unchanged.

The internal `DatasetAgentCommandV1` contains exactly:

- `schema_version=1`;
- application-generated UUIDv4 `run_id`;
- timezone-aware UTC `requested_at`;
- service-side `actor_context`;
- requested UUID `plant_id` and `candidate_id`;
- `agent_id=dataset_governance|training_data_curator`;
- `trigger_kind=dataset_candidate_created|manual_review`.

`manual_review` is an internal application invocation over an existing
candidate, not a public endpoint. Callers cannot submit candidate rows,
evidence payloads, prompts, model/provider choice, output schema, lifecycle
or trainability fields, authorization snapshots, or device data.

`run_id` is the command identity. Before model execution the runtime computes
`command_sha256` from compact sorted-key JSON containing exactly the command
schema version, `run_id`, canonical `requested_at`, ActorContext
`request_id|session_id|account_id|farm_id|membership_id`, `plant_id`,
`candidate_id`, `agent_id`, and `trigger_kind`. Current role,
membership/grant status, permission results, auth provenance, provider data,
and candidate output are not fingerprint inputs; their owning guards remain
current authority.

## Provider requests version 1

`DatasetGovernanceProviderRequestV1` / `TrainingDataCuratorProviderRequestV1`
are strict objects constructed server-side from exactly:

- `schema_version`, `run_id`, `requested_at`, `agent_id`, `plant_id`,
  `candidate_id`;
- a typed candidate snapshot: `candidate_status`, `candidate_origin`,
  `quality_tier`, `follow_up_seen`, `corrected`, evidence-ref kinds and
  counts only (never raw evidence payloads, absolute paths, filenames, or
  secrets);
- the closed policy context: the exact strong-evidence policy identifier and
  the MVP `agent_labeled` guard flag.

Callers and models cannot inject evidence bodies, UI/chat text, manifests, or
timeline snapshots. Request construction follows the redaction rules in
[.memory-bank/contracts/evidence-redaction.md](evidence-redaction.md).

## Typed results version 1

`DatasetGovernanceAssessmentV1` (agent `dataset_governance`):

- `schema_version=1`, `run_id`;
- `assessment=eligible_for_curator_review|needs_human_review|policy_violation`;
- `violation_codes`: closed string set, empty unless `policy_violation`;
- `assessment_notes`: short bounded text, non-authoritative.

`TrainingDataCuratorDecisionV1` (agent `training_data_curator`):

- `schema_version=1`, `run_id`;
- `curator_decision=selected|deferred|rejected|silent` — the curator usually
  stays silent; `silent` persists no decision;
- `curator_notes_ref`: optional short bounded pointer text.

Results are strictly validated; extra fields, unknown enum values, or any
attempt to supply `candidate_status`, `quality_tier`, `split`,
`confirmation_source`, or `can_train_on` reject the result.

## DatasetAgentRuntimeOutcomeV1

Every accepted explicit attempt returns one strict object with exactly:

- `schema_version=1`, `run_id`, `agent_id`, and `candidate_id`;
- `outcome_kind=advisory_ready|model_silent|context_denied|runtime_not_configured|provider_failed|output_invalid|post_io_guard_denied|policy_blocked|audit_failed`;
- `status=advisory_ready|silent|blocked|failed`;
- `reason_code` and nullable stable `error_code`;
- nullable `validated_result`, `event_ref`, and safe `model_ref`;
- `provider_call_status=not_attempted|completed|failed`;
- `audit_status=appended|failed`; and
- `curator_gate_result=not_applicable|not_requested|confirmed|policy_blocked`.

Unknown fields are rejected. The exact matrix is:

| `outcome_kind` | Status | Validated result | Provider | Audit | Curator gate |
|---|---|---|---|---|---|
| `advisory_ready` | `advisory_ready` | matching strict result | `completed` | `appended` | governance: `not_applicable`; curator deferred/rejected: `not_requested`; curator selected: `confirmed` |
| `model_silent` | `silent` | matching strict silent curator result | `completed` | `appended` | `not_requested` |
| `context_denied` | `blocked` | null | `not_attempted` | `appended` | `not_applicable` |
| `runtime_not_configured` | `failed` | null | `not_attempted` | `appended` | `not_applicable` |
| `provider_failed` | `failed` | null | `failed` | `appended` | `not_applicable` |
| `output_invalid` | `blocked` | null | `completed` | `appended` | `not_applicable` |
| `post_io_guard_denied` | `blocked` | null | `completed` | `appended` | `not_applicable` |
| `policy_blocked` | `blocked` | null | `completed` | `appended` | `policy_blocked` |
| `audit_failed` | `failed` | null | `not_attempted|completed|failed` | `failed` | `not_applicable|not_requested|confirmed|policy_blocked` |

On `audit_failed`, `curator_gate_result` records the attempted gate-result value
the failing run would have recorded had the audit append succeeded: `not_applicable`
when no gate is attempted, `not_requested` for silent/deferred/rejected runs, and
`confirmed`/`policy_blocked` on the selected-gate application surface — so an
observer can tell whether a gate was attempted. The audit event always has the
`audit_status=failed` value and no event ref.

`validated_result` exists only for `advisory_ready|model_silent`. A selected
curator result returns `advisory_ready` only when its current-run advisory row
and `curator_auto` transition commit together; a policy failure returns
`policy_blocked` and rolls both back. `audit_failed` returns no result or event
ref and rolls back every pending advisory/lifecycle mutation. Expected failures
never masquerade as model silence.

## Invocation flow and curator gate

1. The application invokes one agent run explicitly over one existing
   candidate (`dataset_candidate_created` after creation commit, or internal
   `manual_review`); page reads, startup, schedulers, and domain events are
   not triggers.
2. Pre-model guards revalidate current ActorContext, Farm/Plant identity,
   Plant-active state, grant, and candidate existence; any guard failure is a
   closed `context_denied` outcome with sanitized audit and no model call.
3. The provider-neutral executor runs; production remains unbound and
   fail-closed without a selected endpoint, exactly as in
   [agent-model-provider-profiles.md](agent-model-provider-profiles.md).
4. The typed result is validated. After every schema-valid provider result,
   the runtime reloads and locks the original LocalSession, Account,
   Membership, Plant/grant, and candidate version before any write. Denial or
   candidate change returns `post_io_guard_denied` with no advisory/lifecycle
   mutation.
5. A valid non-`silent` curator result persists only the current-run
   `curator_decision`/`curator_notes_ref` identity through the advisory seam in
   [domains/dataset-governance.md](../domains/dataset-governance.md).
   Governance assessments persist nothing; they are recorded only through
   sanitized audit.
6. The server-side curator gate then evaluates the canonical strong-evidence
   policy. Only when the persisted current-run `curator_decision=selected`
   and every policy condition holds does the transition authority apply a
   `curator_auto` confirmation in the same transaction; model wording is never
   a policy input. Policy failure rolls back the current-run advisory write.
7. Every accepted explicit attempt — success, silence, validation failure,
   pre/post-I/O guard failure, unbound runtime, provider failure, or policy
   failure — attempts exactly one sanitized
   `dataset_agent_runtime_decided` append. No generic runtime event is written.

## Failure catalog

Closed typed failures only: `dataset_agent_context_denied`,
`dataset_agent_runtime_not_configured`, `dataset_agent_provider_failed`,
`dataset_agent_output_invalid`, `dataset_agent_post_io_guard_denied`,
`dataset_confirmation_policy_violation`, and
`dataset_agent_audit_failed`. Safe reason detail distinguishes unauthorized,
archived Plant, candidate not found/conflict, provider failure, and invalid
result without exposing protected existence or raw exceptions. No failure
writes advisory, evidence, lifecycle, quality, split, or trainability fields.

## Verification

See [.memory-bank/testing/dataset-governance.md](../testing/dataset-governance.md).
Deterministic fake/spy executor tests prove: strict request construction and
redaction; strict result validation including anti-assignment rejection;
the closed outcome/audit matrix; advisory-only persistence; the curator gate
(selected plus policy pass
confirms ordinary raw candidates; gold, `agent_labeled`, weak-evidence, and
non-selected paths never confirm); explicit-trigger-only invocation;
fail-closed unbound production; and the absence of any
MessageEnvelope/Bus/UI/Safety effect.
