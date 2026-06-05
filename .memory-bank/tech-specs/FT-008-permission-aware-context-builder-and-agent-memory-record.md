---
description: Feature-local SDD tech spec for FT-008 permission-aware context builder, AgentMemoryRecord, retrieval, trust labels, and compaction.
status: active
feature_id: FT-008
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-008-permission-aware-context-builder-and-agent-memory-record.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - agents-best-practices
---
# FT-008 Permission-Aware Context Builder And AgentMemoryRecord Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for the shared
permission-aware context builder, `AgentMemoryRecord` schema semantics, retrieval and
write policy, trust labels, stale/supersede/archive handling, and compaction handoff.

This spec applies `agents-best-practices`: context is assembled just in time, memory is
scoped and source-ref backed, untrusted content stays labeled as data, and compaction is
an operational handoff rather than conversational prose.

## Scope

In scope:

- context package assembly for one `AgentHarnessRun`;
- allowed and forbidden context sources;
- AgentMemoryRecord lifecycle, fields, write validation, retrieval filtering, and
  non-authority semantics;
- trust/freshness labels and source-ref requirements;
- compaction handoff shape and cache-aware context ordering;
- permission, redaction, trace, and eval requirements for context/memory paths.

Out of scope:

- canonical harness loop, tool registry, permission engine, and budget controller owned
  by FT-007;
- MessageEnvelope, Bus, and UI Feed payload variants owned by FT-009;
- real provider/model adapter and profile activation choices owned by FT-010;
- Plant State trust-promotion and advisor behavior owned by FT-011;
- Safety Gate action taxonomy, approvals, action-task unlock, and task outcome state
  owned by FT-012 and FT-013;
- full RAG, vector database, or broad external connector retrieval before a later spec
  promotes that scope.

## Context Builder Contract

The context builder is the only route by which product agents receive runtime state,
evidence refs, approved governance summaries, and long-term memory.

Minimum `AgentContextPackage` semantics:

```yaml
context_package_id: string
run_id: string
agent_id: string
agent_profile_version: string
farm_id: string
plant_id: string | null
actor_context_ref: string
plant_access_result: granted | denied | not_applicable
instruction_refs: []
allowed_context_sources: []
excluded_context_sources: []
context_items:
  - item_ref: string
    source_family: runtime_state | bus_event | measurement | observation | photo_ref | task | approval | outcome | governance_summary | agent_memory | trace_summary
    trust_label: trusted | semi_trusted | untrusted_data
    freshness_label: fresh | stale | unknown | not_applicable
    authority_role: policy | runtime_authority | evidence_ref | governance_summary | memory_non_authority | presentation_excluded
    source_refs: []
    evidence_refs: []
compaction_ref: string | null
redaction_status: redacted | no_sensitive_fields
trace_ref: string
```

Assembly rules:

- resolve ActorContext before any context lookup;
- filter Plant-scoped records by Farm, Plant, Plant state, PlantAccessGrant, role
  preset, AgentProfile, allowed source family, freshness/trust labels, and redaction
  policy;
- include PostgreSQL/read-model runtime state and refs as authority where the owning
  feature says they are authoritative;
- include timeline, photo, task, approval, outcome, and Bus refs only as scoped evidence
  or working events, never by replaying them into mutable state;
- include approved governance summaries only after their owning later features create
  valid compact typed records;
- include AgentMemoryRecord entries only through the retrieval policy below;
- label untrusted user-entered, uploaded, provider-returned, connector-returned, or
  retrieved text as data, not instructions.

## Forbidden Context Sources

The context builder must exclude:

- UI Feed cards, display payloads, spoiler notes, UI markdown, and screenshots;
- raw chat history as fact;
- raw provider output, hidden model reasoning, provider memory, and Agno events;
- raw CompanionProposal text/rationale and unapproved governance discussion;
- admin UI notices and audit-view markdown;
- timeline replay as current mutable state;
- local files, logs, or connector output containing secrets/auth material;
- unauthorized Farm/Plant data.

