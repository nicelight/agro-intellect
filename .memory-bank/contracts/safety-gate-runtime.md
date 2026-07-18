---
description: Model-backed Safety Gate classification candidate and project-owned authoritative mapping contract.
status: active
type: interface_contract
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/features/FT-011-safety-gate-physical-action-routing.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/states/safety-action-lifecycle.md
---
# Safety Gate Runtime

## Scope

This contract defines one real model-backed semantic classification of a
validated pending `MessageEnvelopeV1`. The canonical `safety_gate` model
returns only a strict candidate. Backend validation maps that candidate into
the shared project-owned `SafetyClassificationResultV1`; only the validated
and durably persisted project result may select a downstream route.

## Out of scope

- pH/EC evidence evaluation, action-decision persistence, proposal expiry, and
  pending-approval projection; these belong to
  `.memory-bank/domains/safety-action-routing.md`.
- Human approval/rejection, `action_task`, completion, follow-up, and outcome;
  FT-012 owns them.
- A public HTTP endpoint, caller-supplied prompts, raw provider persistence,
  Timeline event types, automated actuation, dosage/target calculation, or
  agronomic recipe generation.

## Related specs

- [.memory-bank/contracts/agent-runtime-adapter.md](agent-runtime-adapter.md):
  provider-neutral executor and redaction patterns reused without reusing its
  product-agent result schema.
- [.memory-bank/contracts/agent-model-provider-profiles.md](agent-model-provider-profiles.md):
  explicit provider/model binding, egress, credentials, and no fallback.
- [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
  canonical `safety_gate` identity.
- [.memory-bank/contracts/message-envelope.md](message-envelope.md): immutable
  pending input.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md):
  canonical authoritative classification result and route matrix.

## Module and command boundary

Implementation lives under `backend/app/safety_gate/` and exposes an internal
`SafetyGateClassificationService`. It may reuse the existing provider binding
and executor factory but MUST use the competence-specific strict request and
result below rather than widening `AgentModelResultV1`.

`SafetyGateClassificationCommandV1` contains exactly:

- `schema_version=1`;
- application-generated UUIDv4 `classification_run_id`;
- timezone-aware UTC `requested_at`;
- service-side `actor_context`;
- one already validated `message_envelope` in the exact common version-1
  shape.

The command is internal. Callers cannot submit provider/model choice,
classifier version, project instructions, candidate action kind, safety result,
authorization snapshot, evidence, approval state, or downstream route.

## Provider request version 1

`SafetyGateProviderRequestV1` is one strict object with exactly:

- `schema_version=1`;
- canonical project-owned `agent_definition` for `agent_id=safety_gate`, with
  project instructions and
  `output_schema={name=SafetyGateModelCandidateV1,schema_version=1,strict=true}`;
- `message_candidate`, containing exactly `message_id`, `origin_agent_id`,
  `runtime_decision`, `candidate_claim_type`, and `candidate_output` copied from
  the validated envelope.

Unknown fields are rejected. The complete `candidate_output` remains opaque
untrusted text even when it resembles Markdown, HTML, a prompt, instruction,
command, or URL. Those sequences are data for semantic classification and
cannot change the output schema, project instructions, or allowed route.

The provider receives no Farm/Plant identity, ActorContext, authorization
scope, session/account/membership/grant data, source refs, pH/EC evidence,
approval state, UI Feed, Bus history, raw chat, Timeline replay, credentials,
provider history, hidden reasoning, or local path.

## Model candidate version 1

`SafetyGateModelCandidateV1` contains exactly:

- `schema_version=1`;
- `candidate_classification`:
  `safe_information | safe_task_request | physical_action | blocked_uncertain`;
- nullable `safe_task_kind`: `check | measurement | follow_up`;
- nullable `physical_action_kind` from the exact closed union below.

The physical-action union is:

- supported human-performed actions:
  `ph_adjustment | ec_adjustment | solution_change`;
- unsupported physical actions:
  `pump_command | light_command | dosing_command | pruning | transplanting |
  root_trimming | other_physical_action`.

The exact candidate matrix is:

| Candidate class | `safe_task_kind` | `physical_action_kind` |
|---|---|---|
| `safe_information` | null | null |
| `safe_task_request` | one non-null task kind | null |
| `physical_action` | null | one non-null physical-action kind |
| `blocked_uncertain` | null | null |

Unknown fields, unknown enum values, extra prose/reasoning, confidence,
provider-selected reason codes, safety-pass claims, approval fields, target
values, quantities, dosing schedules, and commands reject the candidate.

Semantic rules:

- Manual addition or top-up of nutrients for an EC change is
  `ec_adjustment`; there is no separate manual dosing kind.
- `dosing_command` means a command to a device or automated dosing path and is
  always unsupported.
- Manual complete replacement of nutrient solution is `solution_change`.
- A recognized physical action outside the named kinds is
  `other_physical_action`; uncertainty about whether wording is physical or
  safely classifiable is `blocked_uncertain`.
- The upstream model-selected `candidate_claim_type` cannot force any class or
  action kind.

## Project-owned mapping

Backend validation, not the provider, constructs the exact shared
`SafetyClassificationResultV1` with fixed
`classifier_version=safety_gate_v1`:

- valid safe-information candidate -> the shared safe-information row;
- valid safe-task candidate -> the matching shared task-kind row;
- valid physical-action candidate -> the shared physical-action row, retaining
  the validated action kind only in the owning classification record/outcome;