If forbidden content appears inside an otherwise allowed source, the builder must
redact, truncate, downgrade, or reject the item before context assembly.

## AgentMemoryRecord Shape

PostgreSQL/read model or a dedicated local table under the same authority owns
AgentMemoryRecord metadata and content. Hidden provider memory is never product memory.

Minimum semantics:

```yaml
memory_id: string
schema_version: string
agent_id: string
farm_id: string
plant_id: string | null
created_by_run_ref: string
created_from_observation_ref: string
source_refs: []
evidence_refs: []
summary: string
structured_payload: object
claim_type: observation_summary | trend_hypothesis | missing_data_pattern | conflict_note | follow_up_hint | governance_summary_ref
trust_label: semi_trusted | untrusted_data
freshness_label: fresh | stale | unknown | not_applicable
authority_role: memory_non_authority
status: candidate | active | stale | superseded | archived | rejected
supersedes_memory_refs: []
superseded_by_memory_ref: string | null
visibility_scope:
  farm_id: string
  plant_id: string | null
  allowed_agent_ids: []
  source_actor_context_ref: string
created_at: datetime
last_retrieved_at: datetime | null
expires_or_review_after: datetime | null
trace_refs: []
redaction_status: redacted | no_sensitive_fields
```

Rules:

- memory is source-ref backed; candidate writes without source/evidence refs are
  rejected or remain non-retrievable;
- memory is scoped by agent, Farm, Plant, source ActorContext, PlantAccessGrant, and
  allowed AgentProfile visibility;
- memory stores bounded summaries and structured refs, not raw transcripts, hidden
  reasoning, raw provider output, UI Feed text, secrets, or oversized blobs;
- memory cannot confirm Plant state, unlock Safety Gate, create `action_task`, approve
  governance, or change dataset trainability by itself;
- stale, superseded, archived, rejected, unauthorized, or redaction-failed memory is
  excluded from ordinary retrieval unless an explicit diagnostic/admin route allows a
  redacted ref-only view.

## Memory Write Policy

Memory writes start as `candidate`.

Candidate activation requires:

1. valid AgentProfile and `AgentHarnessRun` refs;
2. source refs and evidence refs that the actor and profile were allowed to see;
3. no forbidden context source or secret/auth material;
4. claim type compatible with the AgentProfile competence boundary;
5. explicit trust/freshness labels;
6. trace ref for the write decision.

Activation may be automatic for low-risk source-ref summaries when validation passes.
Memory that would affect Plant confirmation, Safety Gate, physical actions, governance
authority, or dataset trainability remains non-authoritative and must wait for the
owning feature's human/follow-up/review rules.

## Retrieval Policy

Retrieval order is deterministic:

1. active trusted policy and AgentProfile instruction refs;
2. current authorized runtime state from PostgreSQL/read model;
3. fresh or unknown-freshness current evidence refs needed by the AgentProfile;
4. recent structured observations from the active run;
5. active AgentMemoryRecord entries matching agent/Farm/Plant/profile scope;
6. stale memory only when the AgentProfile explicitly needs historical trend context
   and the item is labeled stale in context;
7. redacted trace summaries for diagnostics when allowed.

Retrieval must filter out:

- denied or expired ActorContext;
- missing/revoked PlantAccessGrant;
- archived Plants in normal operation;
- source records not visible to the current actor/profile;
- memory whose source refs are no longer available to the current actor;
- unapproved governance content;
- memory that conflicts with current runtime state unless the context item is clearly
  labeled `conflict_note` or stale historical context.

Revoked access blocks future memory retrieval for that actor/context without deleting
retained audit/evidence.

## Trust, Freshness, And Authority Labels

Context items and memory entries use the same high-level labels:

- `trusted`: policy/spec/harness configuration or backend-owned approval decision;
- `semi_trusted`: internal runtime records and validated refs;
- `untrusted_data`: user-entered text, uploaded content, provider/connector output, or
  any freeform content included as data;
- `fresh`, `stale`, `unknown`, `not_applicable`: freshness labels supplied by the
  owning feature;
- `governance_summary`: approved compact governance fact derived from backend-owned
  DecisionRecord state; not Safety Gate authority and not general runtime authority;
- `runtime_authority`, `evidence_ref`, `memory_non_authority`, or
  `presentation_excluded`: authority role.

Compaction, summarization, or memory activation must not upgrade a trust label or
authority role.

## Compaction Handoff

Compaction creates a durable operational handoff ref for long contexts.

Minimum `AgentContextCompaction` contents:

```yaml
compaction_id: string
run_id: string
agent_id: string
objective: string
active_plan_ref: string | null
actor_context_ref: string
plant_access_summary: object
loaded_instruction_refs: []
active_approval_refs: []
pending_proposal_refs: []
source_refs_preserved: []
memory_refs_preserved: []
trust_freshness_summary: []
tool_observation_refs: []
trace_refs: []
open_blockers: []
next_safe_action: string
redaction_status: redacted | no_sensitive_fields
```

Rules:

- compaction preserves objective, scope, active approvals, pending proposals, source
  refs, memory refs, trust/freshness labels, and trace refs;
- compaction cannot erase or widen permissions;
- compaction cannot summarize untrusted content into trusted facts;
- compaction summaries visible to the model remain bounded and exclude hidden reasoning,
  raw provider output, UI Feed text, secrets, and auth material.

## Cache-Aware Ordering And Budgets

Context assembly should keep stable content before volatile content:

1. stable tool definitions and schemas selected by AgentProfile;
2. stable harness and AgentProfile instructions;
3. stable domain policies and feature-local source-of-truth refs;
4. compact prior event summaries and approved memory refs;
5. dynamic ActorContext, Plant scope, runtime state, evidence refs, latest observations,
   approvals, and user request.

Task decomposition may decide exact token/result limits, but every context build must
record context size, selected source counts, excluded source counts, redaction status,
and trace refs.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- build context for an authorized AgentHarnessRun;
- retrieve allowed AgentMemoryRecord refs for an agent/Farm/Plant scope;
- create candidate memory from a structured observation;
- validate/activate, mark stale, supersede, archive, or reject memory;
- create/read context compaction refs;
- run context/memory eval fixtures and redacted trace summaries.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-008 can be considered implemented:

- ActorContext and PlantAccessGrant filtering blocks unauthorized context and memory
  retrieval;
- revoked PlantAccessGrant blocks future memory retrieval without deleting retained
  audit/evidence;
- UI Feed, spoiler notes, raw chat, raw provider output, hidden reasoning, Agno events,
  unapproved proposals, admin UI text, and secrets cannot enter agent context;
- AgentMemoryRecord candidate without source refs, evidence refs, trace ref, or
  redaction success cannot become active retrievable memory;
- stale/superseded/archived/rejected memory is excluded or clearly labeled when
  historical retrieval is explicitly allowed;
- memory cannot promote hypotheses to confirmed Plant state, unlock Safety Gate,
  authorize physical action, or change dataset trainability;
- untrusted uploaded/user/provider/connector content remains labeled as data and cannot
  become instructions;
- compaction preserves active objective, ActorContext, PlantAccessGrant scope,
  approvals, pending proposals, source refs, memory refs, trust/freshness labels, and
  trace refs;
- compaction does not upgrade authority or erase denial/approval state;
- context build traces record source selection, exclusions, redaction, size, and budget
  information without hidden reasoning or secrets.

## Open Questions

No blocker for `/prd-to-tasks FT-008`. Exact table names, retention durations, memory
review timers, context item count limits, and compaction storage location can be chosen
during task decomposition as long as permission-aware retrieval, source-ref backing,
non-authority, trust labels, redaction, and compaction-retention constraints hold.