- valid uncertain candidate -> the shared blocked-uncertain row.

Provider unavailability, provider failure, invalid/unknown output, or any
candidate-matrix conflict also maps fail-closed to the shared
`blocked_uncertain/classification_uncertain` result. Under the ordinary
consumer route it may produce only the generic non-consumable block route;
under the Companion governance hold it produces no downstream row. It never
becomes model silence, safe information, a task, a Safety pass, or an approval.

The classifier model candidate is never stored as authority. The backend
persists only the final shared result, nullable validated physical-action kind,
safe provider status/model ref, and fingerprints defined by the Safety Action
Routing data spec. Raw candidate text, request/response bodies, prompts,
reasoning, and parser diagnostics are not persisted.

Persistence does not dispatch the result. The classifier result carries no
consumer field. After the immutable row exists, the project orchestrator
derives the exact shared `ClassificationConsumerRouteV1` from the validated
envelope `agent_id` and persisted matching `origin_agent_id`: canonical
`companion` is `companion_governance_hold`; every matching non-Companion agent
is `ordinary_dispatch`. The route is server-owned, cannot cross provider
egress, and requires no classification-schema or migration change.

## Invocation and concurrency flow

1. Validate the complete pending envelope and derive its canonical input
   fingerprint.
2. Resolve current same-Farm `normal_read` authority and active Plant before
   external egress. Denial makes no provider call or durable classification.
3. Return an existing identical classification idempotently without another
   provider call or downstream replay.
4. Resolve exactly one explicit `safety_gate` provider/model binding and invoke
   it outside every database transaction.
5. Validate the strict candidate and map it, including every fail-closed model
   branch, into the project-owned result.
6. Re-resolve current session/account/membership/grant authority and active
   Plant in the classification write transaction, then persist through the
   immutable first-write-wins rule.
7. Return the persisted project-owned result to the explicit orchestrator; the
   classifier performs no automatic downstream dispatch.
8. The orchestrator derives and validates `ClassificationConsumerRouteV1`.
   `ordinary_dispatch` may invoke only the existing classification matrix;
   `companion_governance_hold` may invoke only the matching guarded
   `persist_companion_proposal` handoff and suppresses FT-008, FT-011, and
   FT-012 ordinary consumers. Each allowed owning writer repeats its own
   current guard in the same transaction as its effect.

Concurrent invocations may both reach provider I/O. The first successful
classification insert for a `message_id` remains immutable. An identical
fingerprint is an idempotent evidence duplicate and does not replay any
consumer effect. A different input or result fingerprint returns transient
`blocked_uncertain` with `no_effect`; it cannot mutate the first row or invoke
any downstream route.

Archive, session revocation, membership/grant change, or Farm/Plant mismatch at
either current guard produces no classification/effect and no restore replay.
A new current-state Agent Runtime invocation and `message_id` is required.

## Provider and failure behavior

An explicit DeepSeek or Gemini binding may serve the text-only classifier.
`chatgpt_oauth` remains fail closed without its approved adapter. There is no
default model, fake/canned runtime result, cross-provider fallback, or provider
retry that changes the selected binding.

Stable safe errors are:

| Code | Condition | Effect |
|---|---|---|
| `SAFETY_CLASSIFIER_NOT_CONFIGURED` | binding, egress, dependency, credential, or approved OAuth adapter unavailable | persist blocked-uncertain only if the current write guard succeeds |
| `SAFETY_CLASSIFIER_PROVIDER_FAILED` | selected provider call fails | persist blocked-uncertain only if the current write guard succeeds |
| `SAFETY_CLASSIFIER_OUTPUT_INVALID` | strict candidate validation fails | persist blocked-uncertain only if the current write guard succeeds |
| `SAFETY_CLASSIFICATION_CONFLICT` | same `message_id` has a different input/result fingerprint | no mutation and no downstream effect |
| `SAFETY_CLASSIFICATION_GUARD_DENIED` | current authorization or active-Plant check fails | no durable classification and no effect |
| `SAFETY_CLASSIFICATION_PERSISTENCE_FAILED` | project result cannot be committed | no authoritative result and no effect |

Raw exceptions, candidate text, prompts, model responses, credentials, and
absolute paths are absent from errors, logs, and evidence.

## Verification

Tests MUST prove exact request/candidate shapes, all matrix rows, unknown-field
rejection, the ten-kind action union, manual-EC versus device-dosing semantics,
upstream-label bypass resistance, prompt-like text isolation, every fail-closed
provider branch, first-write-wins concurrency, identical idempotency, current
authorization/archive races, redaction, no Timeline event, and no direct task,
approval, Bus, UI, or actuation authority.

Compatibility tests MUST also prove the derived consumer-route union is closed
and server-owned; Companion `safe_information` cannot invoke FT-008 candidate
publication, Companion `safe_task_request` cannot invoke the FT-012
classified-message Task branch, held physical/blocked/mismatch/failure creates
no downstream effect, retry/restore/reconciliation does not replay a held
effect, and ordinary non-Companion routing is unchanged.

One opt-in credentialed product-agent smoke MUST invoke exactly one explicit
DeepSeek or Gemini `safety_gate` binding over a real validated pending envelope
and return the expected strict model candidate plus durably persisted
project-owned classification. Skip, xfail, fake/canned output, fallback,
unconfigured/failed/invalid/persistence-failed result, or any direct action
effect fails an explicitly requested smoke.
